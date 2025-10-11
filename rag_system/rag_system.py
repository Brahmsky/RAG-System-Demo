import os
from pathlib import Path
from google import genai
from openai import OpenAI
from neo4j import GraphDatabase

from .core.database import KnowledgeDatabase
from .text.retriever import Retriever
from .text.reranker import Reranker
from .generation.compressor import Compressor
from .generation.generator import Generator
from .utils.text_utils import TextProcessor
from .core.config import RAGConfig
from .text.multiquery_generator import MultiqueryGenerator
from .core.embedder import Embedder
from .graph.Data2Neo4j import Data2Neo4j

class RAGSystem:
    def __init__(self, config: RAGConfig):
        self.config = config
        ebd_client = genai.Client(api_key=config.gemini_api_key)
        llm_client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"),
                                base_url='https://api.deepseek.com')
        neo_driver = {'uri': config.neo4j_uri,'auth': config.neo4j_auth}
        try:
            self.neo = Data2Neo4j(llm_client, config.llm_model_name, neo_driver)
        except Exception as e:
            raise RuntimeError(f"Neo4j初始化出错：{str(e)}，请检查服务/配置！")

        self.embedder = Embedder(ebd_client, config.embedding_model_name)
        # 初始化数据库
        self.db = KnowledgeDatabase(
            db_path=config.db_path,
            collection_name=config.embedding_model_name.replace("/", "_"),
            verbose=config.verbose,
        )
        self.db.rebuild_bm25()

        query_expander = MultiqueryGenerator(llm_client, config.llm_model_name)

        # 注意：这里应该使用 config.embedding_model_name（实例属性），而不是 RAGConfig.embedding_model_name（类属性）
        # collection 已经在 self.db 初始化时创建了，这里是重复获取（可以删除）
        # collection_name = config.embedding_model_name.replace('/', '_')
        # self.collection = self.db.chroma_client.get_or_create_collection(name=collection_name)

        # 初始化模块
        self.retriever = Retriever(self.db, embedder=self.embedder, query_expander=query_expander, verbose=config.verbose)
        self.reranker = Reranker(config.reranker_model_name)
        self.compressor = Compressor(llm_client, config.llm_model_name, verbose=config.verbose)
        self.generator = Generator(llm_client, config.llm_model_name)

    # ================= 知识库管理 =================

    def add_corpus(self, filename: str, language="English"):
        """添加新文档到知识库 - 使用文档级实体识别优化图谱构建"""
        filepath = Path(self.config.knowledgebase_path) / filename

        print(f"开始处理知识库文件：{filepath}")
        text = TextProcessor.read_file(filepath)
        chunks = TextProcessor.split_text(text, language=language)

        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        existing_ids = set(self.db.collection.get(ids=ids)['ids'])
        print(f"在数据库中找到了{len(existing_ids)}个已存在的块")

        new_docs, new_ids = [], []
        for i, doc in enumerate(chunks):
            if ids[i] not in existing_ids:
                new_docs.append(doc)
                new_ids.append(ids[i])
        if not new_docs:
            print("所有文本块都已完成存于数据库，无需添加。\n")
            return

        print(f"向数据库中添加{len(new_docs)}个新文本块……")
        
        # ========== 🔥 关键改进：使用文档级处理方法 ==========
        # 使用新的process_document方法替代逐chunk调用process
        self.neo.process_document(filename, text, new_docs)
        
        # 批量生成 embedding
        batch_size = 100
        for i in range(0, len(new_docs), batch_size):
            batch = new_docs[i:i+batch_size]

            embeddings = self.embedder.embed(batch, task_type="RETRIEVAL_DOCUMENT")
            batch_ids = [f"{filename}_{i+j}" for j in range(len(batch))]
            metadatas = [{"source": filename} for _ in batch]

            self.db.collection.add(
                ids=batch_ids,
                documents=batch,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        # 执行后处理合并
        self.neo.after_processing()

        self.db.rebuild_bm25()
        print(f"文档 {filename} 添加完成 ✅")

    def remove_corpus(self, filename: str):
        """从知识库中删除指定文档"""
        if self.config.verbose:
            print(f"正在删除文档 {filename}…")

        results = self.db.collection.get(where={"source": filename})
        ids = results["ids"]
        if ids:
            self.db.collection.delete(ids=ids)

        self.neo.delete_graph_from_sources(filename)

        self.db.rebuild_bm25()
        if self.config.verbose:
            print(f"文档 {filename} 删除完成 ✅")

    def update_corpus(self, filename: str, language="English"):
        """更新知识库中的文档（先删除再添加）"""
        if self.config.verbose:
            print(f"正在更新文档 {filename}…")

        self.remove_corpus(filename)
        self.add_corpus(filename, language=language)

        if self.config.verbose:
            print(f"文档 {filename} 更新完成 ✅")

    # ================= 主查询接口 =================

    def query(self, query: str, k=10, top_n=4, mode="hybrid", compress=False, source_filter=None) -> str:
        """统一查询接口"""
        text_docs = []
        graph_context = ""
        if mode in ["vector", "keyword", "expand", "text_hybrid"]:
            if mode == "vector":
                text_docs = self.retriever.vector_search(query, k, source_filter=source_filter)
            elif mode == "keyword":
                text_docs = self.retriever.keyword_search(query, k)
            elif mode == "expand":
                text_docs = self.retriever.expand_search(query, k, source_filter=source_filter)
            elif mode == "text_hybrid":
                text_docs = self.retriever.text_hybrid_search(query, k, source_filter=source_filter)

            if text_docs:
                text_docs = self.reranker.rerank(query, text_docs, top_n)
                if compress:
                    text_docs = self.compressor.compress(query, text_docs)
            else:
                return "文本中未找到相关信息"

        elif mode == "graph":
            graph_context = self.neo.query_graph_raw(query)
            graph_context = graph_context if graph_context else "知识图谱中未找到相关信息"

        elif mode == "hybrid": # 默认模式
            text_docs = self.retriever.text_hybrid_search(query, k, source_filter=source_filter)
            if text_docs:
                text_docs = self.reranker.rerank(query, text_docs, top_n)
                if compress:
                    text_docs = self.compressor.compress(query, text_docs)

            graph_context = self.neo.query_graph_raw(query)
            graph_context = graph_context if graph_context else "知识图谱中未找到相关信息"

        else:
            return "Unknown search mode!"

        if not text_docs and (not graph_context or "未找到" in graph_context):
            return "文本和知识图谱中均未找到相关信息"

        return self.generator.generate(query, text_docs, graph_context)
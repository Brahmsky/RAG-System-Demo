from pathlib import Path
from google import genai

from .database import KnowledgeDatabase
from .retriever import Retriever
from .reranker import Reranker
from .compressor import Compressor
from .generator import Generator
from .text_utils import TextProcessor
from .config import RAGConfig
from .multiquery_generator import MultiqueryGenerator
from .embedder import Embedder

class RAGSystem:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.client = genai.Client(api_key=config.api_key)

        self.embedder = Embedder(self.client, config.embedding_model_name)
        # 初始化数据库
        self.db = KnowledgeDatabase(
            db_path=config.db_path,
            collection_name=config.embedding_model_name.replace("/", "_"),
            verbose=config.verbose,
        )
        self.db.rebuild_bm25()

        query_expander = MultiqueryGenerator(self.client, config.llm_model_name)

        collection_name = RAGConfig.embedding_model_name.replace('/', '_')
        self.collection = self.db.chroma_client.get_or_create_collection(name=collection_name)

        # 初始化模块
        self.retriever = Retriever(self.db, embedder=self.embedder, query_expander=query_expander, verbose=config.verbose)
        self.reranker = Reranker(config.reranker_model_name)
        self.compressor = Compressor(self.client, config.llm_model_name, verbose=config.verbose)
        self.generator = Generator(self.client, config.llm_model_name)

    # ================= 知识库管理 =================

    def add_corpus(self, filename: str, language="English"):
        """添加新文档到知识库"""
        filepath = Path(self.config.knowledgebase_path) / filename

        print(f"开始处理知识库文件：{filepath}")
        text = TextProcessor.read_file(filepath)
        chunks = TextProcessor.split_text(text, language=language)

        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        existing_ids = set(self.collection.get(ids=ids)['ids'])
        print(f"在数据库中找到了{len(existing_ids)}个已存在的块")

        new_docs, new_ids = [], []
        for i, doc in enumerate(chunks):
            if ids[i] not in existing_ids:  # 这里逻辑是，只有手动在后面添加的文本内容多到出现了新的块时，才会去建立新的索引，如果是小改的话就需要主函数中手动更新
                new_docs.append(doc)
                new_ids.append(ids[i])
        if not new_docs:
            print("所有文本块都已完成存于数据库，无需添加。\n")
            return

        print(f"向数据库中添加{len(new_docs)}个新文本块……")
        # 批量生成 embedding
        batch_size = 100
        for i in range(0, len(new_docs), batch_size):
            batch = new_docs[i:i+batch_size]

            embeddings = self.embedder.embed(batch, task_type="RETRIEVAL_DOCUMENT")
            ids = [f"{filename}_{i+j}" for j in range(len(batch))]
            metadatas = [{"source": filename} for _ in batch]

            self.db.collection.add(
                ids=ids,
                documents=batch,
                embeddings=embeddings,
                metadatas=metadatas,
            )

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

    def query(self, query: str, k=10, top_n=3, mode="hybrid", compress=False) -> str:
        """统一查询接口"""
        if mode == "vector":
            docs = self.retriever.vector_search(query, k)
        elif mode == "keyword":
            docs = self.retriever.keyword_search(query, k)
        elif mode =='fusion':
            docs = self.retriever.fusion_search(query, k)
        else:  # 默认 hybrid
            docs = self.retriever.hybrid_search(query, k)

        if not docs:
            return "没有找到相关信息"

        docs = self.reranker.rerank(query, docs, top_n)
        if compress:
            docs = self.compressor.compress(query, docs)

        return self.generator.generate(query, docs)
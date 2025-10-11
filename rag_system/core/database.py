import chromadb
from rank_bm25 import BM25Okapi
from ..utils.smart_tokenize import smart_tokenize

class KnowledgeDatabase:
    def __init__(self, db_path, collection_name, verbose=True):
        self.verbose = verbose
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
        self.bm25_index = None
        self.bm25_corpus = []

    def get_all_sources(self):
        """获取数据库中所有文档来源"""
        all_data = self.collection.get(include=["metadatas"])
        sources = set()
        for metadata in all_data.get("metadatas", []):
            if metadata and "source" in metadata:
                sources.add(metadata["source"])
        return list(sources)
    
    def get_stats(self):
        """获取数据库统计信息"""
        all_data = self.collection.get(include=["metadatas"])
        total_docs = len(all_data.get("ids", []))
        sources = self.get_all_sources()
        return {
            "total_documents": total_docs,
            "sources": sources,
            "source_count": len(sources)
        }

    def rebuild_bm25(self, language="auto"):
        all_docs = self.collection.get(include=["documents"])
        self.bm25_corpus = all_docs["documents"]
        if not self.bm25_corpus:
            self.bm25_index = None
            if self.verbose:
                print("BM25 索引为空")
            return
        tokenized = [smart_tokenize(doc, language) for doc in self.bm25_corpus]
        self.bm25_index = BM25Okapi(tokenized)
        if self.verbose:
            stats = self.get_stats()
            print(f"[数据库状态]")
            print(f"   - 文档总数: {stats['total_documents']}")
            print(f"   - 来源文件数: {stats['source_count']}")
            print(f"   - 文件列表: {', '.join(stats['sources']) if stats['sources'] else '无'}")
            print(f"   - BM25 索引: 已构建 ({len(self.bm25_corpus)} 文档)")
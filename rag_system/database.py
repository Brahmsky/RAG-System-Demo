import chromadb
from rank_bm25 import BM25Okapi
from .smart_tokenize import smart_tokenize

class KnowledgeDatabase:
    def __init__(self, db_path, collection_name, verbose=True):
        self.verbose = verbose
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
        self.bm25_index = None
        self.bm25_corpus = []

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
            print(f"BM25 索引构建完成，共 {len(self.bm25_corpus)} 文档")
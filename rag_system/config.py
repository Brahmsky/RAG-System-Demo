from dataclasses import dataclass
import os

@dataclass
class RAGConfig:
    embedding_model_name: str = "gemini-embedding-001"
    reranker_model_name: str = "BAAI/bge-reranker-base"
    llm_model_name: str = "gemini-2.5-flash"
    db_path: str = "./chroma_db"
    knowledgebase_path: str = "./Knowledgebase"
    verbose: bool = True

    @property
    def api_key(self):
        key = os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("请先设置 GOOGLE_API_KEY 环境变量")
        return key
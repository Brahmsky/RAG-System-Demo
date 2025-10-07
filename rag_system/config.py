from dataclasses import dataclass
import os
from typing import Dict

@dataclass
class RAGConfig:
    embedding_model_name: str = "gemini-embedding-001"
    reranker_model_name: str = "BAAI/bge-reranker-base"
    llm_model_name: str = "deepseek-chat"
    db_path: str = "./chroma_db"
    knowledgebase_path: str = "./Knowledgebase"
    verbose: bool = True
    neo4j_uri: str = "bolt://localhost:7687"  # Neo4j 连接地址
    neo4j_auth: tuple[str, str] = ("neo4j", "123456qq") # 需要自己改成对应的密码

    @property
    def gemini_api_key(self):
        key = os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("请先设置 GOOGLE_API_KEY 环境变量")
        return key

    @property
    def ds_api_key(self):
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("请先设置 DEEPSEEK_API_KEY 环境变量")
        return key
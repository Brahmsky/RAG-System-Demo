import json
from typing import List, Tuple, Dict, Set

from neo4j import GraphDatabase

from .data_structure import KnowledgeGraph, MergeMapping
from .knowledge_graph_builder import KnowledgeGraphBuilder


class Data2Neo4j:
    """
    兼容适配器类 - 保持向后兼容性
    内部使用重构后的KnowledgeGraphBuilder来实现功能
    """
    def __init__(self, client, model, driver):
        self.client = client
        self.model = model
        
        # 使用新的KnowledgeGraphBuilder
        neo4j_config = {
            'uri': driver['uri'],
            'auth': driver['auth']
        }
        self.builder = KnowledgeGraphBuilder(client, model, neo4j_config)
        
        # 保持兼容性的属性
        self.document_entities = self.builder.document_entities
        print("[Data2Neo4j] Compatibility adapter initialized.")

    def close(self):
        """关闭图谱构建器"""
        if hasattr(self, 'builder') and self.builder:
            self.builder.close()
            
    # 移除__del__方法，避免重复关闭
    # 实际的资源管理由Neo4jDatabase负责

    # ================= 向后兼容的方法 =================
    
    def process(self, filename: str, text: str, doc_entities_mapping: dict | None = None):
        """向后兼容的单chunk处理方法"""
        self.builder.process_single_chunk(filename, text, doc_entities_mapping)
    
    def process_document(self, filename: str, full_text: str, chunks: list):
        """文档级处理方法"""
        self.builder.process_document(filename, full_text, chunks)
    
    def after_processing(self):
        """后处理合并"""
        self.builder.execute_post_processing()
    
    def delete_graph_from_sources(self, source_doc_id: str):
        """删除文档图谱数据"""
        self.builder.delete_document(source_doc_id)
    
    def query_graph_raw(self, question: str):
        """图谱查询"""
        return self.builder.query_graph(question)
    
    def get_graph_schema(self) -> dict:
        """获取图谱Schema"""
        return self.builder.get_graph_schema()
    
    # ================= 可选：保留原有私有方法（如果外部有调用） =================
    
    def _extract_document_entities(self, filename: str, full_text: str) -> dict:
        """向后兼容的文档级实体识别"""
        return self.builder.entity_extractor.extract_document_entities(filename, full_text)
    
    def _get_existing_entities(self) -> List[str]:
        """向后兼容的获取现有实体"""
        return self.builder.graph_db.get_existing_entities()
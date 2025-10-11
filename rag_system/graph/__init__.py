"""
知识图谱引擎模块

重构后的SOLID架构：
- Neo4jDatabase: 数据库连接和基础操作
- EntityExtractor: 实体提取和三元组抽取
- GraphProcessor: 图谱结构化和验证
- GraphQueryEngine: 图谱查询和Cypher生成
- EntityMerger: 实体去重和合并
- KnowledgeGraphBuilder: 主协调器，组合所有组件
- Data2Neo4j: 兼容适配器，保持向后兼容
"""

from .data_structure import KnowledgeGraph, Node, Edge, MergeMapping
from .graph_database import Neo4jDatabase
from .entity_extractor import EntityExtractor
from .graph_processor import GraphProcessor
from .query_engine import GraphQueryEngine
from .entity_merger import EntityMerger
from .knowledge_graph_builder import KnowledgeGraphBuilder
from .Data2Neo4j import Data2Neo4j

__all__ = [
    'KnowledgeGraph', 'Node', 'Edge', 'MergeMapping',
    'Neo4jDatabase', 'EntityExtractor', 'GraphProcessor',
    'GraphQueryEngine', 'EntityMerger', 'KnowledgeGraphBuilder',
    'Data2Neo4j'
]

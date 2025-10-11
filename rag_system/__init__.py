"""
RAG System - 混合检索增强生成系统

架构说明：
- core: 核心基础设施（配置、数据库、嵌入器）
- text: 文本检索引擎（向量检索、关键词检索、查询扩展、重排序）
- graph: 知识图谱引擎（实体提取、图谱构建、图谱查询）
- generation: 生成模块（答案生成、上下文压缩）
- utils: 工具模块（文本处理、分词）
"""

from .core import RAGConfig
from .rag_system import RAGSystem

__version__ = "1.0.0"

__all__ = [
    'RAGConfig',
    'RAGSystem',
]


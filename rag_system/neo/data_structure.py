from pydantic import BaseModel, Field
from typing import Dict, List, Any

class Node(BaseModel):
    id: str = Field(..., description="node的唯一标识符，通常是实体名称(e.g., '人', '组织', '概念')")
    label: str = Field(..., description="node的类型或种类")
    properties: Dict[str, Any] = Field(default_factory=dict, description="node的属性")

class Edge(BaseModel):
    source: str = Field(..., description="source node的ID")
    target: str = Field(..., description="target node的ID")
    label: str = Field(..., description="relationship的类型(e.g., '出生于', '被影响')")
    properties: Dict[str, Any] = Field(default_factory=dict, description="relationship的属性")

class KnowledgeGraph(BaseModel):
    nodes: List[Node] = Field(..., description="图中所有node")
    edges: List[Edge] = Field(..., description="图中所有edge")

class MergeMapping(BaseModel):
    """用于存储实体ID合并映射的模型。"""
    mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="一个字典，其中 key 是要被合并的重复ID，value 是要保留的主ID。"
    )
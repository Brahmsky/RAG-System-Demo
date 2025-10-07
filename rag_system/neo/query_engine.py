"""
图谱查询引擎
负责Schema检索、Cypher生成和查询执行
遵循单一职责原则
"""
import json
import os
import sys
from typing import List, Dict
from .graph_database import Neo4jDatabase

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from ..multiquery_generator import MultiqueryGenerator

class GraphQueryEngine:
    """图谱查询引擎，专门负责图谱查询相关功能"""
    
    def __init__(self, llm_client, model_name: str, graph_db: Neo4jDatabase):
        self.client = llm_client
        self.model = model_name
        self.graph_db = graph_db
        self.multi_query_generator = MultiqueryGenerator(llm_client, model_name, verbose=True)
    
    def retrieve_relevant_schema(self, question: str) -> Dict:
        """
        根据用户问题，从完整的 Schema 和实体列表中，检索出最相关的子集。
        """
        print(f"\n--- Answering question: '{question}' ---")

        schema_dict = self.graph_db.get_graph_schema()
        schema_for_prompt = f"""
        - **节点标签**: {schema_dict.get('node_labels', [])}
        - **关系类型**: {schema_dict.get('relationship_types', [])}
        """
        existing_entities = self.graph_db.get_existing_entities()
        entities_list_str = str(existing_entities)

        prompt = f"""
        你是一个图谱数据检索专家。你的任务是根据用户的这几个问题，从下面提供的"可用数据"中，挑选出可能相关的节点标签、关系类型和实体ID。

        ### 任务要求:
        1.  **相关性为先**: 选择与问题相关程度较高的项，不要选择明显无关的。和这个问题有一定相关性的、可能对答案产生贡献的，也可以选择。
        2.  **返回JSON**: 你的回答必须是一个 JSON 对象，包含三个键: `node_labels`, `relationship_types`, `entity_ids`。每个键的值都是一个列表。
        3.  **如果都不相关**: 如果你认为没有任何数据与问题相关，请返回一个包含三个空列表的 JSON。
        4.  **不要一股脑返回太多杂项，每个键下面最多返回10个项。**

        {schema_for_prompt}
        - **所有实体ID**: 
        {entities_list_str}

        ### 用户问题:
        ---
        {question}
        {'\n\t'.join(self.multi_query_generator.expand(question, num_queries=3))}
        ---
        """
        print("--> Text-to-Cypher 步骤 1: 正在检索相关的 Schema 和实体...")
        print(f"prompt: {prompt}")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个图谱数据检索专家，专注于根据问题筛选相关数据。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        try:
            return json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, IndexError):
            print("  > 步骤 1 失败: LLM未能返回有效的JSON。")
            return {"node_labels": [], "relationship_types": [], "entity_ids": []}
    
    def generate_cypher_query(self, question: str, context_info: Dict) -> str:
        """根据问题和上下文信息生成Cypher查询"""
        context_for_prompt = f"""
        - **相关节点标签**: {context_info.get('node_labels', [])}
        - **相关关系类型**: {context_info.get('relationship_types', [])}
        - **相关实体ID (重点参考)**: {context_info.get('entity_ids', [])}
        """

        cypher_generation_prompt = f"""
        你是一名高效的 Neo4j Cypher 查询专家。你的任务是严格根据下面提供的"可用工具"和用户问题，生成一段 Cypher 代码。
        1.  使用 `id` 属性进行匹配。
        2.  查询和return语句中，保持变量名一致（是的，这么简单的错误也有可能犯）。关系类型前也需要定义变量，通过 type(r) 函数返回关系名称，获得全面的查询信息；
        3.  节点标签和关系类型**只能**来自列表里面提供的元素，绝对不要自己编造列表里不存在的词语
        4.  灵活查询：
            首先采用标签 / 关系批量匹配 + 1跳 / 2跳 / 多跳查询：用 标签1|标签2 或 关系1|关系2 或多个| 覆盖多类标签 / 关系，如匹配 Person|Organization 标签节点、查询 published|wrote 关系；
            可以做多跳查询，[type(rel) for rel in r] 用于返回多跳关系的类型列表
            批量固定匹配：用 IN ['id1', 'id2', 'id3'] 一次性匹配多个已知 id 的节点；
            前缀 / 后缀匹配：用 STARTS WITH '前缀' 或 ENDS WITH '后缀' 精准匹配 id 开头 / 结尾的内容，如匹配 id 以 "英" 开头的节点。
            模糊匹配：用 =~ '.*关键词.*' 匹配 id 含指定关键词的节点；
        
        ### 与问题相关的 Schema 和实体:
        {context_for_prompt}
        ---
        **用户问题**: {question}
        ---
        直接输出cypher查询，不要输出多余的内容。
        """

        print("1.生成Cypher查询")
        cypher_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个精通Cypher查询语言的专家，会根据提供的图谱生成多段查询代码。"},
                {"role": "user", "content": cypher_generation_prompt}
            ],
            temperature=0.0
        )
        cypher_query = cypher_response.choices[0].message.content.strip()

        # 清理Cypher查询格式
        if cypher_query.startswith("```"):
            first_newline = cypher_query.find('\n')
            if first_newline != -1:
                cypher_query = cypher_query[first_newline + 1:]
            else:
                if cypher_query.lower().startswith("```cypher"):
                    cypher_query = cypher_query[9:].strip()
                else:
                    cypher_query = cypher_query[3:].strip()

        if cypher_query.endswith("```"):
            cypher_query = cypher_query[:-3].strip()

        print(f"  > Generated Cypher: {cypher_query}")
        return cypher_query
    
    def query_graph(self, question: str) -> List[Dict]:
        """完整的图谱查询流程"""
        # 第一步：检索相关Schema
        relevant_context = self.retrieve_relevant_schema(question)
        if not relevant_context.get("node_labels") and not relevant_context.get("relationship_types"):
            print("  > 步骤 1 未找到相关 Schema，无法构建查询。")
            return []
        
        print(f"""
        - **相关节点标签**: {relevant_context.get('node_labels', [])}
        - **相关关系类型**: {relevant_context.get('relationship_types', [])}
        - **相关实体ID (重点参考)**: {relevant_context.get('entity_ids', [])}
        """)
        
        # 第二步：生成Cypher查询
        cypher_query = self.generate_cypher_query(question, relevant_context)
        
        # 第三步：执行查询
        print("2.执行查询并返回")
        context = self.graph_db.execute_cypher(cypher_query)
        print(f"  > Retrieved context: {context}")
        
        return context
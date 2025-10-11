"""
图谱查询引擎
负责Schema检索、Cypher生成和查询执行
遵循单一职责原则
"""
import json
from typing import List, Dict
from .graph_database import Neo4jDatabase
from ..text.multiquery_generator import MultiqueryGenerator

class GraphQueryEngine:
    """图谱查询引擎，专门负责图谱查询相关功能"""
    
    def __init__(self, llm_client, model_name: str, graph_db: Neo4jDatabase):
        self.client = llm_client
        self.model = model_name
        self.graph_db = graph_db
        self.multi_query_generator = MultiqueryGenerator(llm_client, model_name, verbose=False)
    
    def retrieve_relevant_schema(self, question: str) -> Dict:
        """
        根据用户问题，从完整的 Schema 和实体列表中，检索出最相关的子集。
        """
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
            raw_content = response.choices[0].message.content
            result = json.loads(raw_content)
            print(f"\n[Schema检索结果] {result}")
            return result
        except (json.JSONDecodeError, IndexError) as e:
            print(f"[ERROR] Schema检索失败: {e}")
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
        
        ### 核心规则（必须遵守）:
        1.  使用 `id` 属性进行匹配。
        2.  查询和return语句中，保持变量名一致。关系类型前定义变量，通过 type(r) 函数返回关系名称。
        3.  节点标签和关系类型**只能**来自下面提供的列表，绝对不要自己编造。
        4.  **禁止使用未定义的变量**：如果要用 path、relationships() 等，必须先在 MATCH 中定义！
        
        ### 查询策略:
        - 标签/关系批量匹配：用 标签1|标签2 或 关系1|关系2 覆盖多类
        - 批量固定匹配：用 IN ['id1', 'id2', 'id3'] 匹配多个已知 id
        - 前缀/后缀匹配：用 STARTS WITH 或 ENDS WITH
        - 模糊匹配：用 =~ '.*关键词.*'
        - 多跳查询：MATCH path = (a)-[*1..3]->(b) 然后用 relationships(path)
        
        ### 正确示例:
        ```cypher
        # 单跳查询（推荐）
        MATCH (p:人物)-[r:被控]->(c:罪名)
        WHERE p.id = '人物_艾伦·图灵'
        RETURN p.id, type(r), c.id
        
        # 多跳查询（如果需要）
        MATCH path = (p:人物)-[*1..2]->(n)
        WHERE p.id = '人物_艾伦·图灵'
        RETURN p.id, [rel IN relationships(path) | type(rel)], n.id
        ```
        
        ### 错误示例（禁止）:
        ```cypher
        # ❌ 错误：path 未定义
        MATCH (p)-[r]->(n)
        RETURN [rel IN relationships(path) | type(rel)]
        
        # ❌ 错误：使用了不存在的标签
        MATCH (p:不存在的标签)
        ```
        
        ### 与问题相关的 Schema 和实体:
        {context_for_prompt}
        ---
        **用户问题**: {question}
        ---
        直接输出一个简洁有效的 Cypher 查询，不要输出多余的内容。优先使用单跳查询，除非问题明确需要多跳。
        """

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

        # 验证和修复常见错误
        cypher_query = self._validate_and_fix_cypher(cypher_query)
        print(f"\n[生成的Cypher] {cypher_query}")
        
        return cypher_query
    
    def _validate_and_fix_cypher(self, cypher_query: str) -> str:
        """验证并修复常见的Cypher语法错误"""
        import re
        
        original_query = cypher_query
        fixes_applied = []
        
        # 修复1: 检查是否使用了 relationships(path) 但没有定义 path
        if 'relationships(path)' in cypher_query or 'nodes(path)' in cypher_query:
            # 检查是否定义了 path
            if not re.search(r'\bpath\s*=', cypher_query, re.IGNORECASE):
                # 没有定义 path，尝试修复
                # 如果是简单的单跳查询，移除 relationships(path) 相关的部分
                if re.search(r'MATCH\s+\([^)]+\)-\[[^\]]+\]->\([^)]+\)', cypher_query, re.IGNORECASE):
                    # 这是单跳查询，移除 relationships(path) 部分
                    cypher_query = re.sub(
                        r',?\s*\[rel\s+IN\s+relationships\(path\)\s*\|\s*type\(rel\)\]',
                        '',
                        cypher_query,
                        flags=re.IGNORECASE
                    )
                    # 移除可能的 AS 路径关系 等别名
                    cypher_query = re.sub(
                        r',?\s*AS\s+路径关系',
                        '',
                        cypher_query,
                        flags=re.IGNORECASE
                    )
                    fixes_applied.append("移除了未定义的 path 变量引用")
        
        # 修复2: 检查是否有重复的逗号
        cypher_query = re.sub(r',\s*,', ',', cypher_query)
        
        # 修复3: 检查RETURN语句末尾是否有多余的逗号
        cypher_query = re.sub(r',\s*$', '', cypher_query.strip())
        
        # 修复4: 清理多余的空格
        cypher_query = re.sub(r'\s+', ' ', cypher_query).strip()
        
        if fixes_applied:
            print(f"[自动修复] {', '.join(fixes_applied)}")
        
        return cypher_query
    
    def query_graph(self, question: str) -> List[Dict]:
        """完整的图谱查询流程"""
        # 第一步：检索相关Schema
        relevant_context = self.retrieve_relevant_schema(question)
        if not relevant_context.get("node_labels") and not relevant_context.get("relationship_types"):
            print("[ERROR] 未找到相关Schema，无法构建查询")
            return []
        
        # 第二步：生成Cypher查询
        cypher_query = self.generate_cypher_query(question, relevant_context)
        
        # 第三步：执行查询（带重试）
        max_retries = 2
        for attempt in range(max_retries):
            try:
                context = self.graph_db.execute_cypher(cypher_query)
                print(f"\n[查询结果] {context}\n")
                return context
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Cypher执行失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                
                if attempt < max_retries - 1:
                    # 还有重试机会，尝试用错误信息重新生成
                    retry_prompt = f"""
                    你之前生成的Cypher查询执行失败了。
                    
                    **失败的查询**:
                    ```cypher
                    {cypher_query}
                    ```
                    
                    **错误信息**: {error_msg}
                    
                    **常见错误修复**:
                    - 如果提示变量未定义（如 path），要么定义它（MATCH path = ...），要么不使用它
                    - 不要在单跳查询中使用 relationships(path)
                    - 检查语法错误，如多余的逗号、括号不匹配等
                    
                    **与问题相关的 Schema**:
                    - 节点标签: {relevant_context.get('node_labels', [])}
                    - 关系类型: {relevant_context.get('relationship_types', [])}
                    - 实体ID: {relevant_context.get('entity_ids', [])}
                    
                    **用户问题**: {question}
                    
                    请生成一个修复后的、更简单的Cypher查询。优先使用最基础的单跳MATCH查询。
                    """
                    
                    retry_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "你是一个精通Cypher查询语言的专家，擅长根据错误信息修复查询。"},
                            {"role": "user", "content": retry_prompt}
                        ],
                        temperature=0.0
                    )
                    
                    cypher_query = retry_response.choices[0].message.content.strip()
                    
                    # 清理代码块标记
                    if cypher_query.startswith("```"):
                        lines = cypher_query.split('\n')
                        cypher_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else cypher_query[3:]
                    if cypher_query.endswith("```"):
                        cypher_query = cypher_query[:-3].strip()
                    
                    cypher_query = self._validate_and_fix_cypher(cypher_query)
                    print(f"\n[重试生成的Cypher] {cypher_query}")
                else:
                    # 最后一次尝试失败
                    return []
        
        return []
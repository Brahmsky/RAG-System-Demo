"""
图谱处理器
负责三元组结构化、消歧、图谱构建和验证
遵循单一职责原则
"""
import json
from typing import List
from .data_structure import KnowledgeGraph


class GraphProcessor:
    """图谱处理器，专门负责图谱的结构化和验证"""
    
    def __init__(self, llm_client, model_name: str):
        self.client = llm_client
        self.model = model_name
    
    def structure_and_disambiguate_graph(self, triples_str: str, existing_entities: List[str]):
        """
        将粗提取的三元组，结构化为符合要求的图谱 JSON，并完成消歧。
        这个提示词融合了结构化和消歧的核心意图。
        """
        entities_list_str = ", ".join(f"'{entity}'" for entity in existing_entities)
        prompt = f"""
        你的任务是将输入的三元组列表，转换为符合 `extract_graph` 工具要求的知识图谱 JSON。

        ### 核心要求:
        1. **融合已有实体**: 检查三元组中的实体是否已存在于"已有实体列表"中。如果存在，**使用完全一致的ID**。
        2. **创建新实体**: 如果实体是新的，为其创建一个简洁唯一的中文ID（如"人物_图灵"）。
        3. **处理别名**: 如果发现别名（如"图灵"和"艾伦·图灵"），将它们合并到同一个节点，并将别名存入`properties`的`别名`字段。
        4. **格式必须完整**:
           - 返回的 JSON 必须包含 `nodes` 和 `edges` 两个列表，即使为空也要返回 `[]`。
           - 每个 `edge` 必须包含 `source`, `target`, `label` 三个字段。
           - `node` 和 `edge` 的 `label` 只能包含汉字、数字、下划线。
        5. **特别注意**: 提取格式不要包含"为...所闻名" "由...设计"这种带三个点号的关系！三个点号不符合cypher语法规范！

        ### 已有实体列表 (用于融合，如果提取实体已存在，请采用这里面的ID):
        ---
        {entities_list_str}
        ---

        ### 待处理的三元组:
        ---
        {triples_str}
        ---
        """
        print("--> 步骤 2: 正在进行结构化与消歧...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个数据建模专家，精通知识图谱构建和JSON格式化。"},
                {"role": "user", "content": prompt}
            ],
            tools=[{"type": "function",
                    "function": {"name": "extract_graph", "parameters": KnowledgeGraph.model_json_schema()}}],
            tool_choice={"type": "function", "function": {"name": "extract_graph"}}
        )

        message = response.choices[0].message
        if not message.tool_calls:
            print("Error: The model did not return a tool call in the structuring phase.")
            print("Model's text response:", message.content)
            return None
        return message.tool_calls[0].function
    
    def build_graph(self, function_call) -> KnowledgeGraph:
        """代码层兜底，确保 `nodes` 和 `edges` 字段存在，避免校验失败。"""
        graph_data = json.loads(function_call.arguments)

        if "nodes" not in graph_data:
            graph_data["nodes"] = []
        if "edges" not in graph_data:
            graph_data["edges"] = []

        extracted_graph = KnowledgeGraph(**graph_data)
        print(
            f"--> 步骤 3: 成功校验图谱，包含 {len(extracted_graph.nodes)} 个节点和 {len(extracted_graph.edges)} 个边。")
        return extracted_graph
"""
实体合并器
负责实体去重、消歧和后处理合并操作
遵循单一职责原则
"""
import json
from typing import List, Dict
from .data_structure import MergeMapping
from .graph_database import Neo4jDatabase


class EntityMerger:
    """实体合并器，专门负责实体去重和合并操作"""
    
    def __init__(self, llm_client, model_name: str, graph_db: Neo4jDatabase):
        self.client = llm_client
        self.model = model_name
        self.graph_db = graph_db
    
    def identify_duplicate_entities(self, entity_ids: List[str]) -> Dict[str, str]:
        """使用 Function Calling 来可靠地识别重复实体。"""
        if not entity_ids:
            return {}

        prompt = f"""
        请检查下面列表中的实体ID，找出那些**含义极其相似、完全可以互相替代**，且所有指向同一个真实世界实体的重复项（如果指的是同一个事物，但是属性有比较明显的差异，就不要合并）。
        在每一组重复的ID中，选择一个最常用、最简洁的作为"主ID"。
        然后调用 `save_merge_mapping` 工具来保存这个合并计划。
        如果没有任何需要合并的项，请调用工具并传入一个空字典。

        ### 待处理的实体ID列表:
        ---
        {json.dumps(entity_ids, ensure_ascii=False)}
        ---
        """
        print("--> 后处理: 正在调用 LLM (Function Calling) 识别重复实体...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个数据清洗专家，专注于实体消歧。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            tools=[{
                "type": "function",
                "function": {
                    "name": "save_merge_mapping",
                    "description": "保存实体ID的合并映射",
                    "parameters": MergeMapping.model_json_schema()
                }
            }],
            tool_choice={"type": "function", "function": {"name": "save_merge_mapping"}}
        )

        message = response.choices[0].message
        if not message.tool_calls:
            print("--> 后处理: LLM 未能调用 save_merge_mapping 工具，跳过合并。")
            return {}

        try:
            tool_args = json.loads(message.tool_calls[0].function.arguments)
            merge_plan = MergeMapping(**tool_args)
            return merge_plan.mapping
        except (json.JSONDecodeError, IndexError) as e:
            print(f"--> 后处理: 解析工具参数时出错: {e}，跳过合并。")
            return {}
    
    def execute_post_processing(self):
        """执行完整的后处理流程"""
        print("\n--- 开始执行后处理合并 ---")
        all_current_entities = self.graph_db.get_existing_entities()
        merge_mapping = self.identify_duplicate_entities(all_current_entities)
        self.graph_db.merge_entities(merge_mapping)
        print("--- 所有处理流程完成 ---\n")
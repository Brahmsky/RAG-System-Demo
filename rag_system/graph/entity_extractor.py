"""
实体提取器
负责LLM驱动的实体识别和三元组提取
遵循单一职责原则
"""
import json
from typing import Dict


class EntityExtractor:
    """实体提取器，专门负责文档级和chunk级的实体提取"""
    
    def __init__(self, llm_client, model_name: str):
        self.client = llm_client
        self.model = model_name
    
    def extract_document_entities(self, filename: str, full_text: str) -> Dict[str, str]:
        """
        文档级实体识别，在处理单个chunk前，先识别整个文档中的核心实体。
        返回一个字典，键为实体原始名称，值为规范化ID。
        """
        print(f"--> 步骤 0: 正在进行文档级实体识别 ({filename})...")
        prompt = f"""
        你的任务是从下面的文档中，识别出所有重要的实体，并为每个实体创建一个规范化的ID。

        ### 要求:
        1. **只识别核心实体**：人物、组织、概念、技术、事件等，避免识别过于琐碎的名词。
        2. **创建规范化ID**：为每个实体创建一个简洁、唯一的中文ID，格式建议为 "类型_名称"，例如 "人物_艾伦·图灵"。
        3. **输出格式**：严格返回JSON，结构为 {{"实体原始名称": "规范化ID", ...}}，不要有任何其他解释。

        ### 待处理文档:
        ---
        {full_text}
        ---
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个信息提取助手，专注于识别文档中的核心实体。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},  # 强制JSON输出
                temperature=0.0
            )
            entities_dict = json.loads(response.choices[0].message.content)
            print(f"    识别到 {len(entities_dict)} 个文档级实体: {list(entities_dict.values())}")
            return entities_dict
        except Exception as e:
            print(f"    文档级实体识别失败: {e}")
            return {}
    
    def extract_raw_triples(self, text: str, filename: str | None = None, 
                           document_entities: Dict[str, str] | None = None) -> str:
        """
        从文本中提取（主体, 关系, 客体）三元组，追求召回率。
        这个任务非常简单，LLM 的出错率极低。
        """
        # 构建文档实体列表提示
        entities_list_str = ""
        if document_entities:
            entities_list_str = f"""
        ### 文档已知实体 (请优先使用这些实体的规范化ID作为三元组的主体或客体):
        ---
        {json.dumps(document_entities, ensure_ascii=False, indent=2)}
        ---
        """
        
        prompt = f"""
        你的任务是从下面的文本中，用 "(主体, 关系, 客体)" 的三元组形式，尽可能完整地提取所有事实信息。

        ### 提取要求:
        1. **只用汉语**：所有主体、关系、客体都使用中文。
        2. **关系要具体**：避免使用"是"、"包含"等模糊关系，例如用"(图灵, 提出, 图灵机)"代替"(图灵, 是, 图灵机提出者)"。
        3. **优先使用规范ID**：如果文本中提及的实体在"文档已知实体"列表中，请务必使用列表中的规范化ID。
        4. **输出格式**：每行一个三元组，不要有任何其他多余的解释。

        {entities_list_str}

        ### 待提取文本:
        ---
        {text}
        ---
        """
        print("--> 步骤 1: 正在进行粗提取...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个信息提取助手，专注于识别实体和关系。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content
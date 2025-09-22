from typing import List

class Generator:
    def __init__(self, llm_client, llm_model):
        self.client = llm_client
        self.model = llm_model

    def generate(self, query, docs) -> str:
        context = "\n\n".join(docs)
        prompt = (f"你是一个问答助手。请根据下面提供的相关信息来回答问题。"
                  f"如果这些信息中没有包含问题的答案，你可以表示无法回答。"
                  f"{query}"
                  f"问题：{context}")
        resp = self.client.models.generate_content(model=self.model, contents=prompt)
        return resp.text
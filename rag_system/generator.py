import json

class Generator:
    def __init__(self, llm_client, llm_model):
        self.client = llm_client
        self.model = llm_model

    def generate(self, query, text_docs, graph_context) -> str:
        text_context = "\n\n".join(text_docs)
        prompt = f"""
        把下面提供的文本数据和图谱数据信息结合起来，得到更加全面准确的答案。
        如果这些信息中没有包含问题的答案，你可以表示无法回答。
        ---
        问题：{query}
        ---
        
        ---
        文本数据：{text_context}
        ---
        
        ---
        图谱数据：{json.dumps(graph_context, ensure_ascii=False, indent=2)}
        ---
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个问答助手，擅长结合文本数据库和图谱数据库中的信息回答问题。"},
                {"role": "user", "content": prompt}
            ])
        return resp.choices[0].message.content.strip()
class Compressor:
    def __init__(self, llm_client, llm_model, verbose=True):
        self.client = llm_client
        self.model = llm_model
        self.verbose = verbose

    def compress(self, query, docs):
        context = "\n\n".join(docs)
        prompt = f"根据问题《{query}》，请从以下上下文中抽取最相关的句子，保持原句，不要改写：\n{context}, 每个文档之间的结果用空行分割"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个擅长文档信息处理的专家。"},
                {"role": "user", "content": prompt}
            ]
        )
        return [s.strip() for s in response.choices[0].message.content.split('\n') if s.strip()]

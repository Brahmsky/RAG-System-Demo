from typing import List
from .query_expander import QueryExpander

class MultiqueryGenerator(QueryExpander):
    def __init__(self, llm_client, llm_model, verbose=True):
        self.client = llm_client
        self.model = llm_model
        self.verbose = verbose

    def expand(self, query: str, num_queries=3) -> List[str]:
        prompt = (f"根据以下问题，专注于其特定方面，使用不同的措辞，生成{num_queries}个语义相关的查询。"
                  f"用空行分隔开每个查询，不要输出编号以及多余内容，严格遵循此格式。"
                  f"原始问题：{query}"
                  f"你的查询：")
        resp = self.client.models.generate_content(model=self.model, contents=prompt)
        queries = resp.text.split('\n\n')
        if self.verbose:
            print(f"扩展{num_queries}个查询")
            for i, query in enumerate(queries):
                print(f"--- {i + 1}.{query}")
        return queries

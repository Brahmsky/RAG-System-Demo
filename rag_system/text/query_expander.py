from typing import List

class QueryExpander:
    """抽象接口：定义扩展查询的能力"""
    def expand(self, query: str, num_queries: int) -> List[str]:
        raise NotImplementedError

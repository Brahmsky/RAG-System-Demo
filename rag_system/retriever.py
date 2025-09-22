from .smart_tokenize import smart_tokenize
from typing import List
from .query_expander import QueryExpander

class Retriever:
    def __init__(self, db, embedder, query_expander: QueryExpander=None, verbose=True):
        self.db = db
        self.verbose = verbose
        self.query_expander = query_expander
        self.embedder = embedder

    @staticmethod
    def reciprocal_rank_fusion(search_res: List[List[str]], k: int = 60) -> List[str]:
        """
        执行倒数排名融合 (RRF)。
        :param search_res: 一个包含多个检索结果列表的列表。
        :param k: RRF算法中的平滑参数。
        :return: 融合并重新排序后的文档列表。
        """
        fused_scores = {}
        for doc_list in search_res:
            for rank, doc in enumerate(doc_list):
                if doc not in fused_scores:
                    fused_scores[doc] = 0
                fused_scores[doc] += 1 / (rank + k)
        reranked_res = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in reranked_res]

    def vector_search(self, query, k=5, source_filter=None):
        embedding = self.embedder.embed([query], task_type="RETRIEVAL_QUERY")[0]
        results = self.db.collection.query(
            query_embeddings=embedding,
            n_results=k,
            where={"source": source_filter} if source_filter else None
        )
        return results["documents"][0]

    def keyword_search(self, query, k=5, language="auto"):
        if not self.db.bm25_index:
            return []
        tokens = smart_tokenize(query, language)# 对查询进行分词
        if not tokens:
            return []
        # 获取BM25分数
        scores = self.db.bm25_index.get_scores(tokens)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.db.bm25_corpus[i] for i in top_idx]

    def hybrid_search(self, query, k=5, source_filter=None):
        v = self.vector_search(query, k, source_filter)
        bm = self.keyword_search(query, k)
        return self.reciprocal_rank_fusion([v, bm])  # RRF fusion

    def fusion_search(self, query, k=5, num_queries=3, source_filter=None):
        """
        :param query: 原始查询
        :param k: 控制单个搜索方案的返回结果数量
        :param num_queries: 控制扩展的查询数量
        """
        if not self.query_expander:
            raise ValueError("fusion_search requires a QueryExpander")
        queries = [query] + self.query_expander.expand(query, num_queries)
        all_retrieved_docs = []
        for q in queries:
            vector_res = self.vector_search(q, k, source_filter)
            keyword_res = self.keyword_search(q, k)
            hybrid_res = self.reciprocal_rank_fusion([vector_res, keyword_res])
            all_retrieved_docs.append(hybrid_res)

        return self.reciprocal_rank_fusion(all_retrieved_docs)


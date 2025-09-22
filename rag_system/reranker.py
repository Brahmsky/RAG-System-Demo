from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name):
        self.model = CrossEncoder(model_name)

    def rerank(self, query, docs, top_n=3):
        pairs = [(query, d) for d in docs]
        scores = self.model.predict(pairs)
        scored = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored[:top_n]]
# --- advanced_retrieval.md ---

# Section 1: About Vector Search
Vector search is a method used to find items that are semantically similar, not just keyword-matched. It relies on machine learning models to generate numerical representations of data called vector embeddings. The core idea is that similar items will have vectors that are close to each other in the vector space. One of the most popular algorithms for Approximate Nearest Neighbor (ANN) search is HNSW.

# Section 2: About Keyword Search
The Okapi BM25 formula is a ranking function used by search engines to estimate the relevance of documents to a given search query. It is a bag-of-words model that ranks a set of documents based on the query terms appearing in each document, regardless of their proximity within the document. It is considered a sparse retrieval method.

# Section 3: About Hybrid Approaches
Combining different search strategies can lead to more robust results. For instance, you can merge the ranked lists from a dense retrieval system (like vector search) and a sparse retrieval system (like BM25). A popular technique for this is Reciprocal Rank Fusion, which considers the rank of a document in each list, not its raw score. This approach often improves overall search quality.

# Section 4: Semantic Distractor
Merging multiple result sets is a common challenge in information retrieval. Different algorithms exist to combine rankings from various sources. The goal is to produce a single unified list that is superior to any of the individual lists. This process is sometimes referred to as rank aggregation.

# Section 5: Keyword Distractor
The company "BM25 Solutions" announced a new product today. Their flagship offering, the "Vector Pro", uses a novel fusion technique. An analyst commented, "This is a reciprocal agreement that benefits both parties."
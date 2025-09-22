from google import genai

class Embedder:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def embed(self, texts, task_type):
        resp = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=genai.types.EmbedContentConfig(task_type=task_type)
        )
        return [d.values for d in resp.embeddings]
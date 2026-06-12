from openai import OpenAI
from ..core.config import settings

EMBED_MODEL = "text-embedding-3-small"
MAX_CHARS = 25000  # ~6500 tokens, bien dentro del límite de 8191


class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def embed(self, text: str) -> list[float]:
        text = text.replace("\n", " ").strip()[:MAX_CHARS]
        response = self.client.embeddings.create(input=text, model=EMBED_MODEL)
        return response.data[0].embedding

    def embed_sentencia(self, sentencia) -> list[float]:
        parts = [
            sentencia.caratula or "",
            sentencia.resumen or "",
            (sentencia.contenido or "")[:20000],
        ]
        return self.embed(" ".join(p for p in parts if p))


embedding_service = EmbeddingService()

from openai import OpenAI

from app.core.config import settings

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# 1536 dimensions, cheap, and strong enough for policy-document retrieval --
# no reason to pay for the larger embedding model on this workload.
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Calls OpenAI's embedding endpoint for a batch of text chunks.
    Batching -- sending all chunks in one request instead of one call per
    chunk -- is both cheaper and faster; the API accepts a list of inputs.
    """
    if not texts:
        return []

    response = _client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]

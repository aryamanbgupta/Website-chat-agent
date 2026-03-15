"""Gemini Embedding 2 wrapper with task_type support."""

from google import genai

from app.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, GEMINI_API_KEY

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def embed_texts(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """Embed a batch of texts using Gemini Embedding model.

    Args:
        texts: Texts to embed.
        task_type: RETRIEVAL_DOCUMENT for indexing, RETRIEVAL_QUERY for searching.

    Returns:
        List of embedding vectors (768 dims).
    """
    result = _get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config={
            "task_type": task_type,
            "output_dimensionality": EMBEDDING_DIMENSIONS,
        },
    )
    return [e.values for e in result.embeddings]


def embed_query(text: str) -> list[float]:
    """Embed a single query text for retrieval."""
    results = embed_texts([text], task_type="RETRIEVAL_QUERY")
    return results[0]

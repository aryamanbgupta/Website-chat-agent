"""ChromaDB client and collection management."""

from __future__ import annotations

import chromadb

from app.config import CHROMA_DIR

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def get_parts_collection() -> chromadb.Collection:
    """Get or create the parts collection (4,170 vectors)."""
    return get_client().get_or_create_collection(
        name="parts",
        metadata={"hnsw:space": "cosine"},
    )


def get_knowledge_collection() -> chromadb.Collection:
    """Get or create the knowledge collection (~250 vectors from guides + blogs)."""
    return get_client().get_or_create_collection(
        name="knowledge",
        metadata={"hnsw:space": "cosine"},
    )


def query_parts(
    embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    """Query the parts collection."""
    col = get_parts_collection()
    kwargs = {
        "query_embeddings": [embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)


def query_knowledge(
    embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    """Query the knowledge collection."""
    col = get_knowledge_collection()
    kwargs = {
        "query_embeddings": [embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)

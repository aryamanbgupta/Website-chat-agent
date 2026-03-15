"""search_parts tool — hybrid search across parts database."""

from app.data.search import search_parts_hybrid


def search_parts(
    reasoning: str,
    query: str,
    appliance_type: str | None = None,
    max_results: int = 5,
) -> dict:
    """Search for parts using hybrid strategy.

    - Regex first: detect PS numbers or model numbers for direct lookup
    - Semantic search: embed query and search ChromaDB
    - Keyword fallback: inverted index of part name words
    - 3-tier fallback: scoped → all products → not found with suggestions
    """
    results = search_parts_hybrid(
        query=query,
        appliance_type=appliance_type,
        max_results=max_results,
    )

    # Slim down part objects for the LLM response
    slim_parts = []
    for part in results.get("parts", []):
        slim_parts.append({
            "ps_number": part.get("ps_number", ""),
            "name": part.get("name", ""),
            "brand": part.get("brand", ""),
            "appliance_type": part.get("appliance_type", ""),
            "price": part.get("price", ""),
            "rating": part.get("rating", ""),
            "in_stock": part.get("in_stock", False),
            "image_url": part.get("image_url", ""),
            "source_url": part.get("source_url", ""),
            "symptoms_fixed": part.get("symptoms_fixed", []),
        })

    # Slim down knowledge snippets
    slim_snippets = []
    for snippet in results.get("knowledge_snippets", []):
        meta = snippet.get("metadata", {})
        slim_snippets.append({
            "content": snippet.get("content", "")[:500],
            "source_type": meta.get("source_type", ""),
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
        })

    return {
        "parts": slim_parts,
        "tier": results.get("tier", ""),
        "scope_note": results.get("scope_note", ""),
        "knowledge_snippets": slim_snippets,
        "result_count": len(slim_parts),
    }

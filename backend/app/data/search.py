"""Hybrid search: regex detection, vector search, keyword fallback, RRF merge."""

import re

from app.config import DEFAULT_MAX_RESULTS, KEYWORD_FALLBACK_MAX
from app.data import loader
from app.data.chroma_store import query_knowledge, query_parts
from app.data.embeddings import embed_query

PS_PATTERN = re.compile(r"PS\d{5,10}", re.IGNORECASE)
MODEL_PATTERN = re.compile(r"[A-Z]{2,5}\d{3,}[A-Z\d]*", re.IGNORECASE)


def search_parts_hybrid(
    query: str,
    appliance_type: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict:
    """Run hybrid search across parts data.

    Strategy:
    1. Regex: detect PS numbers or model numbers for direct lookup
    2. Semantic: embed query and search ChromaDB parts collection
    3. Keyword: fallback inverted index search
    4. Merge with reciprocal rank fusion if multiple result sets exist

    Returns dict with keys: parts, tier, scope_note, knowledge_snippets
    """
    # 1. Try direct PS number lookup
    ps_matches = PS_PATTERN.findall(query)
    if ps_matches:
        parts = []
        for ps in ps_matches:
            ps_upper = ps.upper()
            part = loader.parts_by_ps.get(ps_upper)
            if part:
                parts.append(part)
        if parts:
            return {
                "parts": parts[:max_results],
                "tier": "exact_match",
                "scope_note": f"Found {len(parts)} part(s) by PS number",
                "knowledge_snippets": [],
            }

    # 2. Try model number lookup
    model_matches = MODEL_PATTERN.findall(query)
    model_parts = []
    for model in model_matches:
        ps_numbers = loader.models_index.get(model, [])
        for ps in ps_numbers:
            part = loader.parts_by_ps.get(ps)
            if part and part not in model_parts:
                model_parts.append(part)

    # 3. Semantic search
    semantic_parts = _semantic_search(query, appliance_type, max_results)

    # 4. Keyword fallback
    keyword_parts = _keyword_search(query, max_results)

    # Merge results with RRF
    all_result_lists = []
    if model_parts:
        all_result_lists.append(model_parts)
    if semantic_parts:
        all_result_lists.append(semantic_parts)
    if keyword_parts:
        all_result_lists.append(keyword_parts)

    if not all_result_lists:
        # Try without appliance filter (tier 2)
        if appliance_type:
            semantic_parts = _semantic_search(query, None, max_results)
            if semantic_parts:
                return {
                    "parts": semantic_parts[:max_results],
                    "tier": "all_products",
                    "scope_note": f"No {appliance_type}-specific results. Showing all appliance types.",
                    "knowledge_snippets": _get_knowledge_snippets(query, appliance_type),
                }
        return {
            "parts": [],
            "tier": "not_found",
            "scope_note": "No matching parts found. Try different search terms or browse PartSelect.com.",
            "knowledge_snippets": _get_knowledge_snippets(query, appliance_type),
        }

    merged = _reciprocal_rank_fusion(all_result_lists)

    # Determine tier
    tier = "scoped" if appliance_type else "all_products"
    scope_note = f"Found {len(merged)} result(s)"
    if appliance_type:
        scope_note += f" for {appliance_type}"

    # Get knowledge snippets for symptom-like queries
    knowledge_snippets = _get_knowledge_snippets(query, appliance_type)

    return {
        "parts": merged[:max_results],
        "tier": tier,
        "scope_note": scope_note,
        "knowledge_snippets": knowledge_snippets,
    }


def search_knowledge(
    query: str,
    appliance_type: str | None = None,
    n_results: int = 3,
) -> list[dict]:
    """Search the knowledge collection (blogs + repair guides)."""
    return _get_knowledge_snippets(query, appliance_type, n_results)


def _semantic_search(
    query: str,
    appliance_type: str | None,
    max_results: int,
) -> list[dict]:
    """Embed query and search ChromaDB parts collection."""
    try:
        embedding = embed_query(query)
    except Exception:
        return []

    where = None
    if appliance_type:
        where = {"appliance_type": appliance_type}

    results = query_parts(embedding, n_results=max_results, where=where)

    parts = []
    if results and results.get("ids") and results["ids"][0]:
        for i, ps_number in enumerate(results["ids"][0]):
            part = loader.parts_by_ps.get(ps_number)
            if part:
                parts.append(part)
    return parts


def _keyword_search(query: str, max_results: int) -> list[dict]:
    """Search using the inverted keyword index."""
    words = query.lower().split()
    ps_scores: dict[str, int] = {}

    for word in words:
        cleaned = word.strip(".,()-/")
        if cleaned in loader.keyword_index:
            for ps in loader.keyword_index[cleaned]:
                ps_scores[ps] = ps_scores.get(ps, 0) + 1

    # Sort by number of matching keywords (descending)
    ranked = sorted(ps_scores.items(), key=lambda x: x[1], reverse=True)

    parts = []
    for ps, _score in ranked[:KEYWORD_FALLBACK_MAX]:
        part = loader.parts_by_ps.get(ps)
        if part:
            parts.append(part)
    return parts[:max_results]


def _get_knowledge_snippets(
    query: str,
    appliance_type: str | None = None,
    n_results: int = 3,
) -> list[dict]:
    """Query the knowledge collection for relevant blog/guide content."""
    try:
        embedding = embed_query(query)
    except Exception:
        return []

    where = None
    if appliance_type:
        where = {"appliance_type": appliance_type}

    results = query_knowledge(embedding, n_results=n_results, where=where)

    snippets = []
    if results and results.get("ids") and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            snippet = {
                "id": doc_id,
                "content": results["documents"][0][i] if results.get("documents") else "",
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
            snippets.append(snippet)
    return snippets


def _reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) across all lists where the item appears.
    """
    scores: dict[str, float] = {}
    part_map: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, part in enumerate(result_list):
            ps = part.get("ps_number", "")
            if not ps:
                continue
            scores[ps] = scores.get(ps, 0) + 1.0 / (k + rank + 1)
            part_map[ps] = part

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [part_map[ps] for ps, _score in ranked]

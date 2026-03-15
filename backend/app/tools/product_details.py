"""get_product_details tool — direct JSON lookup for full part info."""

from app.data import loader


def get_product_details(reasoning: str, part_number: str) -> dict:
    """Look up full product details by PS number.

    Returns all fields needed for a frontend product card,
    plus data_tier so the LLM can caveat stale data.
    """
    ps = part_number.strip().upper()
    if not ps.startswith("PS"):
        ps = f"PS{ps}"

    part = loader.parts_by_ps.get(ps)
    if not part:
        return {
            "found": False,
            "part_number": ps,
            "message": f"Part {ps} not found in our database. Try searching on PartSelect.com.",
        }

    has_desc = bool(part.get("description", "").strip())
    return {
        "found": True,
        "data_tier": "enhanced" if has_desc else "baseline",
        "ps_number": part.get("ps_number", ""),
        "mfg_part_number": part.get("mfg_part_number", ""),
        "name": part.get("name", ""),
        "brand": part.get("brand", ""),
        "appliance_type": part.get("appliance_type", ""),
        "price": part.get("price", ""),
        "in_stock": part.get("in_stock", False),
        "rating": part.get("rating", ""),
        "review_count": part.get("review_count", ""),
        "description": part.get("description", ""),
        "installation_difficulty": part.get("installation_difficulty", ""),
        "installation_time": part.get("installation_time", ""),
        "symptoms_fixed": part.get("symptoms_fixed", []),
        "image_url": part.get("image_url", ""),
        "video_url": part.get("video_url", ""),
        "source_url": part.get("source_url", ""),
    }

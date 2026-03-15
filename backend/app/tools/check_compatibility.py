"""check_compatibility tool — verify part + model compatibility."""

from app.data import loader


def check_compatibility(
    reasoning: str, part_number: str, model_number: str
) -> dict:
    """Check if a part is compatible with a specific appliance model.

    Uses both forward lookup (part → compatible_models) and reverse lookup
    (model → parts via models_index).

    With 162,976 models indexed (avg 429/part), we can now distinguish:
    - Model in our data + match found → verified compatible
    - Model in our data + no match → not compatible
    - Model NOT in our data → unknown (suggest checking PartSelect.com)
    """
    ps = part_number.strip().upper()
    if not ps.startswith("PS"):
        ps = f"PS{ps}"
    model = model_number.strip().upper()

    part = loader.parts_by_ps.get(ps)
    if not part:
        return {
            "compatible": None,
            "confidence": "part_not_found",
            "part_number": ps,
            "model_number": model,
            "message": f"Part {ps} not found in our database.",
            "source_url": "",
        }

    # Forward check: part's compatible_models list
    compatible_models = part.get("compatible_models", [])
    forward_match = model in compatible_models

    # Reverse check: models_index
    model_parts = loader.models_index.get(model, [])
    reverse_match = ps in model_parts

    if forward_match or reverse_match:
        return {
            "compatible": True,
            "confidence": "verified",
            "part_number": ps,
            "model_number": model,
            "part_name": part.get("name", ""),
            "part_brand": part.get("brand", ""),
            "price": part.get("price", ""),
            "message": f"{ps} ({part.get('name', '')}) is compatible with model {model}.",
            "source_url": part.get("source_url", ""),
        }

    # Determine confidence based on whether we know the model at all
    model_in_index = model in loader.models_index
    part_has_models = len(compatible_models) > 0

    if model_in_index and part_has_models:
        # Both model and part have compatibility data, but no match — not compatible
        return {
            "compatible": False,
            "confidence": "verified",
            "part_number": ps,
            "model_number": model,
            "part_name": part.get("name", ""),
            "part_brand": part.get("brand", ""),
            "message": (
                f"{ps} ({part.get('name', '')}) is not compatible with model {model}. "
                f"Check PartSelect.com for parts that fit your model."
            ),
            "source_url": part.get("source_url", ""),
        }

    # Model or part lacks compatibility data — can't determine
    return {
        "compatible": None,
        "confidence": "not_in_data",
        "part_number": ps,
        "model_number": model,
        "part_name": part.get("name", ""),
        "part_brand": part.get("brand", ""),
        "message": (
            f"We couldn't verify compatibility between {ps} and model {model} "
            f"in our database. "
            f"Check the full compatibility list on PartSelect.com."
        ),
        "source_url": part.get("source_url", ""),
    }

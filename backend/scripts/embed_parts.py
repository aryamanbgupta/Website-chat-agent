"""One-time script: embed all 4,170 parts into ChromaDB parts collection.

Builds entity-centric search documents from structured fields (not raw_markdown).
Enhanced parts get full docs; baseline parts get shorter docs.

Usage: python -m scripts.embed_parts
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import PARTS_BY_PS_JSON
from app.data.chroma_store import get_parts_collection
from app.data.embeddings import embed_texts

BATCH_SIZE = 50  # Gemini embedding API batch limit


def build_part_document(part: dict) -> str:
    """Build a search-optimized text document from structured part fields."""
    lines = []

    # Name and identifiers
    name = part.get("name", "Unknown Part")
    brand = part.get("brand", "")
    ps = part.get("ps_number", "")
    mfg = part.get("mfg_part_number", "")
    appliance = part.get("appliance_type", "")

    lines.append(f"{name} by {brand}. {ps} / {mfg}.")

    if appliance:
        lines.append(f"Appliance type: {appliance}.")

    # Price and rating
    price = part.get("price", "")
    rating = part.get("rating", "")
    reviews = part.get("review_count", "")
    stock = "In stock" if part.get("in_stock") else "Out of stock"

    if price:
        price_line = f"${price}, {stock}."
        if rating:
            price_line = f"${price}, {rating} stars"
            if reviews:
                price_line += f" ({reviews} reviews)"
            price_line += f". {stock}."
        lines.append(price_line)

    # Description (enhanced parts only)
    desc = part.get("description", "")
    if desc:
        # Truncate very long descriptions to keep embedding quality
        if len(desc) > 500:
            desc = desc[:500] + "..."
        lines.append(desc)

    # Symptoms fixed
    symptoms = part.get("symptoms_fixed", [])
    if symptoms:
        lines.append(f"Fixes symptoms: {', '.join(symptoms)}.")

    # Installation info
    difficulty = part.get("installation_difficulty", "")
    install_time = part.get("installation_time", "")
    if difficulty:
        install_line = f"Installation: {difficulty}"
        if install_time:
            install_line += f", {install_time}"
        lines.append(install_line + ".")

    return "\n".join(lines)


def build_metadata(part: dict) -> dict:
    """Build ChromaDB metadata dict for a part."""
    has_desc = bool(part.get("description", "").strip())
    return {
        "ps_number": part.get("ps_number", ""),
        "appliance_type": part.get("appliance_type", ""),
        "brand": part.get("brand", ""),
        "data_tier": "enhanced" if has_desc else "baseline",
        "has_description": has_desc,
    }


def main():
    print("Loading parts data...")
    with open(PARTS_BY_PS_JSON) as f:
        parts_by_ps = json.load(f)

    print(f"Building documents for {len(parts_by_ps)} parts...")
    ps_numbers = list(parts_by_ps.keys())
    documents = []
    metadatas = []

    for ps in ps_numbers:
        part = parts_by_ps[ps]
        documents.append(build_part_document(part))
        metadatas.append(build_metadata(part))

    # Count tiers
    enhanced = sum(1 for m in metadatas if m["data_tier"] == "enhanced")
    baseline = len(metadatas) - enhanced
    print(f"Enhanced: {enhanced}, Baseline: {baseline}")

    # Embed in batches
    collection = get_parts_collection()
    total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"Embedding {len(documents)} parts in {total_batches} batches...")

    for i in range(0, len(documents), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch_docs = documents[i : i + BATCH_SIZE]
        batch_ids = ps_numbers[i : i + BATCH_SIZE]
        batch_meta = metadatas[i : i + BATCH_SIZE]

        # Embed
        embeddings = embed_texts(batch_docs, task_type="RETRIEVAL_DOCUMENT")

        # Upsert into ChromaDB
        collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=embeddings,
            metadatas=batch_meta,
        )

        print(f"  Batch {batch_num}/{total_batches} ({len(batch_docs)} parts)")

        # Rate limiting — be gentle with the API
        if batch_num < total_batches:
            time.sleep(0.5)

    print(f"\nDone! {collection.count()} parts in ChromaDB 'parts' collection.")


if __name__ == "__main__":
    main()

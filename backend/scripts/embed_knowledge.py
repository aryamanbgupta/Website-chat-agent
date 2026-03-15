"""One-time script: embed repair guides + blog articles into ChromaDB knowledge collection.

- Repair guides: 1 overview doc + 1 doc per structured cause (~51 vectors)
- Blogs: split by H2 headings (~150-200 chunks)

Usage: python -m scripts.embed_knowledge
"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import BLOGS_JSON, REPAIRS_ALL_JSON
from app.data.chroma_store import get_knowledge_collection
from app.data.embeddings import embed_texts

BATCH_SIZE = 50


def build_repair_chunks(repairs: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    """Split repair guides into overview + per-cause chunks.

    Handles 3 guide types: generic, brand_specific, and howto.
    For howto guides, uses title/action instead of symptom for the overview.
    """
    ids = []
    documents = []
    metadatas = []

    for repair_idx, repair in enumerate(repairs):
        guide_type = repair.get("guide_type", "generic")
        symptom = repair.get("symptom", "")
        appliance = repair.get("appliance_type", "")
        description = repair.get("description", "")
        title = repair.get("title", symptom)
        action = repair.get("action", "")

        # For howto guides, use title as the identifier (no symptom field)
        # Include index to guarantee uniqueness across guides with same identifier
        identifier = f"{repair_idx}:{symptom or action or title}"
        if not (symptom or action or title):
            continue

        # Overview doc
        overview_parts = [f"Repair Guide: {title}"]
        if action:
            overview_parts.append(f"Action: {action}")
        if description:
            overview_parts.append(description)
        if repair.get("difficulty"):
            overview_parts.append(f"Difficulty: {repair['difficulty']}")
        if repair.get("percentage"):
            overview_parts.append(f"Frequency: {repair['percentage']}% of {appliance} repairs")
        causes = repair.get("causes", [])
        if causes:
            overview_parts.append(f"Common causes: {', '.join(causes)}")
        part_names = repair.get("part_names", [])
        if part_names:
            overview_parts.append(f"Parts involved: {', '.join(part_names)}")

        overview_text = "\n".join(overview_parts)
        if len(overview_text.strip()) > 20:
            doc_id = f"repair:{guide_type}:{appliance}:{identifier}:overview"
            ids.append(doc_id)
            documents.append(overview_text)
            metadatas.append({
                "source_type": "repair_guide",
                "appliance_type": appliance,
                "content_type": "overview",
                "symptom": symptom,
                "guide_type": guide_type,
                "chunk_type": "repair_guide",
            })

        # Per-cause chunks
        for cause in repair.get("structured_causes", []):
            cause_name = cause.get("cause", "")
            cause_desc = cause.get("description", "")
            if not cause_name or not cause_desc:
                continue

            cause_text = (
                f"Repair Guide: {title} — Cause: {cause_name}\n"
                f"Appliance: {appliance}\n"
                f"Symptom: {symptom}\n\n"
                f"{cause_desc}"
            )

            doc_id = f"repair:{guide_type}:{appliance}:{identifier}:{cause_name}"
            ids.append(doc_id)
            documents.append(cause_text)
            metadatas.append({
                "source_type": "repair_guide",
                "appliance_type": appliance,
                "content_type": "cause",
                "symptom": symptom,
                "cause_name": cause_name,
                "guide_type": guide_type,
                "chunk_type": "repair_guide",
            })

    return ids, documents, metadatas


def build_blog_chunks(blogs: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    """Split blog articles by H2 headings into self-contained chunks."""
    ids = []
    documents = []
    metadatas = []

    for blog_idx, blog in enumerate(blogs):
        title = blog.get("title", "")
        markdown = blog.get("raw_markdown", "")
        appliance = blog.get("appliance_type", "")
        content_type = blog.get("content_type", "")
        brands = blog.get("brands_mentioned", [])
        url = blog.get("url", "")

        if not markdown or len(markdown.strip()) < 50:
            continue

        # Split by H2 headings
        chunks = _split_by_h2(markdown, title)

        for chunk_idx, (heading, content) in enumerate(chunks):
            if len(content.strip()) < 30:
                continue

            chunk_text = f"{title}\n\n"
            if heading and heading != title:
                chunk_text += f"## {heading}\n\n"
            chunk_text += content

            # Truncate very long chunks
            if len(chunk_text) > 3000:
                chunk_text = chunk_text[:3000] + "..."

            doc_id = f"blog:{blog_idx}:{chunk_idx}"
            ids.append(doc_id)
            documents.append(chunk_text)

            meta = {
                "source_type": "blog",
                "appliance_type": appliance,
                "content_type": content_type,
                "chunk_type": "blog",
                "title": title,
                "url": url,
            }
            if brands:
                meta["brands_mentioned"] = ", ".join(brands)
            metadatas.append(meta)

    return ids, documents, metadatas


def _split_by_h2(markdown: str, title: str) -> list[tuple[str, str]]:
    """Split markdown by ## headings. Returns list of (heading, content) tuples."""
    # Split on H2 markers
    pattern = r"(?:^|\n)## (.+)"
    splits = re.split(pattern, markdown)

    chunks = []
    if splits[0].strip():
        # Content before first H2 — use article title as heading
        chunks.append((title, splits[0].strip()))

    # Pair up headings with their content
    for i in range(1, len(splits), 2):
        heading = splits[i].strip()
        content = splits[i + 1].strip() if i + 1 < len(splits) else ""
        if content:
            chunks.append((heading, content))

    # If no H2 splits found, treat whole article as one chunk
    if not chunks:
        chunks.append((title, markdown.strip()))

    return chunks


def main():
    # Load data — flatten all 3 sub-lists, filter out "Page Not Found" brand guides
    print("Loading repair guides from repairs_all.json...")
    with open(REPAIRS_ALL_JSON) as f:
        repairs_all = json.load(f)

    repairs = []
    for guide in repairs_all.get("generic_symptom_guides", []):
        guide["guide_type"] = "generic"
        repairs.append(guide)
    for guide in repairs_all.get("brand_specific_guides", []):
        if guide.get("title", "").strip() == "Page Not Found":
            continue
        guide["guide_type"] = "brand_specific"
        repairs.append(guide)
    for guide in repairs_all.get("howto_guides", []):
        guide["guide_type"] = "howto"
        repairs.append(guide)
    print(f"  {len(repairs)} guides after filtering")

    print("Loading blog articles...")
    with open(BLOGS_JSON) as f:
        blogs = json.load(f)

    # Build chunks
    print("Building repair guide chunks...")
    repair_ids, repair_docs, repair_meta = build_repair_chunks(repairs)
    print(f"  {len(repair_ids)} repair chunks")

    print("Building blog chunks...")
    blog_ids, blog_docs, blog_meta = build_blog_chunks(blogs)
    print(f"  {len(blog_ids)} blog chunks")

    # Combine
    all_ids = repair_ids + blog_ids
    all_docs = repair_docs + blog_docs
    all_meta = repair_meta + blog_meta
    print(f"Total knowledge chunks: {len(all_ids)}")

    # Embed and upsert in batches
    collection = get_knowledge_collection()
    total_batches = (len(all_docs) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"Embedding {len(all_docs)} chunks in {total_batches} batches...")

    for i in range(0, len(all_docs), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch_docs = all_docs[i : i + BATCH_SIZE]
        batch_ids = all_ids[i : i + BATCH_SIZE]
        batch_meta = all_meta[i : i + BATCH_SIZE]

        embeddings = embed_texts(batch_docs, task_type="RETRIEVAL_DOCUMENT")

        collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=embeddings,
            metadatas=batch_meta,
        )

        print(f"  Batch {batch_num}/{total_batches} ({len(batch_docs)} chunks)")

        if batch_num < total_batches:
            time.sleep(0.5)

    print(f"\nDone! {collection.count()} chunks in ChromaDB 'knowledge' collection.")


if __name__ == "__main__":
    main()

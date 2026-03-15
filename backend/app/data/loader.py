"""Load all JSON data files into memory at startup."""

import json
from collections import defaultdict

from app.config import (
    BLOGS_JSON,
    MODELS_INDEX_JSON,
    PARTS_BY_PS_JSON,
    REPAIRS_ALL_JSON,
    REPAIRS_JSON,
    SYMPTOMS_INDEX_JSON,
)

# Global data stores — populated by load_all()
parts_by_ps: dict[str, dict] = {}
models_index: dict[str, list[str]] = {}
symptoms_index: dict[str, list[str]] = {}
repairs: list[dict] = []          # 22 generic guides (backward compat)
repairs_all: dict = {}            # raw 3-key dict from repairs_all.json
all_repairs: list[dict] = []      # flattened 149+ guides (filtered)
blogs: list[dict] = []

# Derived indexes — built by load_all()
keyword_index: dict[str, set[str]] = defaultdict(set)


def load_all() -> None:
    """Load all data files into module-level globals."""
    global parts_by_ps, models_index, symptoms_index, repairs, repairs_all, all_repairs, blogs

    with open(PARTS_BY_PS_JSON) as f:
        parts_by_ps = json.load(f)

    with open(MODELS_INDEX_JSON) as f:
        models_index = json.load(f)

    with open(SYMPTOMS_INDEX_JSON) as f:
        symptoms_index = json.load(f)

    with open(REPAIRS_JSON) as f:
        repairs = json.load(f)

    with open(REPAIRS_ALL_JSON) as f:
        repairs_all = json.load(f)

    # Build flat list from all 3 sub-lists, filtering out "Page Not Found" entries
    all_repairs = []
    for guide in repairs_all.get("generic_symptom_guides", []):
        guide["guide_type"] = "generic"
        all_repairs.append(guide)
    for guide in repairs_all.get("brand_specific_guides", []):
        if guide.get("title", "").strip() == "Page Not Found":
            continue
        guide["guide_type"] = "brand_specific"
        all_repairs.append(guide)
    for guide in repairs_all.get("howto_guides", []):
        guide["guide_type"] = "howto"
        all_repairs.append(guide)

    with open(BLOGS_JSON) as f:
        blogs = json.load(f)

    _build_keyword_index()

    print(
        f"Loaded: {len(parts_by_ps)} parts, {len(models_index)} models, "
        f"{len(symptoms_index)} symptoms, {len(repairs)} generic repairs, "
        f"{len(all_repairs)} total repairs, {len(blogs)} blogs"
    )


def _build_keyword_index() -> None:
    """Build an inverted index of name words -> PS numbers for keyword fallback."""
    keyword_index.clear()
    stop_words = {
        "the", "a", "an", "and", "or", "for", "of", "to", "in", "by", "is",
        "with", "-", "&", "replacement", "part",
    }
    for ps_number, part in parts_by_ps.items():
        name = part.get("name", "")
        words = name.lower().split()
        for word in words:
            cleaned = word.strip(".,()-/")
            if cleaned and cleaned not in stop_words and len(cleaned) > 2:
                keyword_index[cleaned].add(ps_number)

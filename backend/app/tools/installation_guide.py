"""get_installation_guide tool — installation info and repair guide lookup."""

from app.data import loader
from app.data.search import search_repairs


def get_installation_guide(
    reasoning: str,
    part_number: str | None = None,
    symptom: str | None = None,
    appliance_type: str | None = None,
) -> dict:
    """Get installation/repair guidance.

    Part-based: look up difficulty, time, video from parts data.
    Symptom-based: look up repair guide for step-by-step instructions.
    Cross-references part names against repair guide causes.
    """
    result = {
        "found": False,
        "part_info": None,
        "repair_guide": None,
        "related_guide": None,
    }

    # Part-based lookup
    if part_number:
        ps = part_number.strip().upper()
        if not ps.startswith("PS"):
            ps = f"PS{ps}"

        part = loader.parts_by_ps.get(ps)
        if part:
            result["found"] = True
            result["part_info"] = {
                "ps_number": ps,
                "name": part.get("name", ""),
                "installation_difficulty": part.get("installation_difficulty", ""),
                "installation_time": part.get("installation_time", ""),
                "installation_notes": part.get("installation_notes", ""),
                "video_url": part.get("video_url", ""),
                "source_url": part.get("source_url", ""),
            }

            # Cross-reference: find repair guides that mention this part's name
            part_name = part.get("name", "").lower()
            part_appliance = part.get("appliance_type", appliance_type or "")
            for repair in loader.all_repairs:
                if repair.get("appliance_type", "") != part_appliance:
                    continue
                # Check if any cause name appears in the part name
                for cause_name in repair.get("causes", []):
                    if _name_overlap(cause_name, part_name):
                        guide = _format_repair_guide(repair)
                        result["related_guide"] = guide
                        break
                if result["related_guide"]:
                    break

    # Symptom-based lookup
    if symptom:
        guide = _find_repair_guide(symptom, appliance_type)
        if guide:
            result["found"] = True
            result["repair_guide"] = guide

    if not result["found"]:
        if part_number:
            result["message"] = f"No installation guide found for {part_number}."
        elif symptom:
            result["message"] = f"No repair guide found for symptom: {symptom}."
        else:
            result["message"] = "Please provide a part number or symptom to look up."

    return result


def _find_repair_guide(symptom: str, appliance_type: str | None) -> dict | None:
    """Find a repair guide matching the symptom.

    Uses embedding-based search (with word-overlap fallback) to find the
    best-matching repair guide from all 149 guides.
    """
    matches = search_repairs(symptom, appliance_type=appliance_type, top_k=1)
    if not matches:
        return None
    return _format_repair_guide(matches[0])


def _format_repair_guide(repair: dict) -> dict:
    """Format a repair guide for output."""
    causes = []
    for sc in repair.get("structured_causes", []):
        cause = {
            "cause": sc.get("cause", ""),
            "description": sc.get("description", "")[:500],
            "recommended_parts": sc.get("recommended_parts", []),
        }
        if sc.get("likelihood"):
            cause["likelihood"] = sc["likelihood"]
        causes.append(cause)

    return {
        "symptom": repair.get("symptom", ""),
        "appliance_type": repair.get("appliance_type", ""),
        "title": repair.get("title", ""),
        "description": repair.get("description", ""),
        "difficulty": repair.get("difficulty", ""),
        "percentage": repair.get("percentage", ""),
        "causes": causes if causes else repair.get("causes", []),
        "steps": repair.get("steps", []),
        "video_url": repair.get("video_url", ""),
        "source_url": repair.get("source_url", ""),
    }


def _name_overlap(cause_name: str, part_name: str) -> bool:
    """Check if a cause name meaningfully overlaps with a part name."""
    cause_words = set(cause_name.lower().split()) - {
        "the", "a", "an", "and", "or", "&",
    }
    part_words = set(part_name.split()) - {
        "the", "a", "an", "and", "or", "&",
    }
    overlap = cause_words & part_words
    return len(overlap) >= 2

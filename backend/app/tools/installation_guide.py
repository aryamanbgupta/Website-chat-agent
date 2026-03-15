"""get_installation_guide tool — installation info and repair guide lookup."""

from app.data import loader


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

    Searches all 149 guides (22 generic + 91 brand-specific + 36 how-to).
    For how-to guides, also matches against the action and title fields.
    """
    symptom_lower = symptom.lower().strip()
    best_match = None
    best_score = 0

    for repair in loader.all_repairs:
        if appliance_type and repair.get("appliance_type", "") != appliance_type:
            continue

        repair_symptom = repair.get("symptom", "").lower()

        # Exact match on symptom
        if symptom_lower == repair_symptom:
            return _format_repair_guide(repair)

        # Word overlap scoring across symptom, title, and action fields
        symptom_words = set(symptom_lower.split())

        repair_words = set(repair_symptom.split())
        overlap = len(symptom_words & repair_words)

        # Also check title (brand-specific guides)
        title_lower = repair.get("title", "").lower()
        title_words = set(title_lower.split()) - {"how", "to", "fix", "a", "the"}
        title_overlap = len(symptom_words & title_words)
        if symptom_lower in title_lower:
            title_overlap += 2

        # Also check action field (howto guides)
        action_lower = repair.get("action", "").lower()
        action_overlap = 0
        if action_lower:
            action_words = set(action_lower.split())
            action_overlap = len(symptom_words & action_words)
            if symptom_lower in action_lower or action_lower in symptom_lower:
                action_overlap += 2

        best_field_score = max(overlap, title_overlap, action_overlap)

        if best_field_score > best_score:
            best_score = best_field_score
            best_match = repair

    if best_match and best_score >= 1:
        return _format_repair_guide(best_match)

    return None


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

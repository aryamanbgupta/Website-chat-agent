"""diagnose_symptom tool — symptom matching + cause-to-part linking."""

from app.data import loader
from app.data.search import search_knowledge


def diagnose_symptom(
    reasoning: str,
    symptom: str,
    appliance_type: str,
    model_number: str | None = None,
) -> dict:
    """Diagnose an appliance symptom and recommend parts.

    - Fuzzy-matches symptom against 49 keys in symptoms_index
    - Looks up structured causes from repair guides
    - Searches knowledge collection for relevant blog content
    - Links cause names to purchasable parts
    - If model_number provided, filters parts to compatible ones
    """
    # Validate appliance type
    valid_types = {"refrigerator", "dishwasher"}
    if appliance_type.lower() not in valid_types:
        return {
            "found": False,
            "message": (
                f"We specialize in refrigerator and dishwasher parts. "
                f"For {appliance_type} repairs, please visit PartSelect.com."
            ),
        }
    appliance = appliance_type.lower()

    # 1. Match symptom in symptoms_index
    matched_symptom, matched_ps_numbers = _match_symptom(symptom, appliance)

    # 2. Find repair guide
    repair_causes = _get_repair_causes(symptom, appliance)

    # 3. Search knowledge collection for blog content
    knowledge_snippets = search_knowledge(
        query=f"{symptom} {appliance}",
        appliance_type=appliance,
        n_results=3,
    )

    # 4. Build recommended parts from symptom index matches
    recommended_parts = []
    for ps in matched_ps_numbers[:10]:
        part = loader.parts_by_ps.get(ps)
        if not part:
            continue

        # Filter by model compatibility if provided
        if model_number:
            compatible = part.get("compatible_models", [])
            model_parts = loader.models_index.get(model_number.upper(), [])
            if model_number.upper() not in compatible and ps not in model_parts:
                continue

        recommended_parts.append({
            "ps_number": ps,
            "name": part.get("name", ""),
            "brand": part.get("brand", ""),
            "price": part.get("price", ""),
            "rating": part.get("rating", ""),
            "in_stock": part.get("in_stock", False),
            "image_url": part.get("image_url", ""),
            "source_url": part.get("source_url", ""),
        })

    # 5. Enhance causes with part links
    for cause in repair_causes:
        cause_name = cause.get("cause", "").lower()
        cause_parts = []
        for part_data in recommended_parts:
            part_name = part_data.get("name", "").lower()
            # Check if the cause name words appear in the part name
            cause_words = set(cause_name.split()) - {"the", "a", "an", "and", "or", "&"}
            part_words = set(part_name.split())
            if len(cause_words & part_words) >= 1:
                cause_parts.append(part_data["ps_number"])
        cause["linked_parts"] = cause_parts

    # Format knowledge snippets
    slim_snippets = []
    for snippet in knowledge_snippets:
        meta = snippet.get("metadata", {})
        slim_snippets.append({
            "content": snippet.get("content", "")[:500],
            "source_type": meta.get("source_type", ""),
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
        })

    found = bool(matched_symptom or repair_causes or slim_snippets)

    # Suggest follow-up questions
    follow_ups = []
    if recommended_parts and not model_number:
        follow_ups.append("What's your appliance model number? I can check part compatibility.")
    if recommended_parts:
        top_part = recommended_parts[0]["ps_number"]
        follow_ups.append(f"Would you like installation instructions for {top_part}?")

    return {
        "found": found,
        "matched_symptom": matched_symptom or symptom,
        "appliance_type": appliance,
        "causes": repair_causes,
        "recommended_parts": recommended_parts[:5],
        "knowledge_snippets": slim_snippets,
        "follow_up_questions": follow_ups,
        "model_filter_applied": model_number is not None,
        "message": "" if found else f"No specific data found for '{symptom}'. Try describing the issue differently.",
    }


def _match_symptom(symptom: str, appliance_type: str) -> tuple[str, list[str]]:
    """Fuzzy-match symptom against symptoms_index keys.

    Keys are formatted as 'appliance_type:Symptom Name'.
    """
    symptom_lower = symptom.lower().strip()
    best_key = ""
    best_score = 0
    best_ps = []

    for key, ps_list in loader.symptoms_index.items():
        # Parse key format: "appliance_type:Symptom"
        parts = key.split(":", 1)
        if len(parts) != 2:
            continue
        key_appliance, key_symptom = parts
        key_symptom_lower = key_symptom.lower()

        # Filter by appliance type
        if key_appliance != appliance_type:
            continue

        # Exact match
        if symptom_lower == key_symptom_lower:
            return key_symptom, ps_list

        # Word overlap scoring
        symptom_words = set(symptom_lower.split())
        key_words = set(key_symptom_lower.split())
        overlap = len(symptom_words & key_words)

        # Substring match bonus
        if symptom_lower in key_symptom_lower or key_symptom_lower in symptom_lower:
            overlap += 2

        if overlap > best_score:
            best_score = overlap
            best_key = key_symptom
            best_ps = ps_list

    if best_score >= 1:
        return best_key, best_ps

    return "", []


def _get_repair_causes(symptom: str, appliance_type: str) -> list[dict]:
    """Find repair guide causes matching the symptom.

    Searches all 149+ repair guides (generic, brand-specific, how-to).
    For brand-specific guides, also checks the title field since the symptom
    field may contain the brand name instead of the actual symptom.
    """
    symptom_lower = symptom.lower().strip()
    best_match = None
    best_score = 0

    for repair in loader.all_repairs:
        if repair.get("appliance_type", "") != appliance_type:
            continue

        repair_symptom = repair.get("symptom", "").lower()

        # For brand-specific/howto guides, also match against title and action
        title_lower = repair.get("title", "").lower()
        action_lower = repair.get("action", "").lower()

        # Exact match on symptom
        if symptom_lower == repair_symptom:
            best_match = repair
            best_score = 999
            break

        # Word overlap scoring across symptom, title, and action fields
        symptom_words = set(symptom_lower.split())

        # Score against symptom field
        repair_words = set(repair_symptom.split())
        overlap = len(symptom_words & repair_words)
        if symptom_lower in repair_symptom or repair_symptom in symptom_lower:
            overlap += 2

        # Score against title field (brand-specific guides)
        title_words = set(title_lower.split()) - {"how", "to", "fix", "a", "the"}
        title_overlap = len(symptom_words & title_words)
        if symptom_lower in title_lower:
            title_overlap += 2

        # Score against action field (howto guides)
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

    if not best_match or best_score < 1:
        return []

    causes = []
    for sc in best_match.get("structured_causes", []):
        cause_entry = {
            "cause": sc.get("cause", ""),
            "description": sc.get("description", "")[:400],
            "recommended_parts": sc.get("recommended_parts", []),
            "likelihood": sc.get("likelihood", ""),
        }
        if best_match.get("source_url"):
            cause_entry["source_url"] = best_match["source_url"]
        causes.append(cause_entry)

    # If no structured causes, use the simple causes list
    if not causes:
        for cause_name in best_match.get("causes", []):
            cause_entry = {
                "cause": cause_name,
                "description": "",
                "recommended_parts": [],
                "likelihood": "",
            }
            if best_match.get("source_url"):
                cause_entry["source_url"] = best_match["source_url"]
            causes.append(cause_entry)

    return causes

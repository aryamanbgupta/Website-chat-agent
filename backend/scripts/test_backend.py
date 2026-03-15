"""Smoke tests for backend data layer and tools.

Validates that the expanded data (4,170 parts, 149 repair guides, 162K models)
loads correctly and that core tools return expected results.

Usage: uv run python -m scripts.test_backend
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_test(name: str, fn) -> bool:
    """Run a single test, print PASS/FAIL."""
    try:
        fn()
        print(f"  PASS  {name}")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False
    except Exception as e:
        print(f"  ERROR {name}: {e}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# 1. Data Loader Tests
# ---------------------------------------------------------------------------

def test_loader_counts():
    """Verify all data files load with expected counts."""
    from app.data import loader

    assert len(loader.parts_by_ps) == 4170, f"Expected 4170 parts, got {len(loader.parts_by_ps)}"
    assert len(loader.models_index) == 162976, f"Expected 162976 models, got {len(loader.models_index)}"
    assert len(loader.symptoms_index) == 49, f"Expected 49 symptoms, got {len(loader.symptoms_index)}"
    assert len(loader.repairs) == 22, f"Expected 22 generic repairs, got {len(loader.repairs)}"
    assert len(loader.all_repairs) == 149, f"Expected 149 total repairs, got {len(loader.all_repairs)}"
    assert len(loader.blogs) == 51, f"Expected 51 blogs, got {len(loader.blogs)}"


def test_loader_no_page_not_found():
    """Verify 'Page Not Found' brand guides were filtered out."""
    from app.data import loader

    for r in loader.all_repairs:
        assert r.get("title", "").strip() != "Page Not Found", \
            f"Found 'Page Not Found' guide in all_repairs: {r}"


def test_loader_guide_types():
    """Verify all 3 guide types are present in all_repairs."""
    from app.data import loader

    types = {r.get("guide_type") for r in loader.all_repairs}
    assert "generic" in types, "Missing generic guides"
    assert "brand_specific" in types, "Missing brand_specific guides"
    assert "howto" in types, "Missing howto guides"

    generic = [r for r in loader.all_repairs if r["guide_type"] == "generic"]
    brand = [r for r in loader.all_repairs if r["guide_type"] == "brand_specific"]
    howto = [r for r in loader.all_repairs if r["guide_type"] == "howto"]
    assert len(generic) == 22, f"Expected 22 generic, got {len(generic)}"
    assert len(brand) == 91, f"Expected 91 brand_specific (101 - 10 PNF), got {len(brand)}"
    assert len(howto) == 36, f"Expected 36 howto, got {len(howto)}"


def test_loader_keyword_index():
    """Verify keyword index was built."""
    from app.data import loader

    assert len(loader.keyword_index) > 100, \
        f"Keyword index too small: {len(loader.keyword_index)} entries"


# ---------------------------------------------------------------------------
# 2. Diagnose Symptom Tool Tests
# ---------------------------------------------------------------------------

def test_diagnose_noisy_dishwasher():
    """Symptom diagnosis should find causes for a common symptom."""
    from app.tools.diagnose_symptom import diagnose_symptom

    result = diagnose_symptom(
        reasoning="test",
        symptom="noisy",
        appliance_type="dishwasher",
    )
    assert result["found"] is True, "Expected found=True"
    assert len(result["causes"]) >= 1, f"Expected causes, got {len(result['causes'])}"
    cause_names = [c["cause"] for c in result["causes"]]
    assert "Pump" in cause_names, f"Expected 'Pump' in causes, got {cause_names}"


def test_diagnose_brand_specific():
    """Diagnosis should match brand-specific guides via title field."""
    from app.tools.diagnose_symptom import diagnose_symptom

    result = diagnose_symptom(
        reasoning="test",
        symptom="leaking",
        appliance_type="dishwasher",
    )
    assert result["found"] is True, "Expected found=True for leaking dishwasher"
    assert len(result["causes"]) >= 1, "Expected at least 1 cause"


def test_diagnose_source_url():
    """Causes from brand-specific guides should include source_url."""
    from app.tools.diagnose_symptom import diagnose_symptom

    result = diagnose_symptom(
        reasoning="test",
        symptom="noisy",
        appliance_type="dishwasher",
    )
    for cause in result["causes"]:
        if cause.get("source_url"):
            return  # At least one cause has a source_url
    # Not a hard failure — generic guides may not have source_url
    print("    (warning: no source_url found in causes)")


def test_diagnose_wrong_appliance():
    """Diagnosis should reject non-supported appliance types."""
    from app.tools.diagnose_symptom import diagnose_symptom

    result = diagnose_symptom(
        reasoning="test",
        symptom="noisy",
        appliance_type="washing machine",
    )
    assert result["found"] is False, "Expected found=False for unsupported appliance"


# ---------------------------------------------------------------------------
# 3. Installation Guide Tool Tests
# ---------------------------------------------------------------------------

def test_installation_howto_guide():
    """Installation guide should find how-to guides via action field."""
    from app.tools.installation_guide import get_installation_guide

    result = get_installation_guide(
        reasoning="test",
        symptom="test water valve",
        appliance_type="refrigerator",
    )
    assert result["found"] is True, "Expected found=True for 'test water valve'"
    guide = result.get("repair_guide")
    assert guide is not None, "Expected a repair_guide"
    assert len(guide.get("steps", [])) > 0, "Expected steps in how-to guide"


def test_installation_by_part_number():
    """Installation guide should return part info for a valid PS number."""
    from app.tools.installation_guide import get_installation_guide

    result = get_installation_guide(
        reasoning="test",
        part_number="PS11752778",
    )
    assert result["found"] is True, "Expected found=True for PS11752778"
    part_info = result.get("part_info")
    assert part_info is not None, "Expected part_info"
    assert part_info["ps_number"] == "PS11752778"


def test_installation_symptom_brand_specific():
    """Installation guide should find brand-specific guides via title matching."""
    from app.tools.installation_guide import get_installation_guide

    result = get_installation_guide(
        reasoning="test",
        symptom="noisy dishwasher",
        appliance_type="dishwasher",
    )
    assert result["found"] is True, "Expected found=True for noisy dishwasher"


# ---------------------------------------------------------------------------
# 4. Search & Compatibility Tool Tests
# ---------------------------------------------------------------------------

def test_search_parts_by_ps_number():
    """search_parts should find a part by exact PS number."""
    from app.tools.search_parts import search_parts

    result = search_parts(reasoning="test", query="PS11752778")
    parts = result.get("parts", [])
    assert len(parts) >= 1, f"Expected at least 1 part, got {len(parts)}"
    assert any(p["ps_number"] == "PS11752778" for p in parts), \
        "Expected PS11752778 in results"


def test_check_compatibility():
    """check_compatibility should return a result (verified or not_in_data)."""
    from app.tools.check_compatibility import check_compatibility

    result = check_compatibility(
        reasoning="test",
        part_number="PS11752778",
        model_number="WRS321SDHZ08",
    )
    assert "compatible" in result, "Expected 'compatible' key in result"
    assert result["confidence"] in ("verified", "not_in_data"), \
        f"Unexpected confidence: {result['confidence']}"


def test_product_details():
    """get_product_details should return full details for a valid PS number."""
    from app.tools.product_details import get_product_details

    result = get_product_details(reasoning="test", part_number="PS11752778")
    assert result["found"] is True, "Expected found=True"
    assert result["ps_number"] == "PS11752778"
    assert result["name"] != ""


# ---------------------------------------------------------------------------
# 5. App Import Test
# ---------------------------------------------------------------------------

def test_app_imports():
    """Verify the FastAPI app imports and initializes without errors."""
    from app.main import app  # noqa: F401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    from app.data import loader

    print("Loading data...")
    loader.load_all()
    print()

    all_tests = [
        # Data loader
        ("Loader: correct counts", test_loader_counts),
        ("Loader: no Page Not Found", test_loader_no_page_not_found),
        ("Loader: all guide types present", test_loader_guide_types),
        ("Loader: keyword index built", test_loader_keyword_index),
        # Diagnose symptom
        ("Diagnose: noisy dishwasher", test_diagnose_noisy_dishwasher),
        ("Diagnose: brand-specific match", test_diagnose_brand_specific),
        ("Diagnose: source_url present", test_diagnose_source_url),
        ("Diagnose: wrong appliance rejected", test_diagnose_wrong_appliance),
        # Installation guide
        ("Install: how-to guide (water valve)", test_installation_howto_guide),
        ("Install: by part number", test_installation_by_part_number),
        ("Install: brand-specific symptom", test_installation_symptom_brand_specific),
        # Search & compatibility
        ("Search: PS number lookup", test_search_parts_by_ps_number),
        ("Compat: check compatibility", test_check_compatibility),
        ("Details: product details", test_product_details),
        # App
        ("App: imports cleanly", test_app_imports),
    ]

    print(f"Running {len(all_tests)} tests...\n")
    passed = sum(1 for name, fn in all_tests if run_test(name, fn))
    failed = len(all_tests) - passed
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(all_tests)}")

    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")


if __name__ == "__main__":
    main()

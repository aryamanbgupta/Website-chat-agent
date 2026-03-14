"""
PartSelect Scraper — Refrigerator & Dishwasher Focus
=====================================================
Two-phase scraping strategy:
  Phase 1: Load baseline data from reference CSV (9600+ parts with URLs, prices, etc.)
  Phase 2: Enhance top N parts via Firecrawl (adds compatible models, ratings,
           descriptions, images — fields missing from the reference data)
  Phase 3: Scrape repair/troubleshooting guides via Firecrawl
  Phase 4: Export to JSON files for embedding pipeline

Usage:
  # Step 1: Recon — test Firecrawl with 1 page, save raw output for inspection
  export FIRECRAWL_API_KEY=fc-your-key
  python scrape_partselect.py recon

  # Step 2: Full scrape (250 per appliance type)
  python scrape_partselect.py scrape --max-products 250

  # Step 3: Scrape repair guides
  python scrape_partselect.py repairs

  # All at once:
  python scrape_partselect.py all --max-products 250
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PartData:
    """Structured data for a single part."""
    ps_number: str = ""
    mfg_part_number: str = ""
    name: str = ""
    brand: str = ""
    appliance_type: str = ""
    price: str = ""
    in_stock: bool = True
    rating: str = ""
    review_count: str = ""
    description: str = ""
    installation_difficulty: str = ""
    installation_time: str = ""
    installation_notes: str = ""
    compatible_models: list[str] = field(default_factory=list)
    symptoms_fixed: list[str] = field(default_factory=list)
    replace_parts: list[str] = field(default_factory=list)
    image_url: str = ""
    video_url: str = ""
    source_url: str = ""
    raw_markdown: str = ""


@dataclass
class RepairCause:
    """A single cause within a repair guide, linked to its parts."""
    cause: str = ""
    description: str = ""
    recommended_parts: list[str] = field(default_factory=list)
    likelihood: str = ""


@dataclass
class RepairGuide:
    """Structured data for a repair/troubleshooting article."""
    appliance_type: str = ""
    symptom: str = ""
    title: str = ""
    description: str = ""
    percentage: str = ""
    difficulty: str = ""
    causes: list[str] = field(default_factory=list)
    structured_causes: list[dict] = field(default_factory=list)
    recommended_parts: list[str] = field(default_factory=list)
    part_names: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    video_url: str = ""
    source_url: str = ""
    raw_markdown: str = ""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.partselect.com"
REFERENCE_PARTS_CSV = "data/reference_parts.csv"
REFERENCE_REPAIRS_CSV = "data/reference_repairs.csv"
OUTPUT_DIR = "data"
DELAY_BETWEEN_REQUESTS = 1.5  # seconds


# Repair guide URLs (fridge + dishwasher)
REPAIR_PAGES = {
    "refrigerator": [
        "/Repair/Refrigerator/Not-Cooling/",
        "/Repair/Refrigerator/Not-Making-Ice/",
        "/Repair/Refrigerator/Leaking/",
        "/Repair/Refrigerator/Noisy/",
        "/Repair/Refrigerator/Runs-Constantly/",
        "/Repair/Refrigerator/Door-Sweating/",
        "/Repair/Refrigerator/Freezer-Is-Cold-But-Refrigerator-Is-Warm/",
        "/Repair/Refrigerator/Light-Not-Working/",
        "/Repair/Refrigerator/Fridge-Too-Cold/",
        "/Repair/Refrigerator/Water-Dispenser-Not-Working/",
    ],
    "dishwasher": [
        "/Repair/Dishwasher/Not-Draining/",
        "/Repair/Dishwasher/Leaking/",
        "/Repair/Dishwasher/Not-Cleaning-Dishes-Properly/",
        "/Repair/Dishwasher/Not-Drying-Dishes-Properly/",
        "/Repair/Dishwasher/Will-Not-Start/",
        "/Repair/Dishwasher/Door-Latch-Failure/",
        "/Repair/Dishwasher/Noisy/",
        "/Repair/Dishwasher/Will-Not-Fill-With-Water/",
        "/Repair/Dishwasher/Buttons-Do-Not-Work/",
        "/Repair/Dishwasher/Overflowing/",
    ],
}


# ---------------------------------------------------------------------------
# Phase 1: Load baseline data from reference CSV
# ---------------------------------------------------------------------------

def load_reference_parts(csv_path: str, appliance_filter: list[str] = None) -> list[PartData]:
    """Load parts from the reference CSV, optionally filtering by appliance type."""
    parts = []
    seen = set()

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            appliance_types = row.get("appliance_types", "")

            # Filter by appliance type if specified
            if appliance_filter:
                match = False
                for at in appliance_filter:
                    if at.lower() in appliance_types.lower():
                        match = True
                        break
                if not match:
                    continue

            ps_number = row.get("part_id", "")
            if not ps_number or ps_number in seen:
                continue
            seen.add(ps_number)

            # Determine primary appliance type
            at_lower = appliance_types.lower()
            if "refrigerator" in at_lower:
                primary_type = "refrigerator"
            elif "dishwasher" in at_lower:
                primary_type = "dishwasher"
            else:
                primary_type = appliance_types.split(",")[0].strip().rstrip(".").lower()

            # Parse symptoms (pipe-separated in reference data)
            symptoms = []
            raw_symptoms = row.get("symptoms", "")
            if raw_symptoms:
                symptoms = [s.strip() for s in raw_symptoms.split("|") if s.strip()]

            # Parse replace_parts (comma-separated)
            replace_parts = []
            raw_replace = row.get("replace_parts", "")
            if raw_replace:
                replace_parts = [p.strip() for p in raw_replace.split(",") if p.strip()]

            # Clean URL (remove SourceCode tracking param)
            url = row.get("product_url", "")
            if "?SourceCode" in url:
                url = url.split("?SourceCode")[0]

            # Get name: from CSV field, or extract from URL slug
            name = row.get("part_name", "")
            if not name and url:
                name_match = re.search(r"PS\d+-\w+-[\w]+-(.+?)\.htm", url)
                if name_match:
                    name = name_match.group(1).replace("-", " ")

            part = PartData(
                ps_number=ps_number,
                mfg_part_number=row.get("mpn_id", ""),
                name=name,
                brand=row.get("brand", ""),
                appliance_type=primary_type,
                price=row.get("part_price", ""),
                in_stock=row.get("availability", "").lower() == "in stock",
                installation_difficulty=row.get("install_difficulty", "").strip(),
                installation_time=row.get("install_time", "").strip(),
                symptoms_fixed=symptoms,
                replace_parts=replace_parts,
                video_url=row.get("install_video_url", ""),
                source_url=url,
            )
            parts.append(part)

    return parts


def load_reference_repairs(csv_path: str) -> list[RepairGuide]:
    """Load repair guides from the reference CSV."""
    guides = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            product = row.get("Product", "").lower()
            if product not in ("refrigerator", "dishwasher"):
                continue

            # Parse part names
            part_names = []
            raw_parts = row.get("parts", "")
            if raw_parts:
                part_names = [p.strip() for p in raw_parts.split(",") if p.strip()]

            url = row.get("symptom_detail_url", "")

            guide = RepairGuide(
                appliance_type=product,
                symptom=row.get("symptom", ""),
                title=row.get("symptom", ""),
                description=row.get("description", ""),
                percentage=row.get("percentage", ""),
                difficulty=row.get("difficulty", ""),
                part_names=part_names,
                video_url=row.get("repair_video_url", ""),
                source_url=url,
            )
            guides.append(guide)

    return guides


# ---------------------------------------------------------------------------
# Firecrawl backend
# ---------------------------------------------------------------------------

class FirecrawlBackend:
    """Scrapes pages using the Firecrawl API (handles anti-bot)."""

    def __init__(self, api_key: str):
        try:
            from firecrawl import FirecrawlApp
        except ImportError:
            print("Install firecrawl: uv add firecrawl-py")
            sys.exit(1)

        self.app = FirecrawlApp(api_key=api_key)
        print(f"[firecrawl] Initialized with API key: {api_key[:10]}...")

    def fetch_page(self, url: str) -> Optional[dict]:
        """Fetch a page and return {markdown, html, metadata}."""
        try:
            result = self.app.scrape(url, formats=["markdown", "html"])
            return {
                "markdown": result.markdown or "",
                "html": result.html or "",
                "metadata": vars(result.metadata) if result.metadata else {},
                "url": url,
            }
        except Exception as e:
            print(f"  [firecrawl] Error fetching {url}: {e}")
            return None

    def map_site(self, url: str, search: str = None, limit: int = 500) -> list[str]:
        """Use Firecrawl's map API to discover URLs on the site. Returns list of URL strings."""
        try:
            result = self.app.map(url, search=search, limit=limit)
            links = []
            if hasattr(result, "links"):
                raw = result.links or []
            elif isinstance(result, list):
                raw = result
            else:
                return []
            # Handle LinkResult objects or plain strings
            for item in raw:
                if isinstance(item, str):
                    links.append(item)
                elif hasattr(item, "url"):
                    links.append(item.url)
                else:
                    links.append(str(item))
            return links
        except Exception as e:
            print(f"  [firecrawl] Error mapping {url}: {e}")
            return []


# ---------------------------------------------------------------------------
# Parsing: Extract enhanced data from Firecrawl page content
# ---------------------------------------------------------------------------

def parse_product_page(page_data: dict, baseline: PartData = None) -> Optional[PartData]:
    """
    Extract structured PartData from a Firecrawl-scraped page.
    Tuned to the actual PartSelect markdown structure observed via recon.
    If baseline is provided, merge enhanced fields into it.
    """
    md = page_data.get("markdown", "")
    html = page_data.get("html", "")
    url = page_data.get("url", "")

    if not md and not html:
        return baseline

    part = baseline or PartData(source_url=url)
    part.raw_markdown = md[:8000]

    # --- PS number ---
    if not part.ps_number:
        # Pattern: "PartSelect Number PS11752778"
        m = re.search(r"PartSelect\s+Number\s+(PS\d+)", md)
        if m:
            part.ps_number = m.group(1)
        elif "/PS" in url:
            m = re.search(r"/(PS\d+)", url)
            if m:
                part.ps_number = m.group(1)

    if not part.ps_number:
        return None

    # --- Manufacturer part number ---
    # Pattern: "Manufacturer Part Number WPW10321304"
    if not part.mfg_part_number:
        m = re.search(r"Manufacturer\s+Part\s+Number\s+(\S+)", md)
        if m:
            part.mfg_part_number = m.group(1).strip()

    # --- Name ---
    # Pattern: "# Refrigerator Door Shelf Bin WPW10321304" (H1)
    if not part.name:
        h1 = re.search(r"^#\s+(.+)", md, re.M)
        if h1:
            name = h1.group(1).strip()
            # Remove the mfg part number suffix if present
            if part.mfg_part_number and name.endswith(part.mfg_part_number):
                name = name[: -len(part.mfg_part_number)].strip()
            part.name = name

    # --- Brand ---
    # Pattern: "Manufactured by\nWhirlpool"
    if not part.brand:
        m = re.search(r"Manufactured by\s*\n\s*(\w+)", md)
        if m:
            part.brand = m.group(1)
        else:
            m = re.search(r"PS\d+-(\w+)-", url)
            if m:
                part.brand = m.group(1)

    # --- Price ---
    # Pattern: "$46.30" appearing near "In Stock" / "Add to cart"
    if not part.price:
        m = re.search(r"\$(\d{1,4}\.\d{2})\s*\n\s*(?:In Stock|Out of Stock|Special Order)", md)
        if m:
            part.price = m.group(1)
        else:
            m = re.search(r"\$(\d{1,4}\.\d{2})", md)
            if m:
                part.price = m.group(1)

    # --- Rating ---
    # Pattern: "4.9" standalone number in the reviews section, after star characters
    if not part.rating:
        # Look in the Customer Reviews section
        reviews_section = re.search(
            r"Customer Reviews.*?Average Rating:.*?(\d\.\d)\s*\n",
            md, re.S
        )
        if reviews_section:
            part.rating = reviews_section.group(1)

    # --- Review count ---
    # Pattern: "351 Reviews" (appears multiple times, take the first one near rating)
    if not part.review_count:
        m = re.search(r"(\d+)\s+Reviews?\]", md)
        if m:
            part.review_count = m.group(1)
        else:
            m = re.search(r"(\d+)\s+Reviews?", md)
            if m:
                part.review_count = m.group(1)

    # --- Description ---
    # Pattern: "## ... Specifications\n\nDescription text..."
    if not part.description:
        m = re.search(r"##\s+.*?Specifications\s*\n\s*\n(.+?)(?:\n\n|\!\[)", md, re.S)
        if m:
            desc = re.sub(r"\s+", " ", m.group(1)).strip()
            part.description = desc[:500]

        # Fallback: look for "Product Description" section
        if not part.description:
            m = re.search(r"Product Description\s*\n\s*\n(.+?)(?:\n\n|\!\[)", md, re.S)
            if m:
                desc = re.sub(r"\s+", " ", m.group(1)).strip()
                part.description = desc[:500]

    # --- Difficulty ---
    # Pattern: "Really Easy\n\nLess than 15 mins" near top of page
    if not part.installation_difficulty:
        m = re.search(
            r"(Really Easy|Very Easy|Easy|A Bit Difficult|Difficult|Very Difficult)"
            r"\s*\n\s*\n\s*(Less than 15 mins|15 - 30 mins|30 - 60 mins|1- ?2 hours|Over 2 hours)",
            md
        )
        if m:
            part.installation_difficulty = m.group(1)
            part.installation_time = m.group(2)

    # --- Compatible models (CRITICAL for compatibility check) ---
    # Pattern: After "Model Cross Reference" / "This part works with the following models:"
    # Each model: "[10640262010](https://www.partselect.com/Models/10640262010/)"
    if not part.compatible_models:
        models = re.findall(r'/Models/([A-Za-z0-9\-]+)/', md)
        if models:
            part.compatible_models = list(dict.fromkeys(models))  # Dedupe, preserve order

    # --- Symptoms ---
    # Pattern: After "This part fixes the following symptoms:"
    # "- Door won't open or close\n- Ice maker won't dispense ice"
    if not part.symptoms_fixed:
        symptoms_section = re.search(
            r"(?:This part fixes the following symptoms|Fixes these symptoms)[:\s]*\n((?:\s*[-*]\s*.+\n?)+)",
            md, re.I
        )
        if symptoms_section:
            symptoms = re.findall(r"[-*]\s*(.+)", symptoms_section.group(1))
            part.symptoms_fixed = [s.strip() for s in symptoms
                                   if not s.startswith("[") and len(s.strip()) > 3]

    # --- Replace parts ---
    # Pattern: "Part# WPW10321304 replaces these:\n\nAP6019471, 2171046, ..."
    if not part.replace_parts:
        m = re.search(r"replaces these[:\s]*\n\s*\n\s*(.+)", md, re.I)
        if m:
            parts_str = m.group(1).strip()
            part.replace_parts = [p.strip() for p in parts_str.split(",") if p.strip()]

    # --- Image ---
    # Pattern: First product image from Azure CDN
    if not part.image_url:
        m = re.search(
            r"(https://partselectcom-gtcdcddbene3cpes\.z01\.azurefd\.net/\d+-\d+-[MSL]-[^)\s]+\.jpg)",
            md
        )
        if m:
            # Prefer the M (medium) size image
            part.image_url = m.group(1)

    # --- Video ---
    # The part-specific video is under "Part Videos" section heading (standalone line).
    # Avoid matching the nav link "[Part Videos](url)" which appears earlier.
    if not part.video_url:
        # Match "Part Videos" as a standalone section heading (not inside a link)
        part_video_section = re.search(
            r"^Part Videos\s*$.*?youtube\.com/vi/([A-Za-z0-9_-]+)",
            md, re.S | re.M
        )
        if part_video_section:
            part.video_url = f"https://www.youtube.com/watch?v={part_video_section.group(1)}"
        else:
            # Fallback: "Replacing your" pattern near a YouTube thumbnail
            m = re.search(r"Replacing your.*?youtube\.com/vi/([A-Za-z0-9_-]+)", md, re.S)
            if m:
                part.video_url = f"https://www.youtube.com/watch?v={m.group(1)}"

    # --- Stock status ---
    # Check near the price, not the whole page (other products listed below may differ)
    price_area = md[:2000]  # Stock status is always near the top
    if re.search(r"Out of Stock|Special Order", price_area):
        part.in_stock = False
    elif re.search(r"In Stock", price_area):
        part.in_stock = True

    # --- JSON-LD fallback (if HTML available) ---
    if html:
        _parse_jsonld(html, part)

    return part


def _parse_jsonld(html: str, part: PartData):
    """Extract product data from JSON-LD script tags."""
    jsonld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    matches = re.findall(jsonld_pattern, html, re.S)

    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list):
                data = data[0]

            if data.get("@type") != "Product":
                continue

            if not part.name and data.get("name"):
                part.name = data["name"]
            if not part.brand and data.get("brand", {}).get("name"):
                part.brand = data["brand"]["name"]
            if not part.description and data.get("description"):
                part.description = data["description"][:500]
            if not part.image_url and data.get("image"):
                img = data["image"]
                if isinstance(img, list):
                    img = img[0]
                part.image_url = img

            # Offers
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            if not part.price and offers.get("price"):
                part.price = str(offers["price"])
            if offers.get("availability"):
                avail = offers["availability"].lower()
                part.in_stock = "instock" in avail

            # Rating
            rating = data.get("aggregateRating", {})
            if not part.rating and rating.get("ratingValue"):
                part.rating = str(rating["ratingValue"])
            if not part.review_count and rating.get("reviewCount"):
                part.review_count = str(rating["reviewCount"])

        except (json.JSONDecodeError, KeyError, TypeError):
            continue


def parse_repair_page(page_data: dict, baseline: RepairGuide = None) -> Optional[RepairGuide]:
    """Extract structured RepairGuide from a Firecrawl-scraped page."""
    md = page_data.get("markdown", "")
    url = page_data.get("url", "")

    if not md:
        return baseline

    guide = baseline or RepairGuide(source_url=url)
    guide.raw_markdown = md[:8000]

    # Symptom from URL
    if not guide.symptom:
        symptom_match = re.search(r"/Repair/\w+/([\w-]+)/?$", url)
        if symptom_match:
            guide.symptom = symptom_match.group(1).replace("-", " ")

    # Appliance type from URL
    if not guide.appliance_type:
        type_match = re.search(r"/Repair/(\w+)/", url)
        if type_match:
            guide.appliance_type = type_match.group(1).lower()

    # Title (H1)
    if not guide.title:
        title_match = re.search(r"^#\s+(.+)", md, re.M)
        if title_match:
            guide.title = title_match.group(1).strip()
        else:
            meta_title = page_data.get("metadata", {}).get("title", "")
            guide.title = meta_title or guide.symptom

    # --- Parse causes with linked parts (structured) ---
    # Split by H2/H3 headers to find individual cause sections
    sections = re.split(r"(?=#{2,3}\s+)", md)
    structured_causes = []

    for section in sections:
        header_match = re.match(r"#{2,3}\s+(.+)", section)
        if not header_match:
            continue

        cause_title = header_match.group(1).strip()

        # Skip non-cause headers (navigation, footer, etc.)
        skip_words = ["related", "video", "popular", "shop", "about", "contact",
                       "navigation", "menu", "footer", "header", "sign",
                       "click a part", "more repair parts", "repair parts",
                       "start your repair", "price match"]
        if any(w in cause_title.lower() for w in skip_words):
            continue

        # Get the body text after the header
        body = section[header_match.end():]

        # Find PS numbers in this cause section
        ps_numbers = list(set(re.findall(r"PS\d{6,}", body)))

        # Get description (first paragraph)
        desc_lines = [l.strip() for l in body.split("\n") if l.strip() and not l.startswith("#")]
        description = " ".join(desc_lines[:3])[:500]

        if cause_title and (description or ps_numbers):
            structured_causes.append(asdict(RepairCause(
                cause=cause_title,
                description=description,
                recommended_parts=ps_numbers,
            )))

    if structured_causes:
        guide.structured_causes = structured_causes
        # Also flatten causes for backward compat
        guide.causes = [c["cause"] for c in structured_causes]
        # Flatten all PS numbers
        all_ps = []
        for c in structured_causes:
            all_ps.extend(c["recommended_parts"])
        guide.recommended_parts = list(set(all_ps))

    # Steps (numbered items) — associate steps with their cause
    step_matches = re.findall(r"(?:^|\n)\s*\d+[\.\)]\s*(.{20,})", md)
    if step_matches:
        guide.steps = [s.strip() for s in step_matches][:20]

    # Video
    if not guide.video_url:
        m = re.search(r"youtube\.com/vi/([A-Za-z0-9_-]+)", md)
        if m:
            guide.video_url = f"https://www.youtube.com/watch?v={m.group(1)}"

    # Description — first paragraph after the H1
    if not guide.description:
        m = re.search(r"^#\s+.+\n\n(.+?)(?:\n\n|#{2})", md, re.S)
        if m:
            desc = re.sub(r"\s+", " ", m.group(1)).strip()
            # Remove image markdown
            desc = re.sub(r"!\[.*?\]\([^)]+\)", "", desc).strip()
            if len(desc) > 20:
                guide.description = desc[:500]

    return guide


# ---------------------------------------------------------------------------
# Recon: Test Firecrawl with one page
# ---------------------------------------------------------------------------

def run_recon(backend: FirecrawlBackend):
    """Fetch one product page and one repair page, save raw output."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Test with the benchmark product
    test_url = f"{BASE_URL}/PS11752778-Whirlpool-WPW10321304-Water-Inlet-Valve.htm"
    print(f"\n=== RECON: Fetching product page ===")
    print(f"URL: {test_url}")

    page = backend.fetch_page(test_url)
    if page:
        # Save raw markdown
        with open(output_path / "recon_product.md", "w") as f:
            f.write(page.get("markdown", ""))
        print(f"  Saved markdown to data/recon_product.md ({len(page.get('markdown', ''))} chars)")

        # Save raw HTML
        with open(output_path / "recon_product.html", "w") as f:
            f.write(page.get("html", ""))
        print(f"  Saved HTML to data/recon_product.html ({len(page.get('html', ''))} chars)")

        # Try parsing
        part = parse_product_page(page)
        if part:
            print(f"\n  Parsed product:")
            d = asdict(part)
            for k, v in d.items():
                if k == "raw_markdown":
                    print(f"    {k}: ({len(v)} chars)")
                elif k == "compatible_models":
                    print(f"    {k}: {len(v)} models — {v[:5]}...")
                else:
                    print(f"    {k}: {v}")
        else:
            print("  ERROR: Failed to parse product page")
    else:
        print("  ERROR: Failed to fetch product page")

    time.sleep(DELAY_BETWEEN_REQUESTS)

    # Test with a repair guide
    repair_url = f"{BASE_URL}/Repair/Refrigerator/Not-Making-Ice/"
    print(f"\n=== RECON: Fetching repair guide ===")
    print(f"URL: {repair_url}")

    page = backend.fetch_page(repair_url)
    if page:
        with open(output_path / "recon_repair.md", "w") as f:
            f.write(page.get("markdown", ""))
        print(f"  Saved markdown to data/recon_repair.md ({len(page.get('markdown', ''))} chars)")

        guide = parse_repair_page(page)
        if guide:
            print(f"\n  Parsed repair guide:")
            d = asdict(guide)
            for k, v in d.items():
                if k == "raw_markdown":
                    print(f"    {k}: ({len(v)} chars)")
                elif k == "structured_causes":
                    print(f"    {k}: {len(v)} causes")
                    for c in v:
                        print(f"      - {c['cause']}: {len(c['recommended_parts'])} parts")
                else:
                    print(f"    {k}: {v}")
        else:
            print("  ERROR: Failed to parse repair guide")
    else:
        print("  ERROR: Failed to fetch repair guide")


# ---------------------------------------------------------------------------
# Step 0: Explore site via Firecrawl map
# ---------------------------------------------------------------------------

def run_explore(backend: FirecrawlBackend):
    """Use Firecrawl map to discover site URLs and check for missing data sources."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    print("\n" + "=" * 60)
    print("  EXPLORE: Mapping PartSelect URLs via Firecrawl")
    print("=" * 60)

    # Map repair guide URLs
    print("\n  [1/3] Mapping repair pages...")
    repair_urls = backend.map_site(BASE_URL + "/Repair/", search="Repair", limit=200)
    repair_fridge = [u for u in repair_urls if "/Repair/Refrigerator/" in u]
    repair_dish = [u for u in repair_urls if "/Repair/Dishwasher/" in u]
    print(f"    Found {len(repair_urls)} total repair URLs")
    print(f"    Refrigerator repairs: {len(repair_fridge)}")
    print(f"    Dishwasher repairs: {len(repair_dish)}")

    # Check for repair guides we're missing
    known_repair_paths = set()
    for paths in REPAIR_PAGES.values():
        for p in paths:
            known_repair_paths.add(p.rstrip("/"))

    new_repairs = []
    for u in repair_fridge + repair_dish:
        path = u.replace(BASE_URL, "").rstrip("/")
        # Only count leaf repair pages (not the index)
        parts = path.split("/")
        if len(parts) >= 4 and path not in known_repair_paths:
            new_repairs.append(u)

    if new_repairs:
        print(f"    NEW repair guides not in our list: {len(new_repairs)}")
        for u in new_repairs[:10]:
            print(f"      {u}")
    else:
        print(f"    All repair guides accounted for")

    # Map model pages
    print("\n  [2/3] Mapping model pages...")
    model_urls = backend.map_site(BASE_URL + "/Models/", search="Models", limit=200)
    print(f"    Found {len(model_urls)} model page URLs")
    if model_urls:
        print(f"    Sample: {model_urls[:3]}")

    # Map product pages to see total count
    print("\n  [3/3] Mapping product pages...")
    product_urls = backend.map_site(BASE_URL, search="PS", limit=500)
    product_pages = [u for u in product_urls if re.search(r"/PS\d+", u)]
    print(f"    Found {len(product_pages)} product page URLs in map")

    # Compare with reference CSV
    ref_parts = load_reference_parts(REFERENCE_PARTS_CSV, ["refrigerator", "dishwasher"])
    ref_ps = {p.ps_number for p in ref_parts}
    map_ps = set()
    for u in product_pages:
        m = re.search(r"/(PS\d+)", u)
        if m:
            map_ps.add(m.group(1))

    new_in_map = map_ps - ref_ps
    if new_in_map:
        print(f"    Products in map but NOT in reference CSV: {len(new_in_map)}")
        for ps in list(new_in_map)[:5]:
            print(f"      {ps}")
    else:
        print(f"    No new products discovered beyond reference CSV")

    # Save explore results
    explore_data = {
        "repair_urls": {"total": len(repair_urls), "fridge": len(repair_fridge), "dishwasher": len(repair_dish)},
        "new_repair_guides": new_repairs,
        "model_urls_found": len(model_urls),
        "product_urls_found": len(product_pages),
        "new_products_not_in_csv": list(new_in_map),
    }
    with open(output_path / "explore_results.json", "w") as f:
        json.dump(explore_data, f, indent=2)
    print(f"\n  Saved explore_results.json")


# ---------------------------------------------------------------------------
# Main scraper: Enhance reference data with Firecrawl
# ---------------------------------------------------------------------------

def run_scrape(backend: FirecrawlBackend, max_products: int = 250):
    """
    Load reference CSV baseline, then enhance top products via Firecrawl.
    Prioritizes parts that have symptoms (most useful for the agent).
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Load reference data
    print("\n" + "=" * 60)
    print("  PHASE 1: Loading baseline from reference CSV")
    print("=" * 60)

    all_parts = load_reference_parts(
        REFERENCE_PARTS_CSV,
        appliance_filter=["refrigerator", "dishwasher"]
    )
    print(f"  Loaded {len(all_parts)} fridge/dishwasher parts from reference CSV")

    fridge = [p for p in all_parts if p.appliance_type == "refrigerator"]
    dish = [p for p in all_parts if p.appliance_type == "dishwasher"]
    print(f"    Refrigerator: {len(fridge)}")
    print(f"    Dishwasher: {len(dish)}")

    # Sort by usefulness: parts with symptoms first, then by brand diversity
    def sort_key(p):
        score = 0
        if p.symptoms_fixed:
            score += 10
        if p.installation_difficulty:
            score += 5
        if p.video_url:
            score += 3
        return -score  # Descending

    fridge.sort(key=sort_key)
    dish.sort(key=sort_key)

    # Select top N for enhancement
    fridge_to_enhance = fridge[:max_products]
    dish_to_enhance = dish[:max_products]
    to_enhance = fridge_to_enhance + dish_to_enhance

    print(f"\n  Selected {len(to_enhance)} parts for Firecrawl enhancement")
    print(f"    Refrigerator: {len(fridge_to_enhance)}")
    print(f"    Dishwasher: {len(dish_to_enhance)}")

    # Check for checkpoint (resume support)
    checkpoint_path = output_path / "enhance_checkpoint.json"
    enhanced_ps = set()
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            checkpoint_data = json.load(f)
            enhanced_ps = set(checkpoint_data.get("enhanced", []))
        print(f"  Resuming from checkpoint: {len(enhanced_ps)} already enhanced")

    # Phase 2: Enhance via Firecrawl
    print("\n" + "=" * 60)
    print("  PHASE 2: Enhancing with Firecrawl")
    print("=" * 60)

    failed_urls = []
    enhanced_count = 0

    for i, part in enumerate(to_enhance):
        if part.ps_number in enhanced_ps:
            continue

        url = part.source_url
        if not url:
            continue

        print(f"  [{i+1}/{len(to_enhance)}] {part.ps_number} — {part.name[:50]}...")

        page = backend.fetch_page(url)
        if page:
            enhanced = parse_product_page(page, baseline=part)
            if enhanced:
                # Update the part in-place
                idx = to_enhance.index(part)
                to_enhance[idx] = enhanced
                enhanced_ps.add(part.ps_number)
                enhanced_count += 1
            else:
                failed_urls.append(url)
        else:
            failed_urls.append(url)

        # Checkpoint every 25 parts
        if enhanced_count % 25 == 0 and enhanced_count > 0:
            _save_enhance_checkpoint(output_path, enhanced_ps, to_enhance)
            print(f"    Checkpoint: {enhanced_count} enhanced")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n  Enhanced {enhanced_count} parts via Firecrawl")
    if failed_urls:
        print(f"  Failed: {len(failed_urls)} URLs")
        with open(output_path / "failed_urls.json", "w") as f:
            json.dump(failed_urls, f, indent=2)

    # Phase 3: Export
    print("\n" + "=" * 60)
    print("  PHASE 3: Exporting data")
    print("=" * 60)

    # Combine: enhanced parts + remaining non-enhanced parts from reference
    enhanced_ps_set = {p.ps_number for p in to_enhance}
    remaining = [p for p in all_parts if p.ps_number not in enhanced_ps_set]

    final_parts = [asdict(p) for p in to_enhance] + [asdict(p) for p in remaining]

    _save_final(output_path, final_parts)
    _build_indexes(output_path, final_parts)
    _validate_data(final_parts)


def run_repairs(backend: FirecrawlBackend):
    """Scrape repair guides via Firecrawl, merging with reference data."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Load reference repairs as baselines
    print("\n" + "=" * 60)
    print("  Loading baseline repair guides from reference CSV")
    print("=" * 60)

    ref_repairs = load_reference_repairs(REFERENCE_REPAIRS_CSV)
    print(f"  Loaded {len(ref_repairs)} repair guides from reference CSV")

    # Build URL → guide mapping
    url_to_guide = {}
    for g in ref_repairs:
        if g.source_url:
            url_to_guide[g.source_url] = g

    # Scrape each repair page
    print("\n" + "=" * 60)
    print("  Scraping repair guides via Firecrawl")
    print("=" * 60)

    all_repairs = []
    for appliance_type, paths in REPAIR_PAGES.items():
        print(f"\n  [{appliance_type}] {len(paths)} repair guides")

        for path in paths:
            url = BASE_URL + path
            print(f"    {url}")

            # Find baseline if exists
            baseline = url_to_guide.get(url)

            page = backend.fetch_page(url)
            if page:
                guide = parse_repair_page(page, baseline=baseline)
                if guide:
                    all_repairs.append(asdict(guide))
            elif baseline:
                # Use reference data as fallback
                all_repairs.append(asdict(baseline))

            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save
    with open(output_path / "repairs.json", "w") as f:
        json.dump(all_repairs, f, indent=2)
    print(f"\n  Saved repairs.json ({len(all_repairs)} guides)")

    # Summary
    for g in all_repairs:
        causes = g.get("structured_causes", [])
        print(f"    {g['appliance_type']}/{g['symptom']}: {len(causes)} structured causes, "
              f"{len(g.get('recommended_parts', []))} parts")


# ---------------------------------------------------------------------------
# Export and validation helpers
# ---------------------------------------------------------------------------

def _save_enhance_checkpoint(output_path: Path, enhanced_ps: set, parts: list):
    """Save checkpoint during enhancement phase."""
    with open(output_path / "enhance_checkpoint.json", "w") as f:
        json.dump({
            "enhanced": list(enhanced_ps),
            "total": len(parts),
        }, f)


def _save_final(output_path: Path, parts: list):
    """Save all final output files."""
    with open(output_path / "parts.json", "w") as f:
        json.dump(parts, f, indent=2)
    print(f"  Saved parts.json ({len(parts)} products)")

    # Parts lookup (keyed by PS number)
    parts_by_ps = {p["ps_number"]: p for p in parts if p.get("ps_number")}
    with open(output_path / "parts_by_ps.json", "w") as f:
        json.dump(parts_by_ps, f, indent=2)
    print(f"  Saved parts_by_ps.json ({len(parts_by_ps)} entries)")

    # CSV export
    _export_csv(output_path / "parts.csv", parts)
    print(f"  Saved parts.csv")


def _build_indexes(output_path: Path, parts: list):
    """Build derived index files for the agent's tools."""

    # Model → compatible parts index
    model_index: dict[str, list[str]] = {}
    for p in parts:
        for model in p.get("compatible_models", []):
            if model not in model_index:
                model_index[model] = []
            if p["ps_number"] not in model_index[model]:
                model_index[model].append(p["ps_number"])

    with open(output_path / "models_index.json", "w") as f:
        json.dump(model_index, f, indent=2)
    print(f"  Saved models_index.json ({len(model_index)} models)")

    # Symptom → parts index
    symptom_index: dict[str, list[str]] = {}
    for p in parts:
        for symptom in p.get("symptoms_fixed", []):
            key = f"{p['appliance_type']}:{symptom}"
            if key not in symptom_index:
                symptom_index[key] = []
            if p["ps_number"] not in symptom_index[key]:
                symptom_index[key].append(p["ps_number"])

    with open(output_path / "symptoms_index.json", "w") as f:
        json.dump(symptom_index, f, indent=2)
    print(f"  Saved symptoms_index.json ({len(symptom_index)} symptom mappings)")


def _validate_data(parts: list):
    """Report data quality metrics."""
    total = len(parts)
    if total == 0:
        print("\n  No parts to validate!")
        return

    enhanced = [p for p in parts if p.get("raw_markdown")]

    stats = {
        "total_parts": total,
        "enhanced_via_firecrawl": len(enhanced),
        "with_price": sum(1 for p in parts if p.get("price")),
        "with_compatible_models": sum(1 for p in parts if p.get("compatible_models")),
        "with_rating": sum(1 for p in parts if p.get("rating")),
        "with_description": sum(1 for p in parts if p.get("description")),
        "with_image": sum(1 for p in parts if p.get("image_url")),
        "with_video": sum(1 for p in parts if p.get("video_url")),
        "with_symptoms": sum(1 for p in parts if p.get("symptoms_fixed")),
        "with_difficulty": sum(1 for p in parts if p.get("installation_difficulty")),
    }

    # By appliance type
    by_type = {}
    for p in parts:
        at = p.get("appliance_type", "unknown")
        by_type[at] = by_type.get(at, 0) + 1
    stats["by_appliance"] = by_type

    # Average models per enhanced part
    models_counts = [len(p.get("compatible_models", [])) for p in enhanced if p.get("compatible_models")]
    if models_counts:
        stats["avg_models_per_enhanced_part"] = sum(models_counts) / len(models_counts)

    print(f"\n  Data Quality Report:")
    print(f"  {'='*40}")
    for k, v in stats.items():
        if k == "by_appliance":
            print(f"    {k}:")
            for at, count in v.items():
                print(f"      {at}: {count}")
        elif isinstance(v, float):
            print(f"    {k}: {v:.1f}")
        else:
            pct = f" ({v/total*100:.0f}%)" if isinstance(v, int) and k != "total_parts" else ""
            print(f"    {k}: {v}{pct}")

    # Save stats
    output_path = Path(OUTPUT_DIR)
    with open(output_path / "scrape_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\n  Saved scrape_stats.json")


def _export_csv(filepath: Path, parts: list):
    """Export parts to CSV for quick inspection."""
    if not parts:
        return

    fields = [
        "ps_number", "mfg_part_number", "name", "brand",
        "appliance_type", "price", "in_stock", "rating",
        "review_count", "installation_difficulty", "source_url",
    ]
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for p in parts:
            writer.writerow(p)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PartSelect Scraper — Refrigerator & Dishwasher Focus"
    )
    parser.add_argument(
        "command",
        choices=["recon", "explore", "scrape", "repairs", "all", "baseline"],
        help="recon: test 1 page | explore: map site URLs | scrape: enhance products | repairs: scrape guides | all: everything | baseline: export reference data only",
    )
    parser.add_argument(
        "--max-products", type=int, default=250,
        help="Max products per appliance type to enhance (default: 250)",
    )
    parser.add_argument(
        "--output-dir", type=str, default="data",
        help="Output directory (default: data/)",
    )
    args = parser.parse_args()

    global OUTPUT_DIR
    OUTPUT_DIR = args.output_dir

    # "baseline" command doesn't need Firecrawl
    if args.command == "baseline":
        print("Exporting baseline data from reference CSV (no Firecrawl needed)...")
        output_path = Path(OUTPUT_DIR)
        output_path.mkdir(exist_ok=True)

        parts = load_reference_parts(REFERENCE_PARTS_CSV, ["refrigerator", "dishwasher"])
        repairs = load_reference_repairs(REFERENCE_REPAIRS_CSV)

        final_parts = [asdict(p) for p in parts]
        final_repairs = [asdict(r) for r in repairs]

        _save_final(output_path, final_parts)
        _build_indexes(output_path, final_parts)
        _validate_data(final_parts)

        with open(output_path / "repairs.json", "w") as f:
            json.dump(final_repairs, f, indent=2)
        print(f"  Saved repairs.json ({len(final_repairs)} guides)")

        print("\nBaseline export complete! Run 'scrape' with Firecrawl to enhance.")
        return

    # All other commands need Firecrawl
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("Error: Set FIRECRAWL_API_KEY environment variable")
        print("  Get a key at: https://firecrawl.dev")
        sys.exit(1)

    backend = FirecrawlBackend(api_key)

    if args.command == "recon":
        run_recon(backend)
    elif args.command == "explore":
        run_explore(backend)
    elif args.command == "scrape":
        run_scrape(backend, max_products=args.max_products)
    elif args.command == "repairs":
        run_repairs(backend)
    elif args.command == "all":
        run_explore(backend)
        run_scrape(backend, max_products=args.max_products)
        run_repairs(backend)


if __name__ == "__main__":
    main()

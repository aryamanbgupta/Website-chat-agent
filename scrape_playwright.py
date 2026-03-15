"""
Playwright-Based Local Scraper for PartSelect.com
==================================================
Drop-in replacement for Firecrawl backend — uses a real Chromium browser
to bypass Akamai anti-bot, expand AJAX model lists, and scrape unlimited
pages at zero credit cost.

Supports parallel scraping via --slice X/N to split product pages across
multiple processes. Use the `merge` command to combine results afterward.

Usage:
  uv run python scrape_playwright.py recon
  uv run python scrape_playwright.py repairs
  uv run python scrape_playwright.py blogs
  uv run python scrape_playwright.py scrape --slice 1/6
  uv run python scrape_playwright.py scrape --slice 2/6
  ...
  uv run python scrape_playwright.py merge          # combine all slices
"""

import argparse
import asyncio
import json
import random
import time
from dataclasses import asdict
from pathlib import Path

import html2text
from playwright_stealth import Stealth

from scrape_partselect import (
    PartData,
    RepairGuide,
    load_reference_parts,
    load_reference_repairs,
    parse_product_page,
    parse_repair_page,
    _parse_jsonld,
    _save_final,
    _build_indexes,
    _validate_data,
    REPAIR_PAGES,
    BASE_URL,
    REFERENCE_PARTS_CSV,
    REFERENCE_REPAIRS_CSV,
    OUTPUT_DIR,
)
from scrape_blogs import parse_blog_markdown, load_blog_urls, BLOG_CSV


# ---------------------------------------------------------------------------
# HTML → Markdown converter
# ---------------------------------------------------------------------------

def make_html2text():
    """Create an html2text converter matching Firecrawl output style."""
    h = html2text.HTML2Text()
    h.body_width = 0
    h.ignore_images = False
    h.ignore_links = False
    h.protect_links = True
    h.ignore_emphasis = False
    h.skip_internal_links = False
    h.single_line_break = False
    return h


def _strip_boilerplate(html: str) -> str:
    """Remove nav, header, footer from raw HTML before markdown conversion."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    for selector in [
        "header", "footer", "nav",
        ".header", ".footer", ".navbar", ".nav",
        "#header", "#footer", "#nav", "#navbar",
        ".mega-menu", ".megamenu", ".site-header", ".site-footer",
        ".cookie-banner", ".cookie-notice",
        "[role='navigation']", "[role='banner']", "[role='contentinfo']",
    ]:
        for el in soup.select(selector):
            el.decompose()

    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    main = soup.select_one("main, #main, .main-content, [role='main']")
    if main and len(str(main)) > 1000:
        return str(main)

    return str(soup)


# ---------------------------------------------------------------------------
# PlaywrightBackend
# ---------------------------------------------------------------------------

class PlaywrightBackend:
    """Scrapes pages using a local Chromium browser via Playwright."""

    def __init__(
        self,
        headless: bool = True,
        slow_mo: int = 0,
        delay_min: float = 1.0,
        delay_max: float = 3.0,
    ):
        self.headless = headless
        self.slow_mo = slow_mo
        self.delay_min = delay_min
        self.delay_max = delay_max
        self._playwright = None
        self._browser = None
        self._context = None
        self._page_count = 0
        self._converter = make_html2text()
        self._stealth = Stealth()

    async def _launch(self):
        """Launch Chrome with stealth patches."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            channel="chrome",
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        await self._new_context()

        # Warm the session with a homepage visit
        page = await self._context.new_page()
        await self._stealth.apply_stealth_async(page)
        print("[playwright] Warming session with homepage visit...")
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[playwright] Homepage warm-up warning: {e}")
        await page.close()
        print("[playwright] Browser ready")

    async def _new_context(self):
        """Create a new browser context with realistic fingerprint."""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass

        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
        )
        self._page_count = 0

    async def fetch_page(self, url: str, expand_models: bool = False) -> dict | None:
        """Navigate to URL, wait for load, convert HTML→markdown."""
        page = await self._context.new_page()
        await self._stealth.apply_stealth_async(page)

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Only reject hard Akamai blocks (403 with tiny HTML)
            if response and response.status == 403:
                body = await page.content()
                if len(body) < 5000:
                    print(f"  [playwright] HTTP 403 (blocked) for {url}")
                    await page.close()
                    return None
            elif response and response.status >= 400 and response.status != 500:
                print(f"  [playwright] HTTP {response.status} for {url}")
                await page.close()
                return None

            # Wait for dynamic content
            await asyncio.sleep(2)

            # Quick scroll to look human
            await self._random_scroll(page)

            # Optionally expand model list
            if expand_models:
                await self._expand_model_list(page)

            # Extract content
            raw_html = await page.content()
            clean_html = _strip_boilerplate(raw_html)
            markdown = self._converter.handle(clean_html)

            result = {"markdown": markdown, "html": raw_html, "metadata": {}, "url": url}
            if self._is_blocked(result):
                print(f"  [playwright] BOT BLOCKED on {url}")
                await page.close()
                return None

            self._page_count += 1
            await page.close()
            return result

        except Exception as e:
            print(f"  [playwright] Error fetching {url}: {e}")
            try:
                await page.close()
            except Exception:
                pass
            return None

    async def _expand_model_list(self, page):
        """Scroll the .js-infiniteScroll container to load all compatible models."""
        try:
            container = await page.query_selector(".js-infiniteScroll")
            if not container:
                container = await page.query_selector('[class*="infiniteScroll"]')
            if not container:
                return

            prev_count = 0
            for iteration in range(50):
                model_links = await page.query_selector_all('a[href*="/Models/"]')
                current_count = len(model_links)

                if current_count == prev_count and iteration > 0:
                    break
                prev_count = current_count

                await container.evaluate("el => el.scrollTop = el.scrollHeight")
                await asyncio.sleep(0.5)

            model_links = await page.query_selector_all('a[href*="/Models/"]')
            print(f"  [playwright] Expanded models: {len(model_links)}")

        except Exception as e:
            print(f"  [playwright] Model expansion warning: {e}")

    async def _random_scroll(self, page):
        """Quick behavioral scroll."""
        try:
            pct = random.uniform(0.3, 0.7)
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            await asyncio.sleep(random.uniform(0.2, 0.5))
            await page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass

    def _is_blocked(self, result: dict) -> bool:
        """Detect Akamai block pages."""
        html = result.get("html", "")
        md = result.get("markdown", "")

        if len(html) < 5000:
            lower = html.lower()
            if "access denied" in lower or "sec-overlay" in lower:
                return True
            if "reference #" in lower and "akamai" in lower:
                return True

        if len(md) < 500:
            if "access denied" in md.lower():
                return True

        return False

    async def fetch_page_with_retry(
        self, url: str, retries: int = 3, expand_models: bool = False
    ) -> dict | None:
        """Retry with exponential backoff; recreate context on bot detection."""
        backoff = [5, 15, 45]

        for attempt in range(retries + 1):
            result = await self.fetch_page(url, expand_models=expand_models)
            if result is not None:
                return result

            if attempt < retries:
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"  [playwright] Retry {attempt + 1}/{retries} in {wait}s...")
                await asyncio.sleep(wait)
                await self._new_context()

        return None

    async def close(self):
        """Clean up browser resources."""
        for resource in [self._context, self._browser]:
            if resource:
                try:
                    await resource.close()
                except Exception:
                    pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        print("[playwright] Browser closed")


# ---------------------------------------------------------------------------
# ScrapeCheckpoint
# ---------------------------------------------------------------------------

class ScrapeCheckpoint:
    """Track scraping progress for resume support."""

    def __init__(self, path: str):
        self.path = Path(path)
        self._data = {"done": {}, "failed": {}}
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path) as f:
                self._data = json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def is_done(self, key: str) -> bool:
        return key in self._data["done"]

    def mark_done(self, key: str, info: dict = None):
        self._data["done"][key] = info or {}

    def mark_failed(self, key: str, reason: str = ""):
        self._data["failed"][key] = reason

    @property
    def done_count(self) -> int:
        return len(self._data["done"])

    @property
    def failed_count(self) -> int:
        return len(self._data["failed"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_sorted_parts() -> list[PartData]:
    """Load and sort all fridge/dishwasher parts by usefulness."""
    all_parts = load_reference_parts(
        REFERENCE_PARTS_CSV,
        appliance_filter=["refrigerator", "dishwasher"],
    )

    def sort_key(p):
        score = 0
        if p.symptoms_fixed:
            score += 10
        if p.installation_difficulty:
            score += 5
        if p.video_url:
            score += 3
        return -score

    fridge = sorted([p for p in all_parts if p.appliance_type == "refrigerator"], key=sort_key)
    dish = sorted([p for p in all_parts if p.appliance_type == "dishwasher"], key=sort_key)
    return fridge + dish


# ---------------------------------------------------------------------------
# Scrape orchestrators
# ---------------------------------------------------------------------------

async def run_recon(backend: PlaywrightBackend):
    """Test 1 product + 1 repair, validate parser output."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    test_url = f"{BASE_URL}/PS11752778-Whirlpool-WPW10321304-Water-Inlet-Valve.htm"
    print(f"\n=== RECON: Fetching product page ===")
    print(f"URL: {test_url}")

    page = await backend.fetch_page_with_retry(test_url, expand_models=True)
    if page:
        with open(output_path / "recon_product_pw.md", "w") as f:
            f.write(page.get("markdown", ""))
        with open(output_path / "recon_product_pw.html", "w") as f:
            f.write(page.get("html", ""))

        part = parse_product_page(page)
        if part:
            d = asdict(part)
            print(f"\n  Parsed product:")
            for k, v in d.items():
                if k == "raw_markdown":
                    print(f"    {k}: ({len(v)} chars)")
                elif k == "compatible_models":
                    print(f"    {k}: {len(v)} models")
                else:
                    print(f"    {k}: {v}")
        else:
            print("  ERROR: Failed to parse product page")
    else:
        print("  ERROR: Failed to fetch product page")

    await asyncio.sleep(random.uniform(backend.delay_min, backend.delay_max))

    repair_url = f"{BASE_URL}/Repair/Refrigerator/Not-Making-Ice/"
    print(f"\n=== RECON: Fetching repair guide ===")
    print(f"URL: {repair_url}")

    page = await backend.fetch_page_with_retry(repair_url)
    if page:
        with open(output_path / "recon_repair_pw.md", "w") as f:
            f.write(page.get("markdown", ""))

        guide = parse_repair_page(page)
        if guide:
            d = asdict(guide)
            print(f"\n  Parsed repair guide:")
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


async def run_scrape(
    backend: PlaywrightBackend,
    max_products: int = 0,
    batch_size: int = 25,
    skip_models: bool = False,
    slice_spec: str = None,
):
    """Enhance parts from baseline CSV. Supports --slice X/N for parallel scraping."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Load all parts
    all_parts = _get_sorted_parts()
    fridge_count = sum(1 for p in all_parts if p.appliance_type == "refrigerator")
    dish_count = sum(1 for p in all_parts if p.appliance_type == "dishwasher")
    print(f"  Loaded {len(all_parts)} parts (refrigerator: {fridge_count}, dishwasher: {dish_count})")

    # Apply max_products limit (per appliance type)
    if max_products > 0:
        fridge = [p for p in all_parts if p.appliance_type == "refrigerator"][:max_products]
        dish = [p for p in all_parts if p.appliance_type == "dishwasher"][:max_products]
        to_enhance = fridge + dish
    else:
        to_enhance = all_parts

    # Apply slice
    slice_idx = 0
    slice_total = 1
    if slice_spec:
        slice_idx, slice_total = [int(x) for x in slice_spec.split("/")]
        slice_idx -= 1  # convert to 0-based

    chunk_size = len(to_enhance) // slice_total
    remainder = len(to_enhance) % slice_total
    start = slice_idx * chunk_size + min(slice_idx, remainder)
    end = start + chunk_size + (1 if slice_idx < remainder else 0)
    my_parts = to_enhance[start:end]

    slice_label = f"slice {slice_idx + 1}/{slice_total}" if slice_total > 1 else "all"
    print(f"  Scraping {len(my_parts)} parts ({slice_label}, index {start}-{end - 1})")

    # Checkpoint — each slice gets its own file
    suffix = f"_{slice_idx + 1}" if slice_total > 1 else ""
    checkpoint = ScrapeCheckpoint(str(output_path / f"pw_checkpoint{suffix}.json"))
    print(f"  Resume: {checkpoint.done_count} done, {checkpoint.failed_count} failed")

    # Enhance
    enhanced_parts = []
    enhanced_count = 0
    failed_count = 0

    for i, part in enumerate(my_parts):
        if checkpoint.is_done(part.ps_number):
            continue

        url = part.source_url
        if not url:
            continue

        print(f"  [{i + 1}/{len(my_parts)}] {part.ps_number} — {part.name[:50]}...")

        page = await backend.fetch_page_with_retry(url, expand_models=not skip_models)
        if page:
            enhanced = parse_product_page(page, baseline=part)
            if enhanced:
                enhanced_parts.append(asdict(enhanced))
                models_count = len(enhanced.compatible_models)
                checkpoint.mark_done(part.ps_number, {"models": models_count})
                enhanced_count += 1
                print(f"    OK: {models_count} models, rating={enhanced.rating}, price={enhanced.price}")
            else:
                checkpoint.mark_failed(part.ps_number, "parse_failed")
                failed_count += 1
        else:
            checkpoint.mark_failed(part.ps_number, "fetch_failed")
            failed_count += 1

        # Checkpoint every batch_size parts
        if (enhanced_count + failed_count) % batch_size == 0 and (enhanced_count + failed_count) > 0:
            checkpoint.save()
            # Also save partial results
            with open(output_path / f"pw_enhanced{suffix}.json", "w") as f:
                json.dump(enhanced_parts, f, indent=2)
            print(f"    [checkpoint: {enhanced_count} enhanced, {failed_count} failed]")

        # Memory management: restart context every 100 pages
        if backend._page_count > 0 and backend._page_count % 100 == 0:
            print(f"    [restarting browser context]")
            await backend._new_context()

        await asyncio.sleep(random.uniform(backend.delay_min, backend.delay_max))

    # Final save
    checkpoint.save()
    with open(output_path / f"pw_enhanced{suffix}.json", "w") as f:
        json.dump(enhanced_parts, f, indent=2)

    print(f"\n  Done: {enhanced_count} enhanced, {failed_count} failed")
    print(f"  Saved to pw_enhanced{suffix}.json")

    # If single process (no slicing), also build final output
    if slice_total == 1:
        _merge_and_export(output_path)


async def _discover_repair_urls(backend: PlaywrightBackend) -> dict:
    """Crawl PartSelect to discover all repair-related URLs for fridge & dishwasher.
    Returns dict with keys: generic_symptoms, brand_indexes, brand_symptoms, howto_pages."""
    brands = ["Whirlpool", "GE", "Samsung", "LG", "Bosch", "Frigidaire",
              "KitchenAid", "Maytag", "Kenmore", "Amana"]

    result = {
        "generic_symptoms": [],   # /Repair/Refrigerator/Not-Cooling/
        "brand_indexes": [],      # /Repair/Dishwasher/Whirlpool/
        "brand_symptoms": [],     # /Repair/Dishwasher/Whirlpool/Noisy/
        "howto_pages": [],        # /dishwasher+replace-motor+repair.htm
    }

    # 1. Generic symptom pages from appliance index
    for appliance in ["Refrigerator", "Dishwasher"]:
        url = f"{BASE_URL}/Repair/{appliance}/"
        page_data = await backend.fetch_page(url)
        if not page_data:
            continue

        import re
        # Find symptom sub-pages
        symptom_paths = re.findall(
            rf'/Repair/{appliance}/([\w-]+)/',
            page_data["html"]
        )
        seen = set()
        for slug in symptom_paths:
            if slug in seen or slug in brands:
                continue
            seen.add(slug)
            path = f"/Repair/{appliance}/{slug}/"
            result["generic_symptoms"].append(path)

        # Find repair.htm how-to links
        howto_paths = re.findall(
            rf'/(?:refrigerator|dishwasher)\+[\w-]+\+repair\.htm',
            page_data["html"],
            re.I,
        )
        for h in howto_paths:
            if h not in result["howto_pages"]:
                result["howto_pages"].append(h)

        await asyncio.sleep(1)

    # 2. Brand index pages + their symptom sub-pages
    for appliance in ["Refrigerator", "Dishwasher"]:
        for brand in brands:
            path = f"/Repair/{appliance}/{brand}/"
            result["brand_indexes"].append(path)

            url = f"{BASE_URL}{path}"
            page_data = await backend.fetch_page(url)
            if not page_data:
                continue

            import re
            sub_paths = re.findall(
                rf'/Repair/{appliance}/{brand}/([\w-]+)/',
                page_data["html"]
            )
            seen = set()
            for slug in sub_paths:
                if slug in seen:
                    continue
                seen.add(slug)
                result["brand_symptoms"].append(
                    f"/Repair/{appliance}/{brand}/{slug}/"
                )

            # Also pick up any howto links here
            howto_paths = re.findall(
                rf'/(?:refrigerator|dishwasher)\+[\w-]+\+repair\.htm',
                page_data["html"],
                re.I,
            )
            for h in howto_paths:
                if h not in result["howto_pages"]:
                    result["howto_pages"].append(h)

            await asyncio.sleep(0.5)

    # 3. Scrape each generic symptom page to find more howto links
    for path in result["generic_symptoms"]:
        url = f"{BASE_URL}{path}"
        page_data = await backend.fetch_page(url)
        if not page_data:
            continue

        import re
        howto_paths = re.findall(
            rf'/(?:refrigerator|dishwasher)\+[\w-]+\+repair\.htm',
            page_data["html"],
            re.I,
        )
        for h in howto_paths:
            if h not in result["howto_pages"]:
                result["howto_pages"].append(h)

        await asyncio.sleep(0.5)

    return result


def _parse_howto_page(page_data: dict) -> dict | None:
    """Parse a repair.htm how-to page into a structured dict."""
    import re as _re

    md = page_data.get("markdown", "")
    url = page_data.get("url", "")

    if not md or len(md) < 200:
        return None

    # Title from H1
    title = ""
    m = _re.search(r"^#\s+(.+)", md, _re.M)
    if m:
        title = m.group(1).strip()

    # Appliance type from URL
    appliance_type = ""
    if "refrigerator" in url.lower():
        appliance_type = "refrigerator"
    elif "dishwasher" in url.lower():
        appliance_type = "dishwasher"

    # Extract the repair action from URL: dishwasher+replace-motor+repair.htm → replace motor
    action = ""
    m = _re.search(r'\w+\+([\w-]+)\+repair\.htm', url, _re.I)
    if m:
        action = m.group(1).replace("-", " ")

    # Steps (numbered items)
    steps = _re.findall(r"(?:^|\n)\s*\d+[\.\)]\s*(.{20,})", md)
    steps = [s.strip() for s in steps][:30]

    # Video
    video_url = ""
    m = _re.search(r"youtube\.com/vi/([A-Za-z0-9_-]+)", md)
    if m:
        video_url = f"https://www.youtube.com/watch?v={m.group(1)}"

    # Description — first paragraph after H1
    description = ""
    m = _re.search(r"^#\s+.+\n\n(.+?)(?:\n\n|#{2})", md, _re.S)
    if m:
        desc = _re.sub(r"\s+", " ", m.group(1)).strip()
        desc = _re.sub(r"!\[.*?\]\([^)]+\)", "", desc).strip()
        if len(desc) > 20:
            description = desc[:500]

    # PS numbers mentioned
    ps_numbers = list(set(_re.findall(r"PS\d{6,}", md)))

    return {
        "type": "howto",
        "title": title,
        "appliance_type": appliance_type,
        "action": action,
        "description": description,
        "steps": steps,
        "video_url": video_url,
        "recommended_parts": ps_numbers,
        "source_url": url,
        "raw_markdown": md[:8000],
    }


async def run_repairs(backend: PlaywrightBackend):
    """Scrape ALL repair content: generic symptoms, brand-specific, and how-to pages."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Load reference baselines
    ref_repairs = load_reference_repairs(REFERENCE_REPAIRS_CSV)
    print(f"  Loaded {len(ref_repairs)} baseline repair guides")

    url_to_guide = {}
    for g in ref_repairs:
        if g.source_url:
            url_to_guide[g.source_url] = g

    # Discover all repair URLs
    print("\n  Discovering all repair URLs...")
    urls = await _discover_repair_urls(backend)
    print(f"    Generic symptom pages: {len(urls['generic_symptoms'])}")
    print(f"    Brand index pages: {len(urls['brand_indexes'])}")
    print(f"    Brand-specific symptom pages: {len(urls['brand_symptoms'])}")
    print(f"    How-to pages: {len(urls['howto_pages'])}")
    total = (len(urls["generic_symptoms"]) + len(urls["brand_indexes"])
             + len(urls["brand_symptoms"]) + len(urls["howto_pages"]))
    print(f"    Total to scrape: {total}")

    checkpoint = ScrapeCheckpoint(str(output_path / "pw_repairs_checkpoint.json"))
    print(f"  Resume: {checkpoint.done_count} done, {checkpoint.failed_count} failed")

    all_symptom_guides = []  # RepairGuide dicts
    all_howto_guides = []    # howto dicts

    # --- 1. Generic symptom pages ---
    print(f"\n  === Generic symptom guides ({len(urls['generic_symptoms'])}) ===")
    for path in urls["generic_symptoms"]:
        url = BASE_URL + path
        key = path.strip("/")

        if checkpoint.is_done(key):
            print(f"    SKIP: {path}")
            continue

        print(f"    {path}")
        baseline = url_to_guide.get(url)

        page_data = await backend.fetch_page_with_retry(url)
        if page_data:
            guide = parse_repair_page(page_data, baseline=baseline)
            if guide:
                all_symptom_guides.append(asdict(guide))
                checkpoint.mark_done(key)
                print(f"      OK: {len(guide.structured_causes)} causes")
            else:
                checkpoint.mark_failed(key, "parse_failed")
                if baseline:
                    all_symptom_guides.append(asdict(baseline))
        else:
            checkpoint.mark_failed(key, "fetch_failed")
            if baseline:
                all_symptom_guides.append(asdict(baseline))

        await asyncio.sleep(random.uniform(backend.delay_min, backend.delay_max))

    # --- 2. Brand index pages ---
    print(f"\n  === Brand index pages ({len(urls['brand_indexes'])}) ===")
    brand_index_guides = []
    for path in urls["brand_indexes"]:
        url = BASE_URL + path
        key = path.strip("/")

        if checkpoint.is_done(key):
            print(f"    SKIP: {path}")
            continue

        print(f"    {path}")
        page_data = await backend.fetch_page_with_retry(url)
        if page_data:
            guide = parse_repair_page(page_data)
            if guide:
                brand_index_guides.append(asdict(guide))
                checkpoint.mark_done(key)
                print(f"      OK: {guide.title}")
            else:
                checkpoint.mark_failed(key, "parse_failed")
        else:
            checkpoint.mark_failed(key, "fetch_failed")

        await asyncio.sleep(random.uniform(backend.delay_min, backend.delay_max))

    # --- 3. Brand-specific symptom pages ---
    print(f"\n  === Brand-specific symptom pages ({len(urls['brand_symptoms'])}) ===")
    brand_symptom_guides = []
    for path in urls["brand_symptoms"]:
        url = BASE_URL + path
        key = path.strip("/")

        if checkpoint.is_done(key):
            print(f"    SKIP: {path}")
            continue

        print(f"    {path}")
        page_data = await backend.fetch_page_with_retry(url)
        if page_data:
            guide = parse_repair_page(page_data)
            if guide:
                brand_symptom_guides.append(asdict(guide))
                checkpoint.mark_done(key)
                print(f"      OK: {len(guide.structured_causes)} causes")
            else:
                checkpoint.mark_failed(key, "parse_failed")
        else:
            checkpoint.mark_failed(key, "fetch_failed")

        await asyncio.sleep(random.uniform(backend.delay_min, backend.delay_max))

    # --- 4. How-to pages ---
    print(f"\n  === How-to repair pages ({len(urls['howto_pages'])}) ===")
    for path in urls["howto_pages"]:
        url = BASE_URL + path
        key = path.strip("/")

        if checkpoint.is_done(key):
            print(f"    SKIP: {path}")
            continue

        print(f"    {path}")
        page_data = await backend.fetch_page_with_retry(url)
        if page_data:
            howto = _parse_howto_page(page_data)
            if howto:
                all_howto_guides.append(howto)
                checkpoint.mark_done(key)
                print(f"      OK: {howto['action']}, {len(howto['steps'])} steps")
            else:
                checkpoint.mark_failed(key, "parse_failed")
        else:
            checkpoint.mark_failed(key, "fetch_failed")

        await asyncio.sleep(random.uniform(backend.delay_min, backend.delay_max))

    checkpoint.save()

    # --- Save everything ---
    # Main repairs file (generic symptom guides — backward compatible)
    with open(output_path / "repairs.json", "w") as f:
        json.dump(all_symptom_guides, f, indent=2)
    print(f"\n  Saved repairs.json ({len(all_symptom_guides)} generic symptom guides)")

    # Brand-specific repairs
    all_brand = brand_index_guides + brand_symptom_guides
    with open(output_path / "repairs_by_brand.json", "w") as f:
        json.dump(all_brand, f, indent=2)
    print(f"  Saved repairs_by_brand.json ({len(all_brand)} brand-specific guides)")

    # How-to pages
    with open(output_path / "repairs_howto.json", "w") as f:
        json.dump(all_howto_guides, f, indent=2)
    print(f"  Saved repairs_howto.json ({len(all_howto_guides)} how-to guides)")

    # Combined file with everything
    combined = {
        "generic_symptom_guides": all_symptom_guides,
        "brand_specific_guides": all_brand,
        "howto_guides": all_howto_guides,
    }
    with open(output_path / "repairs_all.json", "w") as f:
        json.dump(combined, f, indent=2)
    total_guides = len(all_symptom_guides) + len(all_brand) + len(all_howto_guides)
    print(f"  Saved repairs_all.json ({total_guides} total guides)")

    # Summary
    print(f"\n  Summary:")
    for g in all_symptom_guides:
        causes = g.get("structured_causes", [])
        print(f"    {g['appliance_type']}/{g['symptom']}: {len(causes)} causes")
    if all_howto_guides:
        print(f"    How-tos: {', '.join(h['action'] for h in all_howto_guides)}")


async def run_blogs(backend: PlaywrightBackend):
    """Scrape blog posts."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    blogs = load_blog_urls(BLOG_CSV)
    print(f"\nFound {len(blogs)} relevant blog posts")

    blogs_path = output_path / "blogs.json"
    existing = {}
    if blogs_path.exists():
        with open(blogs_path) as f:
            for b in json.load(f):
                existing[b["url"]] = b
        print(f"  Loaded {len(existing)} existing (will skip)")

    results = list(existing.values())
    scraped = 0
    failed = 0

    for i, blog in enumerate(blogs):
        if blog["url"] in existing:
            continue

        print(f"  [{i + 1}/{len(blogs)}] {blog['title'][:60]}...")

        page = await backend.fetch_page_with_retry(blog["url"])
        if page:
            md = page.get("markdown", "")
            if md and "Page Not Found" not in md:
                parsed = parse_blog_markdown(md, blog)
                results.append(parsed)
                scraped += 1
                print(f"    OK: {parsed['word_count']} words")
            else:
                print(f"    BLOCKED or not found")
                failed += 1
        else:
            print(f"    ERROR: fetch failed")
            failed += 1

        if scraped > 0 and scraped % 10 == 0:
            with open(blogs_path, "w") as f:
                json.dump(results, f, indent=2)

        await asyncio.sleep(random.uniform(backend.delay_min, backend.delay_max))

    with open(blogs_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  Scraped: {scraped} new, {failed} failed, {len(existing)} cached")
    print(f"  Total blogs: {len(results)}")


# ---------------------------------------------------------------------------
# Merge — combine slice outputs into final data files
# ---------------------------------------------------------------------------

def _merge_and_export(output_path: Path = None):
    """Merge all pw_enhanced*.json slices + baseline into final parts.json."""
    if output_path is None:
        output_path = Path(OUTPUT_DIR)

    # Load all enhanced parts from slice files
    enhanced_by_ps = {}
    slice_files = sorted(output_path.glob("pw_enhanced*.json"))

    if not slice_files:
        print("  No pw_enhanced*.json files found. Run scrape first.")
        return

    for sf in slice_files:
        with open(sf) as f:
            parts = json.load(f)
        for p in parts:
            ps = p.get("ps_number", "")
            if ps:
                enhanced_by_ps[ps] = p
        print(f"  Loaded {len(parts)} parts from {sf.name}")

    print(f"  Total enhanced: {len(enhanced_by_ps)} unique parts")

    # Load baseline
    all_baseline = load_reference_parts(
        REFERENCE_PARTS_CSV,
        appliance_filter=["refrigerator", "dishwasher"],
    )
    print(f"  Baseline: {len(all_baseline)} parts")

    # Merge: enhanced parts override baseline
    final_parts = []
    for p in all_baseline:
        if p.ps_number in enhanced_by_ps:
            final_parts.append(enhanced_by_ps[p.ps_number])
        else:
            final_parts.append(asdict(p))

    _save_final(output_path, final_parts)
    _build_indexes(output_path, final_parts)
    _validate_data(final_parts)

    # Summary
    total_models = sum(len(p.get("compatible_models", [])) for p in final_parts)
    enhanced_count = sum(1 for p in final_parts if p.get("raw_markdown"))
    print(f"\n  Final: {len(final_parts)} parts, {enhanced_count} enhanced, {total_models} total model links")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Playwright-based PartSelect scraper (supports parallel slicing)"
    )
    parser.add_argument(
        "command",
        choices=["recon", "scrape", "repairs", "blogs", "all", "merge"],
        help="recon | scrape | repairs | blogs | all | merge",
    )
    parser.add_argument("--headed", action="store_true", default=False)
    parser.add_argument("--max-products", type=int, default=0,
                        help="Max products per appliance type (0 = all)")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--delay-min", type=float, default=1.0,
                        help="Min delay between requests (default: 1s)")
    parser.add_argument("--delay-max", type=float, default=3.0,
                        help="Max delay between requests (default: 3s)")
    parser.add_argument("--skip-models", action="store_true", default=False)
    parser.add_argument("--slice", type=str, default=None,
                        help="Slice spec for parallel scraping, e.g. 1/6 (slice 1 of 6)")
    args = parser.parse_args()

    # Merge is a pure data operation — no browser needed
    if args.command == "merge":
        print("Merging slice outputs...")
        _merge_and_export()
        return

    async def _run():
        backend = PlaywrightBackend(
            headless=not args.headed,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
        )
        await backend._launch()

        try:
            if args.command == "recon":
                await run_recon(backend)
            elif args.command == "scrape":
                await run_scrape(
                    backend,
                    max_products=args.max_products,
                    batch_size=args.batch_size,
                    skip_models=args.skip_models,
                    slice_spec=args.slice,
                )
            elif args.command == "repairs":
                await run_repairs(backend)
            elif args.command == "blogs":
                await run_blogs(backend)
            elif args.command == "all":
                await run_repairs(backend)
                await run_blogs(backend)
                await run_scrape(
                    backend,
                    max_products=args.max_products,
                    batch_size=args.batch_size,
                    skip_models=args.skip_models,
                    slice_spec=args.slice,
                )
        finally:
            await backend.close()

    asyncio.run(_run())


if __name__ == "__main__":
    main()

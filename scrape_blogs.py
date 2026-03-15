"""
PartSelect Blog Scraper — Scrape fridge/dishwasher blog posts via Firecrawl.
Saves structured data to data/blogs.json for RAG embedding.

Usage:
  uv run python scrape_blogs.py                # scrape all relevant blogs
  uv run python scrape_blogs.py --dry-run      # just list what would be scraped
"""

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BLOG_CSV = "data/github-dta/partselect_blogs.csv"
OUTPUT_DIR = Path("data")
DELAY = 1.5

# Keywords to identify fridge/dishwasher blogs
FRIDGE_KEYWORDS = ["refrigerator", "fridge", "freezer", "ice maker", "ice-maker", "icemaker"]
DISHWASHER_KEYWORDS = ["dishwasher"]


def load_blog_urls(csv_path: str) -> list[dict]:
    """Load blog entries from CSV, filter to fridge/dishwasher only."""
    blogs = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "")
            url = row.get("url", "")
            t_lower = title.lower()

            appliance_type = None
            if any(kw in t_lower for kw in FRIDGE_KEYWORDS):
                appliance_type = "refrigerator"
            elif any(kw in t_lower for kw in DISHWASHER_KEYWORDS):
                appliance_type = "dishwasher"

            if appliance_type:
                # Classify content type from title
                content_type = "general"
                if "error" in t_lower or "code" in t_lower or "blinking" in t_lower:
                    content_type = "error_code"
                elif "how to" in t_lower or "fix" in t_lower or "replace" in t_lower or "repair" in t_lower:
                    content_type = "how_to"
                elif "troubleshoot" in t_lower or "why" in t_lower or "not working" in t_lower or "not cooling" in t_lower:
                    content_type = "troubleshooting"
                elif "clean" in t_lower or "maintenance" in t_lower or "smelly" in t_lower:
                    content_type = "maintenance"
                elif "reset" in t_lower:
                    content_type = "how_to"
                elif "tip" in t_lower or "safe" in t_lower or "storage" in t_lower or "load" in t_lower or "energy" in t_lower:
                    content_type = "tips"

                blogs.append({
                    "title": title,
                    "url": url,
                    "appliance_type": appliance_type,
                    "content_type": content_type,
                })

    return blogs


def parse_blog_markdown(md: str, blog_entry: dict) -> dict:
    """Parse Firecrawl markdown into structured blog data."""
    # Strip boilerplate header/footer
    # Header ends after "Subscribe" line, footer starts at "WRITTEN BY" or "was sucessfully"
    lines = md.split("\n")
    content_start = 0
    content_end = len(lines)

    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            content_start = i
            break

    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() in ("- Post", "- Pin It") or "WRITTEN BY" in lines[i] or "was sucessfully" in lines[i]:
            content_end = i
            break

    clean_lines = lines[content_start:content_end]
    clean_md = "\n".join(clean_lines).strip()

    # Remove social sharing buttons
    clean_md = re.sub(r"^- (Post|Pin It|Share|Subscribe)\s*$", "", clean_md, flags=re.M)
    # Remove "Save!" prefixed image captions
    clean_md = re.sub(r"^Save!", "", clean_md, flags=re.M)
    # Remove "Embed Image" lines
    clean_md = re.sub(r"^Embed Image\s*$", "", clean_md, flags=re.M)
    # Collapse multiple blank lines
    clean_md = re.sub(r"\n{3,}", "\n\n", clean_md)

    # Extract headings
    headings = re.findall(r"^#{1,4}\s+(.+)", clean_md, re.M)

    # Extract YouTube video URLs
    video_urls = []
    yt_ids = re.findall(r"youtube\.com/vi/([A-Za-z0-9_-]+)", clean_md)
    for vid in dict.fromkeys(yt_ids):  # dedupe, preserve order
        video_urls.append(f"https://www.youtube.com/watch?v={vid}")

    # Extract part category links
    part_category_links = re.findall(
        r"\[([^\]]+)\]\((https://www\.partselect\.com/[A-Z][a-zA-Z-]+\.htm)\)",
        clean_md
    )

    # Extract any PS numbers (rare in blogs but possible)
    ps_numbers = list(set(re.findall(r"PS\d{6,}", clean_md)))

    # Extract brand mentions
    brands_found = set()
    for brand in ["Whirlpool", "GE", "Samsung", "LG", "Bosch", "Frigidaire", "KitchenAid", "Maytag", "Kenmore"]:
        if brand.lower() in clean_md.lower():
            brands_found.add(brand)

    # Extract error codes mentioned
    error_codes = re.findall(r"\b[A-Z]?\d{1,3}[A-Z]?\b(?:\s+error|\s+code)", clean_md, re.I)
    error_code_patterns = re.findall(r"(?:error|code)\s+([A-Z]?\d{1,3}[A-Z]?)", clean_md, re.I)

    # Word count
    word_count = len(clean_md.split())

    # Numbered steps count
    steps = re.findall(r"(?:^|\n)\s*\d+[\.\)]\s+.{20,}", clean_md)

    return {
        "title": blog_entry["title"],
        "url": blog_entry["url"],
        "appliance_type": blog_entry["appliance_type"],
        "content_type": blog_entry["content_type"],
        "headings": headings,
        "word_count": word_count,
        "video_urls": video_urls,
        "part_category_links": [{"name": name, "url": url} for name, url in part_category_links],
        "ps_numbers": ps_numbers,
        "brands_mentioned": sorted(brands_found),
        "step_count": len(steps),
        "raw_markdown": clean_md[:12000],  # generous limit for blogs
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape PartSelect blog posts")
    parser.add_argument("--dry-run", action="store_true", help="List blogs without scraping")
    args = parser.parse_args()

    blogs = load_blog_urls(BLOG_CSV)
    print(f"Found {len(blogs)} relevant blog posts (fridge + dishwasher)")

    by_type = {}
    for b in blogs:
        by_type.setdefault(b["appliance_type"], []).append(b)
    for t, bl in sorted(by_type.items()):
        print(f"  {t}: {len(bl)}")

    by_content = {}
    for b in blogs:
        by_content.setdefault(b["content_type"], []).append(b)
    for t, bl in sorted(by_content.items()):
        print(f"  [{t}]: {len(bl)}")

    if args.dry_run:
        print("\n--- DRY RUN: Would scrape these blogs ---")
        for b in blogs:
            print(f"  [{b['appliance_type']}] [{b['content_type']}] {b['title']}")
            print(f"    {b['url']}")
        return

    # Scrape
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("Error: Set FIRECRAWL_API_KEY in .env")
        return

    from firecrawl import FirecrawlApp
    app = FirecrawlApp(api_key=api_key)
    print(f"\nFirecrawl initialized (key: {api_key[:10]}...)")

    # Check for existing data (resume support)
    output_path = OUTPUT_DIR / "blogs.json"
    existing = {}
    if output_path.exists():
        with open(output_path) as f:
            for b in json.load(f):
                existing[b["url"]] = b
        print(f"Loaded {len(existing)} existing blog entries (will skip)")

    results = list(existing.values())
    scraped = 0
    failed = 0

    for i, blog in enumerate(blogs):
        if blog["url"] in existing:
            print(f"  [{i+1}/{len(blogs)}] SKIP (already scraped): {blog['title'][:60]}")
            continue

        print(f"  [{i+1}/{len(blogs)}] {blog['title'][:60]}...")

        try:
            result = app.scrape(blog["url"], formats=["markdown"])
            md = result.markdown or ""

            if md and "Page Not Found" not in md:
                parsed = parse_blog_markdown(md, blog)
                results.append(parsed)
                scraped += 1
                print(f"    OK: {parsed['word_count']} words, {len(parsed['headings'])} sections, {len(parsed['video_urls'])} videos")
            else:
                print(f"    BLOCKED (Page Not Found)")
                failed += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

        # Save checkpoint every 10
        if scraped > 0 and scraped % 10 == 0:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"    [checkpoint: {len(results)} blogs saved]")

        time.sleep(DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Scraped: {scraped} new, {failed} failed, {len(existing)} cached")
    print(f"  Total blogs in blogs.json: {len(results)}")
    print(f"  Saved to {output_path}")

    # Summary stats
    total_words = sum(b.get("word_count", 0) for b in results)
    total_videos = sum(len(b.get("video_urls", [])) for b in results)
    total_steps = sum(b.get("step_count", 0) for b in results)
    by_type = {}
    by_content = {}
    for b in results:
        by_type[b["appliance_type"]] = by_type.get(b["appliance_type"], 0) + 1
        by_content[b["content_type"]] = by_content.get(b["content_type"], 0) + 1

    print(f"\n  Total words: {total_words:,}")
    print(f"  Total videos: {total_videos}")
    print(f"  Total steps: {total_steps}")
    print(f"  By appliance: {by_type}")
    print(f"  By content type: {by_content}")


if __name__ == "__main__":
    main()

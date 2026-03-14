# Data Pipeline Status Report

**Last updated:** 2026-03-14
**Scraper:** `scrape_partselect.py`
**Firecrawl credits remaining:** 324 of 500 (free tier)

---

## Executive Summary

We scraped **101 product pages** and **20 repair guide pages** from PartSelect.com using Firecrawl, enhancing a baseline of **4,170 parts** loaded from a reference CSV. The result is a hybrid dataset: 101 parts with full data (compatible models, ratings, descriptions, images, raw markdown for RAG) and 4,069 parts with baseline data only (name, price, brand, stock status).

**The 101 enhanced parts are the ones to build the agent system against.** They have everything needed for all 5 tools. The remaining 4,069 parts can be enhanced later by re-running the scraper with more Firecrawl credits or from a machine with a non-blocked IP.

---

## Data Files

All files are in the `data/` directory.

| File | Size | Description |
|---|---|---|
| `parts.json` | ~3.2 MB | All 4,170 parts (101 enhanced + 4,069 baseline). This is the primary data store. |
| `parts_by_ps.json` | ~3.3 MB | Same data keyed by PS number for O(1) lookup. Used by `get_product_details` and `check_compatibility`. |
| `parts.csv` | ~729 KB | Flat CSV export of key fields for quick inspection in a spreadsheet. |
| `repairs.json` | ~16 KB | 20 repair/troubleshooting guides (10 fully enhanced, 10 baseline-only). |
| `models_index.json` | ~varies | Model number -> list of compatible PS numbers. **1,500 models** mapped. Used by `check_compatibility`. |
| `symptoms_index.json` | ~52 KB | `appliance_type:symptom` -> list of PS numbers. **48 symptom mappings**. Used by `diagnose_symptom`. |
| `scrape_stats.json` | ~321 B | Data quality metrics snapshot. |
| `explore_results.json` | ~varies | Firecrawl map results from site exploration (repair URLs, model pages discovered). |
| `reference_parts.csv` | ~3.2 MB | **Source CSV** (do not modify). ~9,600 rows, filtered to 4,170 fridge/dishwasher. |
| `reference_repairs.csv` | ~8 KB | **Source CSV** (do not modify). 21 repair guide baselines. |
| `enhance_checkpoint.json` | ~varies | Resume checkpoint for interrupted scrape runs. |
| `recon_product.md` | ~30 KB | Raw Firecrawl markdown from recon (PS11752778). Useful as a reference for parser tuning. |
| `recon_repair.md` | ~10 KB | Raw Firecrawl markdown from recon (Not-Making-Ice repair page). |
| `recon_product.html` | ~155 KB | Raw HTML from recon. Contains JSON-LD structured data. |

---

## Part Data Schema

Every part in `parts.json` / `parts_by_ps.json` has this structure:

```json
{
  "ps_number": "PS11752778",
  "mfg_part_number": "WPW10321304",
  "name": "Refrigerator Door Shelf Bin",
  "brand": "Whirlpool",
  "appliance_type": "refrigerator",
  "price": "36.18",
  "in_stock": true,
  "rating": "4.9",
  "review_count": "351",
  "description": "This refrigerator door bin is a genuine OEM replacement...",
  "installation_difficulty": "",
  "installation_time": "",
  "installation_notes": "",
  "compatible_models": ["WRS321SDHZ08", "WRS588FIHZ04", ...],
  "symptoms_fixed": ["Door won't close", "Ice or frost buildup", "Leaking"],
  "replace_parts": ["AP6019471", "2171046", ...],
  "image_url": "https://partselectcom-gtcdcddbene3cpes.z01.azurefd.net/...",
  "video_url": "https://www.youtube.com/watch?v=...",
  "source_url": "https://www.partselect.com/PS11752778-Whirlpool-WPW10321304-...",
  "raw_markdown": "... 8000 chars of page content for RAG embedding ..."
}
```

### Field Coverage by Data Tier

| Field | Enhanced (101 parts) | Baseline (4,069 parts) | Notes |
|---|---|---|---|
| `ps_number` | 100% | 100% | Primary key |
| `name` | 100% | 100% | From URL slug or CSV |
| `brand` | 100% | 100% | |
| `appliance_type` | 100% | 100% | "refrigerator" or "dishwasher" |
| `price` | 100% | 100% | Enhanced = refreshed from live page |
| `in_stock` | 100% | 72% | Enhanced = verified from live page |
| `source_url` | 100% | 100% | |
| **`compatible_models`** | **95%** (96/101) | **0%** | ~30 models per part. **Critical for `check_compatibility`** |
| **`rating`** | **87%** (88/101) | **0%** | e.g. "4.9" |
| **`review_count`** | **87%** (88/101) | **0%** | e.g. "351" |
| **`description`** | **96%** (97/101) | **0%** | 100-500 chars. **Critical for semantic search / RAG** |
| **`image_url`** | **100%** (101/101) | **0%** | Azure CDN product images |
| **`raw_markdown`** | **100%** (101/101) | **0%** | ~8000 chars for RAG chunking |
| `symptoms_fixed` | varies | 35% (1,460 parts) | From reference CSV |
| `installation_difficulty` | varies | 42% (1,760 parts) | From reference CSV |
| `installation_time` | varies | 42% | From reference CSV |
| `video_url` | varies | 47% (1,971 parts) | YouTube install videos |
| `replace_parts` | varies | 88% | Cross-reference part numbers |

---

## The 101 Enhanced Parts

These are the parts to build and test the agent against. They have **all fields populated** and support every tool.

### Completeness Tiers

- **87 FULL** (models + rating + description + image): best for demos and testing
- **9 MOSTLY** (models + description + image, but no rating): still fully functional
- **5 PARTIAL** (missing models or description): some tools limited

### By Appliance Type

- **51 Refrigerator parts** (including benchmark PS11752778)
- **50 Dishwasher parts**

### Full List — 87 Parts with Complete Data

These parts have compatible_models, rating, review_count, description, image_url, and raw_markdown. Use these as the primary test set.

#### Refrigerator (39 full)

| PS Number | Name | Brand | Price | Rating | Reviews | Models |
|---|---|---|---|---|---|---|
| PS11752778 | Refrigerator Door Shelf Bin | Whirlpool | $36.18 | 4.9 | 351 | 30 |
| PS12728638 | Refrigerator Door Switch | Whirlpool | $38.37 | 4.6 | 95 | 30 |
| PS2121513 | Replacement Ice Maker | Whirlpool | $89.89 | 4.7 | 186 | 30 |
| PS11757023 | Capacitor | Whirlpool | $34.89 | 4.3 | 44 | 30 |
| PS11723171 | Defrost Timer | Whirlpool | $35.85 | 4.2 | 40 | 30 |
| PS395284 | Condenser Fan Motor Kit | Whirlpool | $63.12 | 4.8 | 50 | 30 |
| PS8746522 | Compressor Start Device and Capacitor | Whirlpool | $75.87 | 4.4 | 31 | 30 |
| PS11738900 | Door Light Switch | Whirlpool | $24.89 | 4.2 | 15 | 30 |
| PS11742474 | Bimetal Defrost Thermostat | Whirlpool | $42.45 | 4.8 | 18 | 30 |
| PS11701542 | Admiral Refrigerator Ice and Water Filter | Whirlpool | $62.38 | 4.8 | 111 | 30 |
| PS11722130 | Refrigerator Water Filter | Whirlpool | $62.38 | 4.6 | 99 | 30 |
| PS2580853 | Refrigerator Air Filter | Whirlpool | $21.54 | 4.8 | 44 | 30 |
| PS11722126 | Water Filter | Whirlpool | $90.65 | 4.8 | 36 | 30 |
| PS11738120 | Refrigerator Ice Maker | Whirlpool | $75.92 | 4.5 | 53 | 30 |
| PS12731166 | Door Switch | Whirlpool | $27.62 | 4.8 | 39 | 30 |
| PS11746909 | Admiral Refrigerator Retaining Ring | Whirlpool | $7.87 | 3.7 | 3 | 30 |
| PS12584655 | Admiral Refrigerator SWITCH | Whirlpool | $28.72 | 4.5 | 15 | 30 |
| PS2003478 | Admiral Refrigerator Ice Dispenser Solenoid and Door Kit | Whirlpool | $158.58 | 4.4 | 15 | 30 |
| PS11739763 | Admiral Refrigerator Coupling | Whirlpool | $28.49 | 5.0 | 3 | 30 |
| PS12712096 | Admiral Refrigerator ARM-SHUT | Whirlpool | $46.11 | 4.7 | 6 | 30 |
| PS11743653 | Admiral Refrigerator Ice Bucket | Whirlpool | $155.20 | 4.8 | 10 | 30 |
| PS11747838 | Admiral Refrigerator Ice Maker Helix End Cap | Whirlpool | $17.48 | 4.8 | 11 | 30 |
| PS11743318 | Admiral Refrigerator Water Fill Cup and Bearing | Whirlpool | $40.29 | 4.5 | 10 | 30 |
| PS11738609 | Admiral Refrigerator Ice Maker Auger and Crusher Blade | Whirlpool | $263.05 | 4.5 | 11 | 30 |
| PS11739061 | Admiral Refrigerator Hinge Bracket | Whirlpool | $10.72 | 1.8 | 5 | 30 |
| PS11739043 | Admiral Refrigerator Thimble Top | Whirlpool | $11.13 | 5.0 | 2 | 30 |
| PS2168612 | Admiral Refrigerator Door Closure Cam Kit | Whirlpool | $11.09 | 3.9 | 22 | 30 |
| PS11739877 | Admiral Refrigerator Bottom Door Hinge with Pin | Whirlpool | $11.13 | 4.7 | 3 | 30 |
| PS11739241 | Admiral Refrigerator Seal | Whirlpool | $14.57 | 4.2 | 5 | 30 |
| PS323899 | Admiral Refrigerator Freezer Door Gasket | Whirlpool | $271.91 | 4.3 | 3 | 30 |
| PS11743190 | Admiral Refrigerator Fresh Food Door Gasket | Whirlpool | $225.40 | 4.7 | 3 | 30 |
| PS11743313 | Admiral Refrigerator Cycling Thermostat | Whirlpool | $62.04 | 5.0 | 1 | 30 |
| PS11743599 | Admiral Refrigerator Defrost Thermostat | Whirlpool | $83.37 | 5.0 | 2 | 30 |
| PS11743148 | Admiral Refrigerator Clip-On Defrost Thermostat | Whirlpool | $69.22 | 5.0 | 1 | 30 |
| PS11740613 | Hose Clamp | Whirlpool | $11.09 | 3.0 | 2 | 30 |
| PS11743008 | Hose Clamp | Whirlpool | $11.77 | 5.0 | 1 | 30 |
| PS11738697 | Water Inlet Hose Washer | Whirlpool | $7.95 | 4.5 | 2 | 30 |
| PS258461 | Screw 8-16 hxw 1/2 Stainless Steel | GE | $8.54 | 4.0 | 2 | 30 |
| PS298353 | Push On Nut | GE | $13.82 | 4.8 | 8 | 30 |

#### Dishwasher (48 full)

| PS Number | Name | Brand | Price | Rating | Reviews | Models |
|---|---|---|---|---|---|---|
| PS10065979 | Upper Rack Adjuster Kit | Whirlpool | $39.89 | 4.7 | 730 | 30 |
| PS11753379 | Drain Pump | Whirlpool | $64.05 | 4.8 | 65 | 30 |
| PS5136129 | Door Gasket with Strike - Black | Whirlpool | $57.96 | 4.7 | 66 | 30 |
| PS11746830 | Door Gasket | Whirlpool | $69.71 | 4.5 | 51 | 30 |
| PS11755592 | Lower Spray Arm | Whirlpool | $43.25 | 4.9 | 50 | 30 |
| PS11759673 | Filter | Whirlpool | $31.89 | 4.9 | 40 | 30 |
| PS11745488 | Friction Sleeve | Whirlpool | $7.49 | 4.9 | 37 | 30 |
| PS972316 | Spinner Kit | Whirlpool | $29.50 | 4.9 | 33 | 30 |
| PS11755809 | Door Gasket - Gray | Whirlpool | $68.71 | 4.9 | 32 | 30 |
| PS11751238 | Faucet Adapter | Whirlpool | $54.41 | 4.7 | 26 | 30 |
| PS11745451 | Upper Rack Wheel with Mount | Whirlpool | $29.36 | 4.9 | 67 | 30 |
| PS2358130 | Drain Hose | Whirlpool | $31.57 | 5.0 | 25 | 30 |
| PS11755664 | Middle Spray Arm | Whirlpool | $30.89 | 5.0 | 22 | 30 |
| PS11747717 | Lower Wheel Assembly | Whirlpool | $12.45 | 4.4 | 19 | 30 |
| PS11745525 | Upper Rack Wheel and Mount Assembly | Whirlpool | $11.29 | 5.0 | 18 | 30 |
| PS16221222 | GASKET | Whirlpool | $20.89 | 4.9 | 16 | 30 |
| PS11746591 | Rack Track Stop | Whirlpool | $7.70 | 4.6 | 144 | 30 |
| PS8260087 | Heating Element | Whirlpool | $44.68 | 4.5 | 113 | 30 |
| PS11745496 | Mounting Bracket | Whirlpool | $10.03 | 4.6 | 14 | 30 |
| PS11741429 | Dryer Radiant Flame Sensor | Whirlpool | $47.87 | 4.5 | 12 | 30 |
| PS11741334 | Lower Sprayarm Seal | Whirlpool | $15.96 | 4.7 | 12 | 30 |
| PS285013 | Recess Door Spring | GE | $9.16 | 5.0 | 12 | 30 |
| PS6447735 | Door Handle Fastener | GE | $13.11 | 4.8 | 11 | 30 |
| PS11743423 | High Limit Thermostat | Whirlpool | $20.69 | 4.9 | 9 | 30 |
| PS11741351 | Upper Wash Assembly | Whirlpool | $46.52 | 4.2 | 9 | 30 |
| PS370872 | Detergent Dispenser Cover Kit | Whirlpool | $35.83 | 4.3 | 9 | 30 |
| PS11754873 | Middle Spray Arm | Whirlpool | $32.89 | 4.9 | 9 | 30 |
| PS11738178 | Inlet Fill Hose | Whirlpool | $77.20 | 5.0 | 8 | 30 |
| PS11747612 | Upper Spray Arm Assembly | Whirlpool | $11.05 | 5.0 | 8 | 30 |
| PS11741622 | Push-In Retainer Clip | Whirlpool | $38.93 | 4.3 | 8 | 30 |
| PS11750093 | Positioner | Whirlpool | $32.89 | 3.3 | 7 | 30 |
| PS258167 | Check Valve Flapper | GE | $14.60 | 5.0 | 6 | 30 |
| PS11746834 | White Dishrack Roller | Whirlpool | $17.17 | 3.7 | 6 | 30 |
| PS11745444 | Spray Arm Seal | Whirlpool | $13.69 | 4.2 | 6 | 30 |
| PS11748543 | Inner Door Foam Insulation Strip | Whirlpool | $36.18 | 4.5 | 6 | 30 |
| PS11731683 | Seal | Whirlpool | $57.29 | 3.8 | 13 | 30 |
| PS11757605 | Lower Spray Arm Support | Whirlpool | $64.54 | 4.5 | 4 | 30 |
| PS11745432 | Upper Wash Arm Mount | Whirlpool | $46.01 | 5.0 | 4 | 30 |
| PS11745436 | Spray Arm Seal | Whirlpool | $5.41 | 5.0 | 3 | 30 |
| PS11743058 | Lower Spray Arm - Shield Included | Whirlpool | $75.18 | 5.0 | 3 | 30 |
| PS3651318 | HOSE | Whirlpool | $73.05 | 5.0 | 3 | 30 |
| PS11745437 | Lower Spray Arm Support/Hub | Whirlpool | $49.37 | 5.0 | 3 | 30 |
| PS11738161 | Upper Spray Arm Nut | Whirlpool | $11.09 | 5.0 | 3 | 30 |
| PS1960445 | Soap Cup Door Latch and Gasket | Whirlpool | $10.89 | 5.0 | 2 | 30 |
| PS11740642 | Pump Outlet Seal | Whirlpool | $28.37 | 5.0 | 2 | 30 |
| PS11728058 | Heat Resistant Adhesive | Whirlpool | $23.81 | 5.0 | 1 | 30 |
| PS11753224 | Manifold | Whirlpool | $92.44 | 5.0 | 1 | 30 |
| PS11741308 | Pin (Lid Hinge) | Whirlpool | $12.99 | 5.0 | 1 | 30 |

### 9 Mostly Complete Parts (no rating)

These have compatible_models, description, and image but are missing rating/review_count. All tools work except showing star ratings.

| PS Number | Name | Models |
|---|---|---|
| PS11743189 | Admiral Refrigerator Freezer Door Gasket | 30 |
| PS11738201 | Admiral Refrigerator Bi-Metal Defrost Thermostat | 30 |
| PS11743751 | Admiral Refrigerator Cold Control Thermostat | 30 |
| PS11743796 | Caloric Dishwasher Clamp | 30 |
| PS11747716 | Admiral Dishwasher Top Wash Arm Retainer | 4 |
| PS11746138 | Admiral Dishwasher Gasket | 30 |
| PS11743934 | Estate Dishwasher Rubber Washer | 30 |
| PS11741257 | Estate Dishwasher Torx Screw | 30 |
| PS384950 | Estate Dishwasher Pump Tub Gasket | 30 |

### 5 Partial Parts (missing models or description)

These are missing critical fields. `check_compatibility` won't work for them.

| PS Number | Name | Issue |
|---|---|---|
| PS11757437 | Admiral Dishwasher Inlet Hose Washer | No models, no description |
| PS11770133 | Admiral Refrigerator RELAY-STRT | No models, no description |
| PS11742795 | Admiral Refrigerator Defrost Thermostat | No models, no description |
| PS451462 | Caloric Dishwasher Element Grommet | No models, no description |
| PS11747685 | Admiral Dishwasher Bottom Door Seal | No models |

---

## Repair Guide Data

### Schema

```json
{
  "appliance_type": "dishwasher",
  "symptom": "Not draining",
  "title": "How To Fix A Dishwasher That's Not Draining",
  "description": "If your dishwasher isn't draining...",
  "percentage": "",
  "difficulty": "EASY",
  "causes": ["Piston & Nut Assembly", "Drain Pump & Motor", ...],
  "structured_causes": [
    {
      "cause": "Piston & Nut Assembly",
      "description": "The piston and nut assembly creates a seal...",
      "recommended_parts": [],
      "likelihood": ""
    }
  ],
  "recommended_parts": [],
  "part_names": ["Drain Pump", "Check Valve", ...],
  "steps": ["Step 1...", "Step 2...", ...],
  "video_url": "https://www.youtube.com/watch?v=...",
  "source_url": "https://www.partselect.com/Repair/Dishwasher/Not-Draining/",
  "raw_markdown": "... 8000 chars for RAG embedding ..."
}
```

### 10 Fully Enhanced Guides (structured causes + step-by-step instructions)

| Appliance | Symptom | Causes | Steps | Video |
|---|---|---|---|---|
| Refrigerator | Ice maker not making ice | 4 (Water Fill Tubes, Water Inlet Valve, Ice & Water Filter, Ice Maker Assembly) | 20 | Yes |
| Refrigerator | Leaking | 3 (Door Gaskets, Water Inlet Valve, Ice Maker Assembly) | 12 | Yes |
| Refrigerator | Noisy | 3 (Condenser Fan Motor, Evaporator Fan Motor, Evap Fan Grommet) | 12 | Yes |
| Refrigerator | Door Sweating | 4 (Door Gasket, Dispenser Door, Closure Cam Kit, Door Hinge) | 12 | Yes |
| Refrigerator | Light not working | 4 (Light Bulb, Light Sockets, Door Light Switch, Ice Dispenser) | 16 | Yes |
| Dishwasher | Not draining | 6 (Piston & Nut, Drain Pump, Check Valve, Belt, Timer, Drain Hose) | 20 | Yes |
| Dishwasher | Leaking | 7 (Pump, Door Gasket, Water Inlet Valve, Dispensers, Spray Arm, Float, Hoses) | 20 | Yes |
| Dishwasher | Will not start | 6 (Door Latch, Timer/Control, Selector Switch, Relay, Thermal Fuse, Motor) | 20 | Yes |
| Dishwasher | Door latch failure | 1 (Door Latch Assembly) | 5 | Yes |
| Dishwasher | Noisy | 3 (Pump, Wash Arm Bearing, Spray Arms) | 12 | Yes |

### 10 Baseline-Only Guides (blocked by anti-bot, symptom name only)

These repair page URLs returned "Page Not Found" from Firecrawl (anti-bot protection). They have the symptom name from the URL slug but no structured content. **These are not in the reference CSV** either.

| Appliance | Symptom | Has Data |
|---|---|---|
| Refrigerator | Not Cooling | Symptom name only |
| Refrigerator | Runs Constantly | Symptom name only |
| Refrigerator | Freezer Is Cold But Refrigerator Is Warm | Symptom name only |
| Refrigerator | Fridge Too Cold | Symptom name only |
| Refrigerator | Water Dispenser Not Working | Symptom name only |
| Dishwasher | Not Cleaning Dishes Properly | Symptom name only |
| Dishwasher | Not Drying Dishes Properly | Symptom name only |
| Dishwasher | Will Not Fill With Water | Symptom name only |
| Dishwasher | Buttons Do Not Work | Symptom name only |
| Dishwasher | Overflowing | Symptom name only |

---

## Models Index

`models_index.json` maps **1,500 model numbers** to their compatible parts.

```json
{
  "WRS321SDHZ08": ["PS11752778", "PS11722130"],
  "WDT780SAEM1": ["PS10065979", "PS11746591"],
  ...
}
```

Each enhanced part contributes ~30 model numbers (the Firecrawl scrape captures the first page of AJAX-loaded models; the full list can be longer). This is sufficient for the `check_compatibility` tool to work for demo queries.

**Limitation:** The 30-model cap per part is a Firecrawl limitation — PartSelect loads additional models via AJAX pagination that isn't captured in the initial page render. A direct scraper could get all models by making the AJAX calls.

---

## Symptoms Index

`symptoms_index.json` maps **48 unique symptom strings** to parts. These come from the reference CSV (not Firecrawl), so they cover the full 1,460 parts that have symptoms.

```json
{
  "refrigerator:Won't start": ["PS12728638", "PS12731166", ...],
  "dishwasher:Leaking": ["PS11746830", "PS5136129", ...],
  ...
}
```

This powers the `diagnose_symptom` tool's ability to recommend specific parts for a given symptom.

---

## What Each Agent Tool Needs

| Tool | Required Data | Status |
|---|---|---|
| `search_parts` | name, description, symptoms, raw_markdown (for RAG embedding) | Works fully for 101 enhanced parts (semantic search). Works partially for 4,069 baseline parts (keyword match on name/symptoms only). |
| `check_compatibility` | compatible_models list | Works for **96 parts** across **1,500 models**. Returns "unknown" for the 4,069 baseline parts. |
| `get_product_details` | all fields for product card UI | Full product card (image, rating, price, description) for 101 enhanced parts. Basic card (name, price, brand) for baseline. |
| `get_installation_guide` | difficulty, time, steps, video | Difficulty/time from CSV covers 1,760 parts. Step-by-step instructions only from 10 enhanced repair guides. |
| `diagnose_symptom` | symptom->cause->part mapping | 10 enhanced guides with structured causes (41 causes total). Symptom->part mapping from CSV covers 1,460 parts. |

---

## Recommended Build Strategy

### Phase 1: Build with enhanced data (now)
Build and test all 5 tools against the **87 fully-complete parts**. These parts span both appliance types, have all fields, and cover enough variety (filters, gaskets, motors, switches, thermostats, spray arms, etc.) to demonstrate every tool capability.

**Benchmark queries to test with:**
- "Find a water inlet valve for my refrigerator" -> should return PS11752778 and similar
- "Is PS11752778 compatible with WRS321SDHZ08?" -> should return YES
- "My dishwasher won't drain" -> should trigger diagnose_symptom, return 6 causes
- "How do I install PS10065979?" -> should return difficulty, video
- "Show me details for PS2121513" -> should return full product card with image, rating, 4.7 stars

### Phase 2: Embed for RAG (next)
The 101 enhanced parts each have ~8,000 chars of `raw_markdown` plus structured fields. Chunk and embed these into ChromaDB using Gemini Embedding 2. The 10 enhanced repair guides also have raw_markdown for embedding.

### Phase 3: Extend coverage (later)
Options to enhance more parts:
1. **Re-run scraper** with `--max-products 150` (uses ~200 more credits, ~124 remaining)
2. **Buy Hobby plan** ($16/mo, 3,000 credits) to scrape 1,000+ parts
3. **Direct scraping** from a non-blocked IP (free, unlimited, 1.5s/page)

---

## Scraper Usage Reference

```bash
# Export baseline only (no Firecrawl needed)
uv run python scrape_partselect.py baseline

# Explore site URLs via Firecrawl map
uv run python scrape_partselect.py explore

# Enhance top N parts per appliance type
uv run python scrape_partselect.py scrape --max-products 50

# Scrape repair guides
uv run python scrape_partselect.py repairs

# Do everything (explore + scrape + repairs)
uv run python scrape_partselect.py all --max-products 50

# Test with 1 page (recon)
uv run python scrape_partselect.py recon
```

The scraper saves checkpoints every 25 parts and supports resume — if interrupted, re-running the same command picks up where it left off.

**Environment:** Requires `FIRECRAWL_API_KEY` in `.env` file (loaded via python-dotenv).

---

## Credit Accounting

| Action | Credits Used |
|---|---|
| Recon (before this session) | 38 |
| Site exploration (3 map calls) | 3 |
| Product scraping (101 pages) | 101 |
| Repair guide scraping (20 pages) | 20 |
| Retry blocked repairs (10 pages) | 10 |
| Overhead / misc | ~4 |
| **Total used** | **~176** |
| **Remaining** | **324** |

---

## Known Limitations

1. **30-model cap per part** — PartSelect loads models via AJAX pagination. Firecrawl only captures the initial page render (~30 models). A direct scraper making AJAX calls could get all models.

2. **10/20 repair guides blocked** — Some PartSelect URLs consistently return "Page Not Found" through Firecrawl. The blocked pages may work from a different IP or with Firecrawl's premium anti-bot bypass.

3. **Brand skew** — The priority sort selected many Admiral/Estate/Caloric parts (which had symptoms + difficulty + video). Future scrapes should use brand diversity weighting to get more Whirlpool, GE, Samsung, LG parts.

4. **No `recommended_parts` in repair guides** — Repair pages link to part *categories* (e.g., "Refrigerator Valves") not individual PS numbers. To connect causes to specific parts, we'll need to match cause part names against our parts database at query time.

5. **Stale baseline data** — The 4,069 non-enhanced parts have prices and stock status from ~1 year ago. These are fine for search/discovery but shouldn't be shown as current pricing.

# PartSelect Chat Agent — Backend Architecture

## Context

We're building the FastAPI backend for a PartSelect.com AI chat agent (InstaLILY case study). The backend orchestrates a Gemini 2.5 Flash agent that uses tool-calling to answer questions about refrigerator and dishwasher parts. We have 4,170 parts (2,442 enhanced with full data, 1,728 baseline), 149 repair guides (22 generic + 91 brand-specific + 36 how-to), 51 blog articles (86K words), 162,976 model mappings, and 49 symptom mappings ready to go.

---

## 1. Agent Loop: Custom While-Loop (No Framework)

A simple `while True` loop — LLM decides which tool to call, we execute it, feed the result back, repeat until the LLM produces a text response.

```python
async def agent_loop(messages, tools):
    while iterations < MAX_ITERATIONS (5):
        response = await gemini.generate(messages, tools)
        if response.has_tool_calls:
            for call in response.tool_calls:
                result = execute_tool(call)
                messages.append(tool_result(call, result))
                yield status_event(f"Running {call.name}...")
        else:
            async for chunk in response.stream:
                yield text_delta(chunk)
            break
```

**Why not LangChain/LlamaIndex?** Our use case is 5 tools + 1 LLM — not complex enough to justify the abstraction tax. A custom loop is ~50 lines, fully debuggable, and signals stronger engineering to evaluators. Framework internals are hard to explain in the 1-hour Q&A.

**Why not a state machine?** The LLM is better at routing than hand-coded heuristics. A state machine breaks on multi-intent queries ("is PS11752778 compatible with my model and how do I install it?") while the agent loop handles them naturally by chaining tool calls.

---

## 2. The Five Tools

### Reasoning Parameter (all tools)

Every tool includes a **`reasoning: str`** required parameter. The LLM must explain:
- Why it chose this tool over the others
- Why it's passing these specific inputs

This parameter is **not used by tool logic** — it's for chain-of-thought (improves tool selection accuracy) and logging/debugging. The Gemini function declaration describes it as: `"Your reasoning for calling this tool with these parameters. Explain why this tool is the right choice and how you determined the input values."`

### `search_parts(reasoning, query, appliance_type?, max_results?)`
- **Regex first**: detect PS numbers (`PS\d+`) or model numbers → direct JSON lookup
- **Semantic search**: embed query → ChromaDB `parts` collection with `appliance_type` metadata filter
- **Knowledge augmentation**: also query `knowledge` collection for relevant blog/guide content when the query is symptom-like or mentions error codes/brands. Return knowledge snippets alongside parts.
- **3-tier fallback**: scoped (fridge/dishwasher) → all products → not found with suggestions
- **Mixed queries** ("Whirlpool ice maker"): run both keyword + vector, merge with reciprocal rank fusion
- Returns: list of parts (ps_number, name, brand, price, rating, image_url) + knowledge_snippets[] + tier + scope_note

### `check_compatibility(reasoning, part_number, model_number)`
- Normalize inputs → look up part in `parts_by_ps.json` → check `compatible_models` list
- Also reverse-check `models_index.json`
- Return `confidence: "verified"` when found, `"not_in_data"` when not (never say "incompatible" — we have 162,976 models but coverage varies per part, avg 429 models/part)
- When not in data: honest caveat + link to PartSelect.com for the full compatibility list
- Returns: compatible (bool/null), part info, confidence, message, source_url

### `get_installation_guide(reasoning, part_number?, symptom?, appliance_type?)`
- Part-based: look up difficulty, time, video from `parts_by_ps.json`
- Symptom-based: look up repair guide from all 149 guides for step-by-step instructions
- Matches against `symptom`, `title`, and `action` fields (brand-specific/how-to guides)
- Cross-reference: match part names against repair guide causes for richer results
- Returns: difficulty, time, video_url, steps[], tips, related_guide

### `diagnose_symptom(reasoning, symptom, appliance_type, model_number?)`
- Fuzzy-match symptom against 49 keys in `symptoms_index.json`
- Look up structured causes from all 149 repair guides (generic, brand-specific, how-to)
- Matches against `symptom`, `title`, and `action` fields — brand-specific guides use `title` since their `symptom` field may contain the brand name
- **Also search `knowledge` collection** for relevant blog content (error codes, brand-specific troubleshooting). This is critical for queries like "Bosch E22 error" or "Samsung ice maker not working" that the repair guides don't cover.
- Includes `source_url` in cause results for linking to full repair pages
- Link cause names to actual purchasable parts via name matching against parts DB
- If model_number provided, filter parts to compatible ones
- Returns: matched symptom, causes with recommended parts + source_url, knowledge_snippets[], follow_up_questions

### `get_product_details(reasoning, part_number)`
- Direct lookup in `parts_by_ps.json`
- Returns full product object + `data_tier` ("enhanced" vs "baseline") so LLM can caveat stale data
- Returns: all fields needed for frontend product card

---

## 3. Embedding & Search Strategy

### Three data sources to embed:

**Source 1: Parts (4,170)** — Entity-centric constructed documents (NOT raw_markdown)
For each part, build a search-optimized text document from structured fields:
```
Refrigerator Door Shelf Bin by Whirlpool. PS11752778 / WPW10321304.
$36.18, 4.9 stars (351 reviews). In stock.
This refrigerator door bin is a genuine OEM replacement...
Fixes symptoms: Door won't close, Ice or frost buildup, Leaking.
```
- **2,442 enhanced**: full doc with description, symptoms, all metadata
- **1,728 baseline**: shorter doc from name + brand + symptoms (if available) + price
- **Why not raw_markdown?** Navigation noise, image URLs, diagram references dilute embedding quality. Entity-centric docs are ~300-500 tokens — no chunking needed. One part = one vector.

**Source 2: Repair Guides (149 total)** — Split by cause
- 22 generic + 91 brand-specific (10 "Page Not Found" filtered out) + 36 how-to guides
- Each guide → 1 overview doc + 1 doc per structured cause (with description + steps)
- ~689 vectors total (overviews + per-cause chunks)
- For how-to guides: uses `title` and `action` fields in overview (no `symptom` field)
- Metadata: `appliance_type`, `symptom`, `cause_name`, `guide_type` (generic/brand_specific/howto), `chunk_type=repair_guide`

**Source 3: Blog Articles (51)** — Split by H2 section
- These are the highest-value RAG addition: 86K words covering error codes, brand-specific how-tos, maintenance, and deep troubleshooting
- **Chunking**: split each blog by H2 headings. Each chunk = one self-contained topic/fix (~200-800 words)
- Estimated ~150-200 chunks from 51 articles
- Metadata: `appliance_type`, `content_type` (error_code/how_to/troubleshooting/etc.), `brands_mentioned[]`, `chunk_type=blog`
- **Critical for**: "Bosch E22 error", "how to reset Whirlpool dishwasher", "Samsung ice maker not working" — queries our parts/repair data can't answer

### Embedding model: Gemini Embedding (gemini-embedding-001)

- Stable GA model with `task_type` parameter (RETRIEVAL_QUERY vs RETRIEVAL_DOCUMENT) = free accuracy boost
- 768 dimensions (Matryoshka truncation)
- Gemma 2 requires self-hosting on a GPU (Railway doesn't have GPUs) — not worth deployment complexity
- If we add image upload later, Gemini Embedding handles it with zero migration

### ChromaDB setup:
- **Two collections**: `parts` (4,170 vectors) and `knowledge` (~937 vectors from guides + blogs)
- Separate collections because search behavior differs: part search returns purchasable items, knowledge search returns informational content. The agent may query both or just one depending on the query type.
- 768 dimensions (Gemini Embedding with Matryoshka truncation)
- Parts metadata: `ps_number`, `appliance_type`, `brand`, `data_tier`, `has_description`
- Knowledge metadata: `source_type` (repair_guide/blog), `appliance_type`, `content_type`, `guide_type`, `brands_mentioned`, `symptom`
- Total: ~5,107 vectors

### Keyword fallback:
- Simple in-memory inverted index of part name words → PS numbers
- Catches cases where semantic search misses exact terms

---

## 4. Guardrails: Rule-Based Classifier (No Extra LLM Call)

A keyword/regex classifier runs BEFORE the LLM — zero latency, zero cost:
- **ON_TOPIC**: appliance keywords detected (fridge, dishwasher, etc.) or part number patterns → normal agent flow
- **GREETING**: hi/hello/thanks → pass to LLM, system prompt handles it
- **OTHER_APPLIANCE**: washer/dryer/range keywords → agent flow but search starts at tier-2
- **OFF_TOPIC**: no appliance signals → canned redirect, skip LLM entirely

System prompt is the primary guardrail. Each tool function also validates inputs (e.g., `diagnose_symptom` rejects `appliance_type="washer"` with a helpful message).

---

## 5. System Prompt: Few-Shot Tool Examples

The system prompt includes 3-4 worked examples showing correct tool selection with reasoning. These dramatically improve tool-calling accuracy.

```
## Example Interactions

### Example 1: Part number lookup
User: "Find part PS11752778"
→ Call search_parts(
    reasoning="The user provided a specific PS number. I should use search_parts with the exact
    part number rather than diagnose_symptom or check_compatibility, since they want to find/view
    a part, not check compatibility or diagnose an issue.",
    query="PS11752778"
  )
→ Then call get_product_details(
    reasoning="search_parts returned PS11752778. The user wants to see this part, so I should
    fetch full details to display a product card with price, rating, and image.",
    part_number="PS11752778"
  )

### Example 2: Compatibility check
User: "Is this part compatible with my WDT780SAEM1?"
(conversation context: previously discussed PS10065979)
→ Call check_compatibility(
    reasoning="The user is asking about compatibility between a previously discussed part
    (PS10065979) and their model WDT780SAEM1. This is a direct compatibility question,
    not a search or diagnosis.",
    part_number="PS10065979",
    model_number="WDT780SAEM1"
  )

### Example 3: Symptom diagnosis
User: "The ice maker on my Whirlpool fridge is not working"
→ Call diagnose_symptom(
    reasoning="The user describes a symptom (ice maker not working) on a specific appliance
    (refrigerator). This is a troubleshooting request, not a part search. I should diagnose
    first to identify causes before recommending specific parts.",
    symptom="ice maker not working",
    appliance_type="refrigerator"
  )

### Example 4: Multi-step (diagnosis + compatibility)
User: "My dishwasher won't drain. I have model WDT780SAEM1."
→ First call diagnose_symptom(reasoning="...", symptom="won't drain", appliance_type="dishwasher")
→ Read causes and recommended parts
→ Then call check_compatibility(reasoning="...", part_number="PS11753379", model_number="WDT780SAEM1")
→ Synthesize: diagnosis + compatible parts for their specific model
```

---

## 6. Streaming: SSE (not WebSockets)

**Why SSE over WebSockets?**
- **Vercel doesn't support WebSockets** on free/pro tier — this alone is decisive
- SSE works through CDN/proxies (Vercel edge, Cloudflare) natively
- Built-in auto-reconnect via EventSource API
- Our flow is unidirectional (user POSTs, server streams back) — WS bidirectionality is unused overhead
- Simpler: no connection management, heartbeats, or upgrade handshakes

```
POST /api/chat { messages, session_id }
→ text/event-stream

Event types:
  status              → "Searching for parts..." (while tool runs)
  product_card        → full part data for rich card rendering
  compatibility_result → yes/no badge
  diagnosis           → causes + recommended parts
  text_delta          → streamed LLM text tokens
  suggestions         → quick-reply options after answer
  error               → recoverable error message
  done                → stream complete
```

Product cards and structured results sent BEFORE the text explanation — user sees results immediately while LLM generates narrative.

---

## 7. Frontend ↔ Backend Connection (Vercel + Railway)

```
Vercel (Next.js)                    Railway (FastAPI)
  Browser → /api/chat  ──proxy──→  POST /api/chat (SSE)
            (Next.js API route)     (FastAPI endpoint)
```

**Next.js API route as proxy** (not direct CORS):
- Frontend calls `/api/chat` on its own Vercel domain
- A Next.js API route forwards the request to the Railway backend URL and pipes the SSE stream back
- Backend URL stays hidden (no CORS exposure), clean same-origin setup
- Can add auth/rate-limiting at the proxy layer later
- The proxy is ~15 lines of code

This means the FastAPI backend only needs to handle requests from the Next.js proxy, not from browsers directly. CORS is still configured as a safety net but the proxy handles the primary flow.

---

## 8. Session Management

- Server-side in-memory dict: `session_id → list[Message]`
- Frontend sends `session_id` (UUID) + latest user message per request
- Backend manages full conversation history including tool calls/results
- Store compact tool results in history (not full raw data)
- No summarization needed — Gemini 2.5 Flash has 1M token context window

---

## 9. Project Structure

```
backend/
  app/
    __init__.py
    main.py                    # FastAPI app, CORS, lifespan startup/shutdown
    config.py                  # Settings (API keys, model names, paths)

    agent/
      __init__.py
      loop.py                  # The while-loop agent orchestrator
      system_prompt.py         # System prompt text + few-shot examples
      classifier.py            # Rule-based intent classifier

    tools/
      __init__.py
      registry.py              # Tool name → function mapping + Gemini function declarations
      search_parts.py
      check_compatibility.py
      installation_guide.py
      diagnose_symptom.py
      product_details.py

    data/
      __init__.py
      loader.py                # Load all JSON into memory at startup
      chroma_store.py          # ChromaDB client, two collections, query interface
      embeddings.py            # Gemini Embedding 2 wrapper
      search.py                # Vector + keyword + RRF hybrid search

    api/
      __init__.py
      chat.py                  # POST /api/chat SSE endpoint
      models.py                # Pydantic request/response schemas

    session/
      __init__.py
      memory.py                # In-memory session store

  scripts/
    embed_parts.py             # One-time: embed all 4,170 parts into ChromaDB `parts` collection
    embed_knowledge.py         # One-time: embed 149 repair guides + 51 blogs into ChromaDB `knowledge` collection
    test_backend.py            # Smoke tests: data loading, tool correctness, app imports (15 tests)

  pyproject.toml
  .env
```

---

## 10. Dependencies

```
fastapi
uvicorn[standard]
sse-starlette
google-genai                   # New unified Gemini SDK — chat + function calling + streaming + embeddings
chromadb
pydantic
python-dotenv                  # already have
```

Using `google-genai` (not the older `google-generativeai`). Single package for all Gemini interactions.

---

## 11. Implementation Order (Embeddings First)

Build the data foundation first so tools are built directly against ChromaDB from the start.

### Phase 1: Data Layer + Embeddings
1. `config.py` — API keys, paths, model names
2. `data/loader.py` — Load all JSONs into memory at startup (parts.json, parts_by_ps.json, repairs.json, blogs.json, models_index.json, symptoms_index.json)
3. `data/embeddings.py` — Gemini Embedding 2 wrapper (task_type support, 768 dims)
4. `data/chroma_store.py` — ChromaDB client, two collections (`parts` + `knowledge`), query interface
5. `scripts/embed_parts.py` — Embed all 4,170 parts (entity-centric docs) into `parts` collection
6. `scripts/embed_knowledge.py` — Embed 149 repair guides (split by cause, 3 guide types) + 51 blogs (split by H2) into `knowledge` collection
7. `data/search.py` — Hybrid search: regex detection → JSON lookup / ChromaDB vector / keyword fallback + RRF merge. Queries can target `parts`, `knowledge`, or both.
8. **Verify**: run test queries against both collections — part searches, error code queries, symptom queries

### Phase 2: Tools
9. `tools/registry.py` — Tool name → function mapping + Gemini function declarations
10. `tools/product_details.py` — simplest tool, pure JSON lookup
11. `tools/check_compatibility.py` — JSON lookup + honest "not in data" caveat
12. `tools/search_parts.py` — hybrid search (built on top of ChromaDB from phase 1)
13. `tools/installation_guide.py` — part lookup + repair guide cross-reference
14. `tools/diagnose_symptom.py` — symptom matching + cause-to-part linking + knowledge search
15. **Verify**: call each tool directly with benchmark inputs

### Phase 3: Agent + API
16. `agent/system_prompt.py` — system prompt text + few-shot examples
17. `agent/classifier.py` — rule-based intent classifier
18. `agent/loop.py` — the while-loop agent with Gemini function calling
19. `api/models.py` — Pydantic request/response schemas
20. `api/chat.py` — POST /api/chat SSE endpoint
21. `session/memory.py` — in-memory session store
22. `main.py` — FastAPI app, CORS, lifespan
23. **Verify**: end-to-end with all benchmark queries

---

## 12. Verification

Test against these benchmark queries:

**Core tool tests:**
1. `"Find part PS11752778"` → search_parts exact lookup → product card
2. `"Is PS11752778 compatible with WRS321SDHZ08?"` → check_compatibility → verified yes
3. `"The ice maker on my Whirlpool fridge is not working"` → diagnose_symptom → 4 causes from repair guide
4. `"How do I install PS10065979?"` → get_installation_guide → difficulty + video
5. `"I need a door gasket for my dishwasher"` → search_parts semantic → 2-3 gaskets

**Blog/knowledge tests:**
6. `"Bosch dishwasher E22 error"` → search knowledge collection → blog content with filter/drain fixes
7. `"How to reset my Whirlpool dishwasher"` → search knowledge → blog with reset instructions
8. `"Samsung ice maker not working"` → diagnose_symptom + knowledge search → blog + repair guide

**Guardrail tests:**
9. `"Can you help me fix my washing machine?"` → classifier → redirect (other appliance)
10. `"What's the weather today?"` → classifier → off-topic redirect

**Multi-step test:**
11. `"My dishwasher won't drain, find me a part for model WDT780SAEM1"` → diagnose_symptom → search_parts → check_compatibility chain

Run each query and verify: correct tool called, correct data returned, reasoning parameter logged, streamed response includes product cards, text is accurate.

### Automated Smoke Tests

```bash
uv run python -m scripts.test_backend
```

Runs 15 tests covering: data loader counts, guide type filtering, "Page Not Found" exclusion, symptom diagnosis (generic + brand-specific), how-to guide matching, part search, compatibility checks, product details, and app imports.

---

## Key Data Files

| File | Description |
|---|---|
| `data/parts_by_ps.json` | 4,170 parts keyed by PS number (primary lookup store, ~68 MB) |
| `data/models_index.json` | 162,976 model → parts mappings (~25 MB) |
| `data/symptoms_index.json` | 49 symptom → parts mappings |
| `data/repairs.json` | 22 generic symptom repair guides (backward compatible) |
| `data/repairs_all.json` | All 159 repair guides: 22 generic + 101 brand-specific + 36 how-to (~1.1 MB) |
| `data/blogs.json` | 51 blog articles (86K words: error codes, how-tos, troubleshooting, maintenance) |

**Note:** `parts.json` (array format, ~68 MB) is NOT loaded at runtime to save memory. The loader uses only `parts_by_ps.json` for O(1) lookups. The `embed_parts.py` script reads `parts_by_ps.json` directly.

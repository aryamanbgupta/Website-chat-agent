# Top 6 Improvements

## 1. No True Token-by-Token Streaming

**File:** `backend/app/agent/loop.py:69-100`

The backend calls `generate_content()` (synchronous, blocking) and sends the entire text response as a single `text_delta` event. The frontend has full streaming infrastructure (`APPEND_TEXT_DELTA` reducer, `StreamingIndicator`), but it's never actually used — the user sees nothing, then the full response appears at once.

**Fix:** Replace `generate_content()` with `generate_content_stream()` and yield `text_delta` events per-chunk inside the agent loop. This is the single highest-impact UX improvement.

---

## 2. Synchronous Tool Execution Blocks the Event Loop

**File:** `backend/app/tools/registry.py:167-175`, `backend/app/data/search.py:123-124`

`execute_tool()` is a synchronous call inside an `async` generator. The `embed_query()` call inside `search_parts_hybrid` makes a blocking network request to Gemini's embedding API, stalling the entire event loop for all concurrent users.

**Fix:** Wrap tool execution in `asyncio.to_thread()` or make the embedding client calls natively async. This is critical for any multi-user deployment.

---

## 3. In-Memory Session Store with No Eviction

**File:** `backend/app/session/memory.py`

`SessionStore` is a plain `dict` with no TTL, max-size cap, or eviction policy. Every session's full conversation history lives in memory forever until the process restarts. Under sustained traffic this is a memory leak.

**Fix:** Add a TTL (e.g., 30 min inactivity) with a max session count. Even a simple `OrderedDict` with LRU eviction would suffice. For production, move to Redis.

---

## 4. Fragile Fuzzy Symptom Matching

**Files:** `backend/app/tools/diagnose_symptom.py:118-161`, `backend/app/tools/installation_guide.py:77-128`

Symptom matching uses simple word-overlap scoring, which fails for synonyms ("leaking" vs "dripping"), paraphrases, and typos. The same fuzzy-matching logic is also duplicated across both files (DRY violation).

**Fix:** Use embedding-based similarity (the infrastructure already exists via `embed_query`) for symptom matching. Extract the shared matching logic into a single utility in `app/data/search.py`.

---

## 5. No Test Suite

There is no pytest suite, no frontend tests, and no CI. The classifier, tools, and search functions are all highly testable with deterministic inputs/outputs. The absence of tests undermines the "extensibility" claim — how does a new contributor know they haven't broken compatibility checking?

**Fix:** Add at minimum: unit tests for `classify()` (edge cases like "fix my washing machine" vs "fix my dishwasher"), tool-level tests with fixture data, and a search accuracy test against known PS numbers.

---

## 6. Wide-Open CORS and No Rate Limiting

**Files:** `backend/app/main.py:32-37`, `backend/app/api/chat.py`

CORS is `allow_origins=["*"]` and the `/api/chat` endpoint has zero rate limiting. A single bad actor can drain the Gemini API quota in minutes. Combined with the session store issue (#3), this also enables trivial memory exhaustion.

**Fix:** Restrict CORS origins to the frontend URL (configurable via env var). Add per-session or per-IP rate limiting (e.g., `slowapi` or a simple token bucket middleware).

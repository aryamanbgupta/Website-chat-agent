# PartSelect Chat Agent — Architecture

## High-Level Overview

The system is a **hybrid RAG + tool-calling agent** with three layers:

1. **Next.js Chat Frontend** — Polished UI with streaming responses, product cards, and guided flows
2. **FastAPI Backend** — Orchestrates an LLM agent that decides which tools to call per user query
3. **ChromaDB Vector Store** — Stores embedded product data, repair guides, and compatibility mappings

The LLM doesn't answer questions from memory. Instead, it acts as a **reasoning router**: it reads the user's message, decides which tool(s) to invoke (search parts, check compatibility, diagnose symptom, etc.), calls them, and synthesizes the results into a natural response. This is the function-calling / tool-use pattern.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Next.js Chat Interface                       │  │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────────┐  │  │
│  │  │ Message  │ │ Product  │ │  Quick    │ │  Starter   │  │  │
│  │  │ Bubbles  │ │ Cards    │ │  Replies  │ │  Prompts   │  │  │
│  │  └─────────┘ └──────────┘ └───────────┘ └────────────┘  │  │
│  └──────────────────────┬────────────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────────────┘
                          │ SSE Stream (Server-Sent Events)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Agent Loop                              │  │
│  │                                                           │  │
│  │  User Message → LLM (Gemini 2.5 Flash)                   │  │
│  │       │                                                   │  │
│  │       ├── decides: call tool(s)?                          │  │
│  │       │     YES → execute tool → feed result back to LLM  │  │
│  │       │     NO  → stream final response                   │  │
│  │       │                                                   │  │
│  │       └── repeat until LLM produces final answer          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │  Guardrail  │ │  Session     │ │  Streaming Response     │  │
│  │  Classifier │ │  Memory      │ │  (SSE)                  │  │
│  └─────────────┘ └──────────────┘ └─────────────────────────┘  │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Tool Layer                               │
│                                                                 │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────────────┐ │
│  │ search_parts │ │ check_compat  │ │ get_install_guide      │ │
│  │              │ │               │ │                        │ │
│  │ Semantic +   │ │ Exact model → │ │ Installation steps,    │ │
│  │ keyword      │ │ part lookup   │ │ video links, difficulty│ │
│  │ hybrid search│ │ in metadata   │ │ rating                 │ │
│  └──────┬───────┘ └───────┬───────┘ └────────────┬───────────┘ │
│         │                 │                      │             │
│  ┌──────────────────┐  ┌─────────────────────────────────────┐ │
│  │ diagnose_symptom │  │ get_product_details                 │ │
│  │                  │  │                                     │ │
│  │ Symptom → causes │  │ Full product page data for a        │ │
│  │ → recommended    │  │ specific part number                │ │
│  │ parts            │  │                                     │ │
│  └────────┬─────────┘  └──────────────────┬──────────────────┘ │
└───────────┼────────────────────────────────┼────────────────────┘
            │                                │
            ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                    │
│                                                                 │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│  │      ChromaDB           │  │   Structured JSON Store      │ │
│  │                         │  │                              │ │
│  │  Embedded chunks:       │  │  parts.json                  │ │
│  │  - product overviews    │  │  - part_number → full data   │ │
│  │  - installation guides  │  │  - model compatibility map   │ │
│  │  - troubleshooting tips │  │  - symptom → parts map       │ │
│  │  - repair articles      │  │                              │ │
│  │                         │  │  (Fast exact lookups)        │ │
│  │  Metadata filters:      │  │                              │ │
│  │  - appliance_type       │  │                              │ │
│  │  - brand                │  │                              │ │
│  │  - chunk_type           │  │                              │ │
│  │  - part_number          │  │                              │ │
│  └─────────────────────────┘  └──────────────────────────────┘ │
│                                                                 │
│  Embeddings: Gemini Embedding 2 (gemini-embedding-2-preview)   │
│  3072 dimensions → truncated to 768 via MRL for speed          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why This Architecture

### The Agent Loop Pattern (not a simple RAG chain)

A naive RAG chatbot does: `query → embed → retrieve → stuff into prompt → generate`. This breaks for our use case because:

- A compatibility check needs an **exact lookup**, not semantic search
- A diagnosis flow needs **multi-turn reasoning**, not a single retrieval
- A part search by PS number needs **keyword matching**, not embeddings

The agent loop pattern solves this. The LLM receives the user message plus a list of available tools. It **decides** which tool to call (or whether to respond directly), executes it, reads the result, and either calls another tool or generates the final answer. This is native function-calling — Gemini 2.5 Flash supports it with excellent reliability and the lowest latency of any frontier model.

### Why Gemini 2.5 Flash as the Chat LLM

Speed is the top priority for a chat agent. Based on current benchmarks:

| Model | TTFT (Time to First Token) | Throughput | Function Calling | Cost (input/1M) |
|---|---|---|---|---|
| **Gemini 2.5 Flash** | **~250ms** | **~250 tok/s** | Excellent | **$0.15** |
| Claude Haiku 4.5 | ~600ms | ~79 tok/s | Good | $0.80 |
| GPT-4.1 Mini | ~800ms | ~62 tok/s | Excellent | $0.40 |
| GPT-4o | ~500ms | ~90 tok/s | Excellent | $2.50 |
| Claude Sonnet 4.6 | ~1.5s | ~77 tok/s | Excellent | $3.00 |

Gemini 2.5 Flash gives us the fastest TTFT, highest throughput, strong function-calling, and the lowest cost. For a customer support chatbot where perceived speed matters enormously, this is the right choice. The quality is more than sufficient for routing queries to tools and synthesizing retrieved data.

**Fallback strategy**: If Gemini has an outage, fall back to GPT-4.1 Mini. Both support the same OpenAI-compatible function-calling format.

### Why Gemini Embedding 2 for Embeddings

`gemini-embedding-2-preview` was released March 10, 2026 and is Google's first **natively multimodal** embedding model. It maps text, images, video, audio, and PDFs into a single unified vector space.

**Why this matters for PartSelect:**

1. **Product images + text in one embedding** — We can embed a part's image alongside its description as a single vector. When a user describes what they see ("the rubber gasket on the bottom of the door"), the search finds visually AND semantically similar parts.

2. **Future-proof for image upload** — If we add "photograph your broken part" later, user-uploaded images land in the same embedding space as our product data. No separate model pipeline needed.

3. **Top MTEB scores** — Gemini Embedding 2 holds the top position on the Massive Text Embedding Benchmark for retrieval accuracy.

4. **Task-type optimization** — The API accepts a `task_type` parameter (`RETRIEVAL_QUERY` vs `RETRIEVAL_DOCUMENT`) that optimizes the vector for asymmetric search. This is a free accuracy boost.

5. **Matryoshka dimensions** — Supports 3072, 1536, or 768 dimensions with minimal quality loss. We use **768** for speed + storage efficiency during the demo, with the option to scale up.

```python
# Embedding a product with image + text (multimodal)
result = client.models.embed_content(
    model="gemini-embedding-2-preview",
    contents=[
        types.Content(parts=[
            types.Part(text="WPW10321304 - Refrigerator Water Inlet Valve"),
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ])
    ],
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768,
    ),
)

# Embedding a user query
query_result = client.models.embed_content(
    model="gemini-embedding-2-preview",
    contents=["my fridge water dispenser stopped working"],
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768,
    ),
)
```

**Cost**: $0.20 per million text tokens. Image/audio follows standard Gemini media token rates. For our 500-part demo dataset, total embedding cost is < $1.

---

## The Five Tools

Each tool is a Python function the LLM can invoke. They're registered with the Gemini API as function declarations.

### 1. `search_parts`

**Purpose**: Find parts by natural language description or partial part number.

**How it works — three-tier search with graceful broadening:**

```
Tier 1: Search within scope (refrigerator + dishwasher only)
  │
  ├── Part number detected (regex: PS\d+ or mfg format)?
  │     → Exact JSON lookup, filtered to fridge/dishwasher
  │
  └── Natural language?
        → Embed query → ChromaDB search with
          metadata filter: appliance_type IN ["refrigerator", "dishwasher"]
  │
  ├── Results found? → Return them ✅
  │
  ▼ No results
Tier 2: Search ALL products (full catalog, no appliance filter)
  │
  ├── Same search logic but without the appliance_type filter
  │   This catches cases where the user asks about a part that
  │   happens to be cross-listed or miscategorized
  │
  ├── Results found? → Return them with a note:
  │   "This part is for a [washer/range/etc]. I specialize in
  │    refrigerator and dishwasher parts, but here's what I found."
  │
  ▼ No results
Tier 3: Not found
  │
  └── Return a helpful "not found" with suggestions:
      "I couldn't find that part. You can try:
       • Searching on PartSelect.com directly
       • Double-checking the part/model number
       • Describing the symptom instead"
```

This means we **scrape and embed the full PartSelect catalog** (all appliance types), not just fridge/dishwasher. The scope filtering happens at query time via metadata, not at data ingestion. This is better for extensibility too — adding a new appliance type means changing one filter value, not re-scraping.

**Returns**: `{ results: [...], tier: 1|2|3, scope_note: string|null }`

### 2. `check_compatibility`

**Purpose**: Check if a specific part fits a specific model number.

**How it works**:
1. Look up the part in the structured JSON store by part number
2. Check if the user's model number appears in the `compatible_models` list
3. Return a clear yes/no with the full model name if found

**Returns**: `{ compatible: bool, part_name, model_name, message }`

### 3. `get_installation_guide`

**Purpose**: Return installation instructions for a specific part.

**How it works**:
1. Look up the part by number in the JSON store
2. Return the installation steps, difficulty rating, estimated time, and YouTube video link
3. If no specific guide exists, search ChromaDB for the closest repair article

**Returns**: `{ steps: string[], difficulty: 1-5, time_estimate, video_url, tools_needed }`

### 4. `diagnose_symptom`

**Purpose**: Given an appliance type and symptom, suggest likely causes and parts.

**How it works**:
1. Match the symptom to pre-built troubleshooting trees (scraped from PartSelect's Repair Help)
2. If no exact match, do a semantic search in ChromaDB filtered to `chunk_type=troubleshooting`
3. Return ranked list of possible causes, each linked to a recommended replacement part

**Returns**: `{ causes: [{ cause, likelihood, part_number, part_name, price }], follow_up_questions: string[] }`

### 5. `get_product_details`

**Purpose**: Get full details for a specific part number (used after search or diagnosis to show a rich product card).

**How it works**:
1. Direct lookup in the JSON store by part number
2. Return complete product data including all fields needed for a product card

**Returns**: Full product object with all fields (price, rating, reviews, compatibility count, image, etc.)

---

## Data Pipeline

### Scraping Strategy

PartSelect is server-rendered HTML — no JavaScript rendering needed. `BeautifulSoup + requests` is sufficient.

We scrape **all appliance types**, not just fridge/dishwasher. Scope filtering happens at query time via metadata — this enables the tiered search (scoped → all → not found) and makes future appliance additions trivial.

```
Step 1: Scrape ALL category index pages (fridge + dishwasher FIRST)
        Priority 1: /Refrigerator-Parts.htm → part categories
                     /Dishwasher-Parts.htm   → part categories
        Priority 2: /Washer-Parts.htm, /Dryer-Parts.htm,
                     /Range-Parts.htm, /Microwave-Parts.htm, etc.

Step 2: Scrape top parts per category
        /PS{number}-{slug}.htm → full product page
        Extract: name, PS#, mfg#, price, stock, rating, reviews,
                 compatible models, installation, description, image URL
        Tag each with appliance_type from its source category

Step 3: Scrape repair/troubleshooting guides (fridge + dishwasher only)
        /Repair/Refrigerator/{Symptom}/ → symptom articles
        /Repair/Dishwasher/{Symptom}/   → symptom articles
        Extract: symptom, causes, recommended parts, steps

Step 4: Build structured data files
        → parts.json (keyed by part_number, includes appliance_type)
        → models.json (model_number → compatible parts)
        → symptoms.json (appliance + symptom → causes + parts)
```

**Target counts**: ~300–500 products for fridge/dishwasher (deep coverage), ~50–100 per other appliance type (enough for tier-2 fallback). Total ~1,000–1,500 products.

Rate limit: 1 request/second, respect robots.txt.

### Chunking & Embedding Strategy

Each product generates **multiple chunks** in ChromaDB, each with rich metadata:

| Chunk Type | Content | Metadata |
|---|---|---|
| `overview` | Part name, description, price, specs | `part_number, appliance_type, brand, chunk_type` |
| `compatibility` | "Compatible with [model list]" | `part_number, appliance_type, compatible_models` |
| `installation` | Installation steps + tips | `part_number, appliance_type, difficulty` |
| `troubleshooting` | "Fixes symptoms: [symptom list]" | `part_number, appliance_type, symptoms` |

Repair guide articles get their own chunks tagged with `chunk_type=repair_guide`.

**Why entity-centric chunking?** A single vector search can combine semantic similarity ("my fridge is leaking") with metadata filtering (`appliance_type="refrigerator"`, `chunk_type="troubleshooting"`) for precise results. This is dramatically better than naive fixed-size text chunking.

---

## Hybrid Search: Why Both Keyword and Semantic

Users search in two fundamentally different ways:

| Search Type | Example | Best Method |
|---|---|---|
| Exact part number | "PS11752778" | Keyword / JSON lookup |
| Manufacturer number | "WPW10321304" | Keyword / JSON lookup |
| Model number | "WDT780SAEM1" | Keyword / JSON lookup |
| Natural language | "rubber gasket for dishwasher door" | Semantic (vector) search |
| Symptom description | "fridge making buzzing noise" | Semantic (vector) search |
| Mixed | "Whirlpool ice maker part" | Both, merged + reranked |

The `search_parts` tool handles this by first checking for part/model number patterns via regex, then falling back to semantic search. For mixed queries, we run both and merge results with reciprocal rank fusion.

---

## Guardrail Architecture

Three-layer approach to keep the agent scoped to refrigerator and dishwasher parts:

### Layer 1: System Prompt (Primary Defense)

```
You are a helpful assistant for PartSelect.com, specializing exclusively
in Refrigerator and Dishwasher replacement parts. You help customers:
- Find the right replacement part
- Check part-model compatibility  
- Diagnose appliance problems
- Get installation guidance

If asked about anything outside refrigerator and dishwasher parts
(other appliances, general knowledge, unrelated topics), politely redirect:
"I specialize in refrigerator and dishwasher parts. I can help you find
replacement parts, check compatibility, or troubleshoot issues with
these appliances. How can I help?"

Never provide medical, legal, or financial advice. Never discuss competitors.
```

### Layer 2: Parallel Input Classifier (Zero Latency)

A lightweight classification call runs **in parallel** with the main LLM call. Uses Gemini 2.5 Flash with a minimal prompt:

```
Classify this user message as one of:
- REFRIGERATOR_PARTS (about refrigerator parts, repair, or troubleshooting)
- DISHWASHER_PARTS (about dishwasher parts, repair, or troubleshooting)
- OTHER_APPLIANCE (about other appliance parts — washer, dryer, range, etc.)
- OFF_TOPIC (not about appliance parts at all)
Respond with only the label.
```

Routing logic:
- `REFRIGERATOR_PARTS` / `DISHWASHER_PARTS` → normal agent flow (tier-1 search)
- `OTHER_APPLIANCE` → agent flow but search starts at tier-2 (all products, no scope filter). Agent prefixes response with: "I specialize in refrigerators and dishwashers, but I found this for you..."
- `OFF_TOPIC` → polite redirect, no search

Since it runs in parallel, it adds **zero latency** to on-topic queries.

### Layer 3: Metadata Filtering (Data-Level)

The tiered search in `search_parts` is itself a guardrail: tier-1 restricts to `appliance_type IN ["refrigerator", "dishwasher"]`, tier-2 opens to all products, and tier-3 returns a helpful not-found. The data layer enforces scope even if the LLM ignores the system prompt.

---

## Frontend Architecture

### Chat UI Components

Built with Next.js + shadcn/ui + Tailwind CSS, styled to match PartSelect's brand (blues, clean/trustworthy aesthetic).

**Core Components:**

1. **ChatContainer** — Manages message list, auto-scroll, streaming state
2. **MessageBubble** — User and assistant messages with markdown rendering
3. **ProductCard** — Rich card with image, name, PS#, price, rating, stock badge, compatibility badge, "View Details" / "Add to Cart" buttons
4. **QuickReplyButtons** — Contextual suggested actions after each response ("Order this part", "See installation video", "Check other causes")
5. **StarterPrompts** — Welcome screen buttons: "🔧 Diagnose a problem", "🔍 Find a part by number", "📋 Check compatibility"
6. **CompatibilityBadge** — Green ✓ or red ✗ inline badge showing part-model compatibility
7. **DiagnosisProgress** — Numbered step indicator showing diagnostic flow progress
8. **StreamingIndicator** — Typing dots + "Searching parts..." status messages
9. **VoiceInputButton** — 🎤 mic button for speech-to-text input via Web Speech API

### Streaming Protocol

The frontend uses **Server-Sent Events (SSE)** to stream responses from FastAPI. SSE is simpler than WebSockets, unidirectional (server → client), and works through proxies and CDNs.

```
Frontend (Next.js)                    Backend (FastAPI)
      │                                      │
      │── POST /api/chat ──────────────────►│
      │   { messages, session_id }           │
      │                                      │── LLM decides tool call
      │◄── SSE: {"type": "status",  ────────│
      │          "text": "Searching..."}     │
      │                                      │── Tool executes
      │◄── SSE: {"type": "product_card", ───│
      │          "data": {...}}              │
      │                                      │── LLM generates text
      │◄── SSE: {"type": "text_delta", ─────│
      │          "text": "Based on..."}      │
      │◄── SSE: {"type": "text_delta", ─────│
      │          "text": " your model..."}   │
      │                                      │
      │◄── SSE: {"type": "suggestions", ────│
      │          "options": [...]}           │
      │◄── SSE: {"type": "done"} ───────────│
      │                                      │
```

The SSE stream carries **typed events** so the frontend knows when to render a product card vs. append text vs. show suggestions. This is what makes the chat feel rich and interactive rather than a plain text stream.

### The Vercel AI SDK Connection

The Next.js frontend uses Vercel AI SDK's patterns for streaming. The backend implements a custom SSE endpoint that the frontend consumes. Vercel has an official `ai-sdk-preview-python-streaming` template for exactly this Next.js ↔ FastAPI pattern.

### Speech-to-Text (Voice Input)

The chat input includes a **🎤 microphone button**. Tapping it starts voice recognition — the user speaks their query and it's transcribed into the text input, then sent as a normal message. Uses the browser's built-in **Web Speech API** (`SpeechRecognition`). This is:

- **Completely free** — no API keys, no server cost, no external dependencies
- **Zero latency** — runs client-side, streams transcription in real-time
- **Works in Chrome + Edge** — covers ~75% of desktop/mobile users (Firefox and Safari have partial support)
- **Perfect for our use case** — user is under the sink with wet hands, speaks "my dishwasher is leaking from the bottom" instead of typing

**Implementation** — a lightweight React hook:

```tsx
// hooks/useSTT.ts
export function useSTT() {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const startListening = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return; // Unsupported browser

    const recognition = new SpeechRecognition();
    recognition.continuous = false;  // Single utterance
    recognition.interimResults = true; // Show partial results as user speaks
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const result = event.results[event.results.length - 1];
      setTranscript(result[0].transcript);
    };

    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
    setListening(false);
  };

  return { startListening, stopListening, listening, transcript };
}
```

**UX flow**: User taps 🎤 → mic icon pulses red → interim transcription appears in the input field as they speak → they stop talking → final transcription fills the input → user reviews and hits send (or it auto-sends after a brief pause). The interim results give immediate feedback so users know it's working.

**Graceful degradation**: If `SpeechRecognition` isn't available (Firefox/Safari), the mic button is hidden. No broken state.

### Roadmap: Text-to-Speech (Read Aloud)

On the roadmap (not MVP): a 🔊 button per assistant message that reads the response aloud using the same Web Speech API's `SpeechSynthesis` interface. Especially useful for step-by-step installation guides — the agent reads one step at a time while the user works hands-free. Both STT and TTS use the same browser API family, so adding TTS later is trivial.

---

## Extensibility Story

This is what evaluators care about: how easy is it to add new capabilities?

### Adding a New Appliance (e.g., Washing Machines)

Since we already scrape and embed ALL appliance types:

1. Add `"washer"` to the tier-1 metadata filter whitelist in `search_parts`
2. Scrape washer-specific repair guides for the symptom database
3. Update the system prompt to include washers
4. **No re-scraping, no re-embedding, no code changes** to the agent loop or frontend

**Time estimate: 1–2 hours**

### Adding a New Tool (e.g., Order Tracking)

1. Define the tool function in Python
2. Register it as a function declaration with the LLM
3. Add a new SSE event type if it needs a custom UI component
4. Build the frontend component

**Time estimate: half a day**

### Swapping the LLM

The agent loop is model-agnostic. Tool definitions use a standard JSON schema format. Switching from Gemini to GPT-4.1 or Claude requires changing one config value and minor SDK adaptation. The tool layer, data layer, and frontend are completely unchanged.

### Scaling to Production

| Current (Demo) | Production Path |
|---|---|
| ChromaDB (local) | Pinecone or Weaviate (managed, 23ms p95) |
| 500 products | Full catalog via PartSelect API or sitemap crawl |
| Single FastAPI instance | Kubernetes + load balancer |
| In-memory sessions | Redis for session state |
| Gemini API direct | Vertex AI (SLAs, quotas, monitoring) |

---

## Execution Plan

### Day 1–2: Data Pipeline
- Build scraper for product pages + repair guides
- Design JSON schema for structured data
- Set up ChromaDB + embedding pipeline with Gemini Embedding 2
- Populate vector store with 200–500 products

### Day 3–4: Backend Agent
- FastAPI project setup with SSE streaming endpoint
- Implement the 5 tool functions
- Build the agent loop with Gemini 2.5 Flash function-calling
- Add guardrail classifier (parallel)
- System prompt tuning

### Day 5: Frontend
- Next.js + shadcn/ui project setup
- Chat interface with streaming consumption
- ProductCard, QuickReplyButtons, StarterPrompts components
- PartSelect brand styling (colors, typography, logo placement)

### Day 6: Integration & Polish
- End-to-end testing with all benchmark queries
- Three pre-built demo scenarios for the Loom video
- Edge case handling (empty results, ambiguous queries, multi-turn)
- Loading states, error handling, responsive design

### Day 7: Deploy & Record
- Deploy frontend to Vercel, backend to Railway
- Architecture diagram for presentation
- Record Loom walkthrough (demo + architecture explanation)
- Prepare slide deck for the 1-hour engineering Q&A

---

## Cost Estimate

| Component | Monthly Cost (Demo Scale) |
|---|---|
| Gemini 2.5 Flash (chat) | ~$5–20 |
| Gemini Embedding 2 (embeddings) | < $1 (one-time for 500 products) |
| ChromaDB | $0 (local) |
| Vercel (frontend) | $0 (free tier) |
| Railway (backend) | $0–5 (free tier) |
| **Total** | **< $25/month** |

At production scale (10K daily conversations): Gemini 2.5 Flash at ~$0.15/1M input tokens keeps costs under $100/month even at high volume.

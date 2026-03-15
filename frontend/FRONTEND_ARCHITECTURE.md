# Frontend Architecture — PartSelect Chat Agent

## Overview

A Next.js 16 chat interface for the PartSelect AI assistant. The frontend consumes the FastAPI backend's SSE streaming protocol and renders rich components (product cards, compatibility badges, diagnosis views) alongside streamed markdown text. Designed to feel like a native extension of PartSelect.com.

**Stack:** Next.js 16 (App Router) · React 19 · Tailwind CSS v4 · TypeScript 5

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SSE transport | `@microsoft/fetch-event-source` | Native `EventSource` is GET-only; our backend expects `POST /api/chat`. This library supports POST with automatic retry and error handling. |
| State management | `useReducer` + React Context | Multiple coordinated state updates arrive per SSE event during streaming. A reducer is deterministic and avoids stale closures that `useState` would create inside streaming callbacks. |
| Message model | Content block array | Assistant messages contain interleaved text + product cards + diagnosis data. An array of typed discriminated unions (`ContentBlock`) preserves ordering naturally and maps cleanly to component rendering. |
| Markdown | `react-markdown` + `remark-gfm` | Industry standard, supports incremental re-rendering during streaming, handles GFM tables/lists from the LLM. |
| API connection | Next.js API route proxy (Edge Runtime) | Backend URL stays server-side. Same-origin requests avoid CORS. Edge Runtime has no response timeout, critical for long-running SSE streams. |
| Session | UUID in `localStorage` | Simple, stateless. Backend manages conversation history server-side keyed by session ID. |
| Styling | Tailwind v4 with CSS `@theme` tokens | PartSelect brand colors defined once in `globals.css`, referenced everywhere via semantic class names (`text-primary-teal`, `bg-cta-yellow`, etc.). |
| Icons | `lucide-react` | Tree-shakeable, consistent style, 1000+ icons, no CSS imports needed. |

---

## Project Structure

```
frontend/
├── next.config.ts                          # Image remote patterns (PartSelect CDN)
├── .env.local                              # BACKEND_API_URL=http://localhost:8000
├── src/
│   ├── app/
│   │   ├── layout.tsx                      # Root layout, Roboto font, metadata
│   │   ├── page.tsx                        # Entry: ChatProvider → ChatContainer
│   │   ├── globals.css                     # Tailwind v4 theme, animations, markdown styles
│   │   └── api/
│   │       ├── chat/route.ts               # POST SSE proxy (Edge Runtime)
│   │       └── health/route.ts             # GET health proxy
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx           # Full-page layout: header + messages + input
│   │   │   ├── MessageList.tsx             # Scrollable message area with auto-scroll
│   │   │   ├── MessageBubble.tsx           # Content block router → text/cards/badges
│   │   │   ├── ChatInput.tsx               # Textarea + send/stop + voice input
│   │   │   ├── StreamingIndicator.tsx      # Bouncing dots + status text
│   │   │   ├── StarterPrompts.tsx          # Welcome screen with 4 prompt buttons
│   │   │   └── QuickReplyButtons.tsx       # Suggested follow-up pill buttons
│   │   ├── cards/
│   │   │   ├── ProductCard.tsx             # Part image, price, rating, stock, difficulty
│   │   │   ├── CompatibilityBadge.tsx      # Green ✓ / amber ⚠ / red ✗ states
│   │   │   └── DiagnosisCard.tsx           # Causes + likelihood + parts + follow-ups
│   │   └── shared/
│   │       ├── StarRating.tsx              # 5-star display (filled/empty)
│   │       ├── StockBadge.tsx              # "In Stock" / "Out of Stock"
│   │       └── VoiceInputButton.tsx        # Mic button, pulse animation
│   ├── hooks/
│   │   ├── useChat.ts                      # Core: reducer + SSE + session composition
│   │   ├── useSSE.ts                       # fetch-event-source wrapper, typed handlers
│   │   ├── useSession.ts                   # localStorage UUID management
│   │   ├── useAutoScroll.ts                # Smart scroll (respects user scroll-up)
│   │   └── useSTT.ts                       # Web Speech API, graceful degradation
│   ├── context/
│   │   └── ChatContext.tsx                 # React context wrapping useChat
│   └── lib/
│       ├── types.ts                        # All TypeScript interfaces
│       ├── constants.ts                    # Starter prompts, API paths
│       └── utils.ts                        # cn(), formatPrice(), generateId()
```

---

## Component Hierarchy

```
page.tsx
└── ChatProvider (context)
    └── ChatContainer
        ├── Header (logo + "New Chat" button)
        ├── MessageList (scrollable, flex-1)
        │   ├── StarterPrompts (shown when no messages)
        │   │   └── PromptButton × 4
        │   └── MessageBubble (per message)
        │       ├── [user] → teal bubble, right-aligned
        │       └── [assistant] → white, left-aligned
        │           ├── TextBlock (react-markdown)
        │           ├── ProductCard
        │           │   ├── StarRating
        │           │   └── StockBadge
        │           ├── CompatibilityBadge
        │           ├── DiagnosisCard
        │           │   ├── CauseItem[] (with LikelihoodIndicator)
        │           │   ├── Recommended part rows
        │           │   └── Follow-up question buttons
        │           └── StreamingIndicator (if still streaming)
        ├── QuickReplyButtons (after last assistant message)
        └── ChatInput
            ├── VoiceInputButton
            ├── Textarea (auto-resize, Enter=send, Shift+Enter=newline)
            └── SendButton / StopButton (toggles on streaming state)
```

---

## Data Flow

### Message Lifecycle

```
User types → ChatInput.handleSubmit()
  → dispatch(ADD_USER_MESSAGE)        # user bubble appears immediately
  → dispatch(ADD_ASSISTANT_MESSAGE)   # empty assistant bubble appears (streaming=true)
  → useSSE.send() opens POST SSE connection to /api/chat

SSE events arrive:
  status          → dispatch(SET_STATUS)          # "Running search_parts..."
  product_card    → dispatch(ADD_CONTENT_BLOCK)   # ProductCard rendered inline
  compatibility   → dispatch(ADD_CONTENT_BLOCK)   # CompatibilityBadge rendered
  diagnosis       → dispatch(ADD_CONTENT_BLOCK)   # DiagnosisCard rendered
  text_delta      → dispatch(APPEND_TEXT_DELTA)   # appended to current text block
  suggestions     → dispatch(SET_SUGGESTIONS)     # QuickReplyButtons shown after stream
  done            → dispatch(FINALIZE_STREAM)     # streaming=false, indicators removed
```

### Text Delta Append Logic

The reducer's `APPEND_TEXT_DELTA` handler is the key to supporting interleaved content:

1. If the last content block in the assistant message is `{ type: "text" }`, concatenate the delta to it.
2. Otherwise, create a new text block.

This means when a product card arrives between text chunks, the text before the card is block N, the card is block N+1, and text after the card starts as a new block N+2. The `MessageBubble` component renders each block in order, naturally producing interleaved text and rich cards.

### API Proxy

```
Browser → POST /api/chat (Next.js Edge Runtime) → POST /api/chat (FastAPI backend)
                    ↑ pipes response.body through as-is
```

Edge Runtime is required because standard Node.js routes have a response timeout that would kill long SSE streams. The proxy keeps `BACKEND_API_URL` server-side and provides same-origin requests (no CORS).

---

## SSE Protocol

The backend emits Server-Sent Events with this wire format:

```
event: <event_type>
data: <string_or_json>
```

| Event | Data Format | Frontend Action |
|-------|-------------|-----------------|
| `status` | Plain string: `"Running search_parts..."` | Show in StreamingIndicator below message |
| `product_card` | JSON: `ProductCardData` | Insert ProductCard component |
| `compatibility_result` | JSON: `CompatibilityResultData` | Insert CompatibilityBadge component |
| `diagnosis` | JSON: `DiagnosisData` | Insert DiagnosisCard component |
| `text_delta` | Plain string (token chunk) | Append to current text block |
| `suggestions` | JSON: `{ options: string[] }` | Show QuickReplyButtons after stream ends |
| `error` | Plain string | Display error state |
| `done` | Empty | Finalize streaming, remove indicators |

**Typical arrival order:** `status` → structured data events → `text_delta` chunks → `suggestions` → `done`

---

## TypeScript Interfaces

### Message Model

```typescript
type ContentBlock =
  | { type: "text"; text: string }
  | { type: "product_card"; data: ProductCardData }
  | { type: "compatibility_result"; data: CompatibilityResultData }
  | { type: "diagnosis"; data: DiagnosisData }
  | { type: "status"; text: string }

interface Message {
  id: string
  role: "user" | "assistant"
  content: ContentBlock[]       // ordered array of typed blocks
  timestamp: number
  isStreaming?: boolean          // true while SSE is active
  suggestions?: string[]        // populated by suggestions event
}
```

### Backend Data Shapes

**ProductCardData** — emitted for `get_product_details` and `search_parts` tool results:
```typescript
{
  ps_number, name, brand, price, rating, review_count: string
  in_stock: boolean
  image_url, source_url: string
  installation_difficulty?, symptoms_fixed?, description?: optional
}
```

**CompatibilityResultData** — three states based on `confidence`:
```typescript
{
  compatible: boolean | null     // true=verified, null=unknown, never false
  confidence: "verified" | "not_in_data" | "part_not_found"
  part_number, model_number, message: string
  source_url?: string
}
```

**DiagnosisData** — the most complex structure:
```typescript
{
  symptom: string
  causes: Array<{
    cause, description, likelihood: string
    recommended_parts: string[]     // PS numbers
  }>
  recommended_parts: Array<{       // full part objects for mini-cards
    ps_number, name, brand, price, rating: string
    in_stock: boolean
    image_url, source_url: string
  }>
  follow_up_questions: string[]    // rendered as clickable buttons
}
```

---

## State Management

### Reducer Actions

| Action | Trigger | Effect |
|--------|---------|--------|
| `ADD_USER_MESSAGE` | User sends message | Appends user message, sets `isStreaming: true` |
| `ADD_ASSISTANT_MESSAGE` | Immediately after user message | Appends empty assistant message with `isStreaming: true` |
| `APPEND_TEXT_DELTA` | `text_delta` SSE event | Appends text to last text block or creates new one |
| `ADD_CONTENT_BLOCK` | `product_card` / `compatibility_result` / `diagnosis` events | Pushes new block to assistant message's content array |
| `SET_STATUS` | `status` SSE event | Updates `statusText` (shown in StreamingIndicator) |
| `SET_SUGGESTIONS` | `suggestions` SSE event | Attaches options to assistant message |
| `SET_ERROR` | `error` SSE event or network failure | Sets error, stops streaming |
| `FINALIZE_STREAM` | `done` SSE event | Sets `isStreaming: false` on message and global state |
| `CLEAR_MESSAGES` | "New Chat" button | Resets to initial state |

### Why `dispatchRef`

The `useChat` hook stores `dispatch` in a ref (`dispatchRef`) and passes `dispatchRef.current` to SSE callbacks. This avoids recreating the SSE connection when React re-renders — the callbacks always reference the latest dispatch without being listed as dependencies.

---

## Styling System

### PartSelect Brand Tokens

Defined in `globals.css` via Tailwind v4's `@theme inline` block:

| Token | Value | Usage |
|-------|-------|-------|
| `primary-teal` | `#337778` | Header, links, user bubbles, accents |
| `teal-dark` | `#2a6162` | Hover states |
| `teal-light` | `#e8f0f0` | Light backgrounds, symptom tags |
| `cta-yellow` | `#F3C04C` | Send button, focus rings |
| `yellow-dark` | `#d9a83e` | CTA hover |
| `body-text` | `#121212` | All body copy |
| `muted-text` | `#555555` | Secondary text, timestamps |
| `bg-light` | `#F2F2F2` | Panel/input backgrounds |
| `border` | `#DDDDDD` | All borders/dividers |
| `star-filled` | `#F68C1E` | Filled stars |
| `star-empty` | `#CBCDCF` | Empty stars |
| `error-red` | `#AA1E00` | Errors, stop button, out-of-stock |
| `success-green` | `#288500` | In-stock, verified compatible |

### Design Conventions

- **Border radius:** 0px everywhere (PartSelect brand). Only chat bubbles use 2px for minimal softening.
- **Font:** Roboto (loaded from Google Fonts in `layout.tsx`).
- **Viewport:** `100dvh` for full-height layout that handles mobile keyboard.
- **Mobile-first:** Cards stack vertically, min 44px touch targets, fixed input at bottom.

### Animations

| Name | Usage | Defined in |
|------|-------|------------|
| `bounce-dot` | StreamingIndicator's three dots | `globals.css` |
| `mic-pulse` | Red pulse on VoiceInputButton while recording | `globals.css` |
| `fade-in` | Message bubbles, cards, quick reply buttons | `globals.css` |

---

## Rich Components

### ProductCard

Renders part details from the backend's `get_product_details` and `search_parts` tools. Displays image, name, PS number, brand, price, star rating, stock status, installation difficulty, and symptom fix tags. Links to PartSelect.com via `source_url`.

### CompatibilityBadge

Three visual states based on `confidence`:
- **Verified** (`compatible: true`): Green left border, check icon, "Compatible"
- **Not in data** (`compatible: null, confidence: "not_in_data"`): Amber left border, warning icon, "Unable to Verify"
- **Part not found** (`compatible: null, confidence: "part_not_found"`): Amber left border, warning icon, "Unable to Verify"

The backend never returns `compatible: false` — it returns `null` with a `not_in_data` confidence when it can't confirm. The red "Not Compatible" state exists for future use.

### DiagnosisCard

The most complex component. Sections:
1. **Header** — teal banner with symptom description
2. **Possible Causes** — each with a likelihood indicator (High=red, Medium=amber, Low=green) and description
3. **Recommended Parts** — mini part rows with image, price, stock status, and external link
4. **Follow-up Questions** — clickable buttons that send the question as a new user message via `onFollowUp`

---

## Session Management

- On first load, `useSession` generates a UUID via `crypto.randomUUID()` and stores it in `localStorage` under key `partselect_session_id`.
- Every chat message includes this session ID. The backend uses it to maintain conversation history.
- "New Chat" calls `resetSession()`, which generates a new UUID. This effectively starts a fresh conversation on the backend.

---

## Voice Input

`useSTT` wraps the Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`):

- **Graceful degradation:** `isSupported` is false if the API isn't available; the mic button hides itself.
- **Single utterance:** `continuous: false` — records one phrase, then stops automatically.
- **Append mode:** Transcript is appended to the current input text, not replaced.
- **Visual feedback:** Red pulse animation on the mic button while listening.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 16.1.6 | Framework (App Router, Edge Runtime) |
| `react` / `react-dom` | 19.2.3 | UI library |
| `tailwindcss` | 4.x | Utility-first CSS |
| `@microsoft/fetch-event-source` | ^2.0.1 | POST-capable SSE client |
| `react-markdown` | ^10.1.0 | Markdown → React rendering |
| `remark-gfm` | ^4.0.1 | GitHub Flavored Markdown support |
| `lucide-react` | ^0.577.0 | Icon library |
| `clsx` + `tailwind-merge` | ^2.1 / ^3.5 | Conditional class merging (`cn()`) |
| `class-variance-authority` | ^0.7.1 | Component variant patterns |
| `tailwindcss-animate` | ^1.0.7 | Animation utilities |

---

## Running

```bash
# Development
cd frontend
npm run dev          # → http://localhost:3000

# Production build
npm run build
npm start

# Backend must be running for chat to work
cd ../backend
uvicorn app.main:app --reload   # → http://localhost:8000
```

**Environment:** Set `BACKEND_API_URL` in `.env.local` (defaults to `http://localhost:8000`).

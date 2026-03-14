# PartSelect Chat Agent — Task Definition

## Overview

Build a production-quality AI chat agent for [PartSelect.com](https://www.partselect.com), an e-commerce site with 2M+ OEM appliance replacement parts. The agent is scoped to **Refrigerator** and **Dishwasher** parts only, and must handle product lookup, compatibility checks, symptom-based troubleshooting, and installation guidance.

This is a case study submission for **InstaLILY AI** — a $28M-funded startup building domain-specific AI "teammates" for distributors and field-service operations. The submission includes source code and a Loom video walkthrough.

---

## What the Agent Must Do

### Core Capabilities

| Capability | Description | Example Query |
|---|---|---|
| **Part Lookup** | Find parts by PS number, manufacturer number, or natural language description | *"Find part PS11752778"* or *"I need a water inlet valve for my dishwasher"* |
| **Compatibility Check** | Verify whether a specific part fits a given appliance model | *"Is this part compatible with my WDT780SAEM1?"* |
| **Symptom Diagnosis** | Walk users from a vague complaint → narrowing questions → specific part recommendation | *"The ice maker on my Whirlpool fridge isn't working"* |
| **Installation Help** | Provide installation steps, difficulty rating, and link to repair videos | *"How do I install part PS11752778?"* |
| **Scope Guardrails** | Politely redirect any queries outside refrigerator/dishwasher parts | *"Can you help me fix my washing machine?"* → redirect |
| **Voice Input (STT)** | Browser-native speech-to-text via microphone; speak instead of type | 🎤 button on input; hands-free repair queries |

### Stretch Capabilities (if time permits)

- **Read Aloud (TTS)** — 🔊 button per message using Web Speech API `SpeechSynthesis`; step-by-step reading for install guides
- **Image Upload** — User photographs a broken part or model sticker; agent identifies it
- **Part Comparison** — Side-by-side comparison when multiple parts could solve the problem
- **Conversation Export** — "Email me this diagnosis" summary with model, symptom, part, and price

---

## What PartSelect.com Gives Us

PartSelect is a data-rich site with highly structured, scrapable content. Key data per product page:

- **Dual part IDs**: PartSelect number (PS prefix) + manufacturer part number
- **Price & stock status**
- **Star ratings & review counts**
- **Installation difficulty rating** (1–5 scale)
- **Customer-submitted installation instructions**
- **Expert Q&A threads**
- **Compatible model lists** (often 50–200+ models per part)
- **Links to YouTube repair videos** (2,000+ total on the site)
- **Product images**

### Key URL Patterns

```
Product pages:   /PS{number}-{Brand}-{MfgPartNo}-{Part-Name}.htm
Model pages:     /Models/{MODEL_NUMBER}/
Repair guides:   /Repair/{Appliance}/{Symptom}/
Symptom tool:    /Instant-Repairman/
```

### Existing Symptom-to-Part Mappings

PartSelect's **Instant Repairman** and **Repair Help** sections already map common symptoms to likely replacement parts:

**Refrigerator**: not cooling, ice maker broken, water leaking, unusual noises, door seal issues
**Dishwasher**: not draining, leaking, not cleaning, door latch broken, unusual noises

This structured data is the foundation for the agent's troubleshooting flows.

---

## Success Criteria (from case study brief)

The submission is evaluated on:

1. **Interface Design** — Polished, branded chat UI with rich components (product cards, quick replies)
2. **Agentic Architecture** — Modular tool-calling design that's easy to reason about
3. **Extensibility & Scalability** — "Adding washing machines takes hours, not weeks"
4. **Query Accuracy** — Correct part recommendations, accurate compatibility checks
5. **User Experience** — Fast responses, guided flows, helpful when confused

### Benchmark Queries (must handle well)

1. *"How can I install part number PS11752778?"*
2. *"Is this part compatible with my WDT780SAEM1 model?"*
3. *"The ice maker on my Whirlpool fridge is not working. How can I fix it?"*

---

## Competitive Landscape

- **42 candidates** have forked the official `Instalily/case-study` repo on GitHub
- Only **1 fully public implementation** exists (`zehuiwu/partselect-agent`) — uses Python + OpenAI + MySQL + MCP servers
- PartSelect has **no AI chatbot deployed today** — only basic live chat and phone support
- The real-world analog is **iFixit's FixBot** (launched Dec 2025) — a symptom-based diagnosis chatbot for repairs

### What Differentiates Strong Submissions

Based on Glassdoor reviews and analysis of past submissions:

- **Live deployed demo** (not just localhost) — Vercel + Railway/Render
- **Architecture diagram** with clear tool-calling flow
- **Hybrid retrieval** (keyword for part numbers + semantic for natural language)
- **Rich chat UI** with product cards, quick-reply buttons, starter prompts
- **Awareness of InstaLILY's philosophy** — domain-specific agents, not generic chatbot wrappers
- **Self-assessment** — what you'd do differently with more time

---

## Constraints

- **Timeline**: < 1 week
- **Scope**: Refrigerator + Dishwasher as primary focus; all other appliance types scraped for fallback
- **Search strategy**: Tier 1 (fridge/dishwasher) → Tier 2 (all products) → Tier 3 (not found with suggestions)
- **Data**: Full catalog scrape (~1,000–1,500 products across all categories + fridge/dishwasher repair guides)
- **Deliverables**: Source code + Loom walkthrough video
- **Presentation**: 1-hour final round with engineering team (Q&A on design decisions)

---

## Tech Stack (Decided)

| Layer | Technology |
|---|---|
| Frontend | Next.js + Tailwind + shadcn/ui |
| Backend | Python FastAPI |
| LLM (Chat) | Gemini 2.5 Flash (primary) — fastest latency + function calling |
| Embeddings | Gemini Embedding 2 (`gemini-embedding-2-preview`) — multimodal, unified space |
| Vector DB | ChromaDB (local, zero-config) |
| Scraping | BeautifulSoup + requests (PartSelect is server-rendered) |
| Deploy | Vercel (frontend) + Railway (backend) |

# Loom Walkthrough Script

**Target length:** 8-12 minutes
**Setup:** Have 3 tabs open before recording:
1. PowerPoint/Google Slides with the presentation
2. GitHub README (or local preview)
3. Live demo at website-chat-agent.vercel.app (fresh session, no chat history)

---

## PART 1: Presentation (3-4 minutes)

### Slide 1 — Title (5 sec)
> "Hi, I'm Aryaman. This is my PartSelect AI Chat Agent — a domain-specific AI assistant built with a custom agent loop for the Instalily case study."

### Slide 2 — The Problem (20 sec)
> "PartSelect has over 2 million OEM appliance parts. Customers today have no AI-assisted way to search, diagnose, or verify compatibility — they're stuck with basic live chat and phone support. They struggle with four things: finding the right part, verifying it fits their model, diagnosing symptoms, and understanding how hard a repair is."

### Slide 3 — The Solution (20 sec)
> "So I built a domain-specific agent — not a generic chatbot wrapper — that understands part numbers, model compatibility, symptoms, and installation. It has six core capabilities: part lookup with hybrid search, compatibility checking against over 162,000 model mappings, symptom diagnosis using 159 repair guides and 51 blog articles, installation guidance, scope guardrails, and voice input."

### Slide 4 — UX User Stories (20 sec)
> "Each of these maps to a real user story. Someone who only knows their model number, someone with a symptom but no idea what's broken, someone who found a part but needs to verify it fits, someone wondering if they can DIY the repair, and someone mid-repair with greasy hands who needs to speak instead of type."

### Slide 5 — Style & Branding (15 sec)
> "The interface isn't a generic chatbot widget — it's designed to feel like a native extension of PartSelect.com. Same teal color system, same blocky card layout, same information-dense component style. Users see familiar patterns, which builds trust."

**[Skip screenshot slides 6-10 — you'll show these live in the demo]**

### Slide 11 — Architecture (30 sec)
> "The architecture is straightforward. The Next.js frontend connects to a FastAPI backend via Server-Sent Events. The backend runs a custom while-loop agent — about 50 lines of Python. The LLM receives the user's message, decides which tool to call, executes it, reads the result, and either calls another tool or streams the final answer. No LangChain, no LlamaIndex — fully debuggable and easy to reason about."

### Slide 12 — Five Tools (20 sec)
> "The agent has five domain-specific tools. Search parts with hybrid semantic and keyword search. Check compatibility with exact model lookups. Diagnose symptoms using repair guides and blogs. Get installation guides with difficulty ratings and videos. And get full product details for rendering rich cards. Every tool has a required reasoning parameter — the LLM has to explain why it's calling that tool, which improves accuracy and creates an audit trail."

### Slide 13 — Walkthrough (20 sec)
> "Here's what a multi-step query looks like. The user says 'my dishwasher won't drain, I have model WDT780SAEM1.' The agent calls diagnose_symptom, gets 6 ranked causes, then calls search_parts to find matching parts, then calls check_compatibility to verify the part fits their model. All three tool calls happen in a single turn — the LLM chains them automatically."

### Slide 14 — LLM Choice (15 sec)
> "I chose Gemini 2.5 Flash as the default LLM. For a support chatbot, perceived speed is everything — 250 millisecond time-to-first-token feels instant. But the agent loop is model-agnostic. Swapping to a different model is a single config change — the tools use standard JSON schema, no vendor lock-in."

### Slide 15 — Guardrails (40 sec)
> "The agent stays in scope through three independent layers — and this is defense in depth, not redundancy. Each layer catches things the others might miss."
>
> "Layer one is the system prompt. It instructs the LLM to specialize in refrigerators and dishwashers, and includes few-shot examples of correct tool routing. This is the primary defense for on-topic queries where the LLM just needs to stay focused."
>
> "Layer two is a rule-based classifier that runs *before* the LLM is ever called. It's pure regex and keyword matching — zero latency, zero cost. It checks the user's message against five pattern groups: appliance keywords like 'fridge' or 'dishwasher', part-related terms like 'gasket' or 'PS' numbers, repair keywords like 'broken' or 'leaking', other-appliance keywords like 'washer' or 'dryer', and greeting patterns. If it detects an off-topic or other-appliance intent, it returns a canned redirect immediately — the LLM never sees that message, so we pay nothing for it. I'll show this in the demo."
>
> "Layer three is metadata filtering at the data level. When the search_parts tool queries ChromaDB, tier-1 search restricts results to `appliance_type` equals refrigerator or dishwasher. Even if the LLM somehow ignores the system prompt and tries to search for washer parts, ChromaDB physically won't return them in tier-1. It has to fall through to tier-2 — which searches all products but flags the results with a scope note. So the data layer itself enforces the boundary."

### Slide 16 — Extensibility (30 sec)
> "Adding a new appliance like washing machines takes one to two hours — just add it to the metadata filter, scrape repair guides, and update the system prompt. No re-embedding, no code changes. Adding a new tool takes about half a day. And swapping the LLM is one config value. This works because we indexed all appliance types upfront — scope filtering happens at query time, not ingestion."
>
> "And there's another extensibility dimension worth mentioning — we chose Gemini Embeddings specifically because they support multimodal vectors. Right now we embed text, but the same embedding model can embed images into the same vector space. So in the future, a user could photograph a broken part or their model number sticker, and we'd match it against our existing product vectors — no separate image model pipeline, no re-embedding the catalog. The infrastructure is already there."

**[Skip Tech Stack slide — it's in the README]**

### Slide 18 — Closing (10 sec)
> "So to summarize against the four evaluation criteria: interface design with rich cards and PartSelect branding, a custom agentic architecture that's fully debuggable, extensibility that makes adding features trivial, and query accuracy backed by 162,000 model mappings and 159 repair guides. Let me show you this live."

---

## PART 2: README & Architecture (1-2 minutes)

**[Switch to GitHub/README tab]**

> "Here's the GitHub repo. You can see the hero screenshots showing a multi-turn conversation with diagnosis, product cards, and a compatibility check."

**[Scroll to the Architecture section]**

> "The architecture diagram shows the full data flow — from the browser through the Next.js frontend, SSE streaming to the FastAPI backend, through the agent loop, into the tool layer, and down to the data layer with ChromaDB and the structured JSON store. The key thing is that ChromaDB handles semantic search while the JSON store handles exact lookups for part numbers and model compatibility."

**[Scroll to the Tools table]**

> "Each tool is registered as a Gemini function declaration. The agent decides which to call based on the user's intent — sometimes it chains multiple tools in a single turn."

**[Scroll to Getting Started]**

> "The project is fully set up for local development — backend with uv, frontend with npm, and there's a Dockerfile for the backend. Tests are included for both."

---

## PART 3: Live Demo (4-5 minutes)

**[Switch to the live demo tab — website-chat-agent.vercel.app]**

### Demo 1: Welcome Screen + Starter Prompts (15 sec)
> "This is the welcome screen. Four starter prompts guide users to common tasks — ice maker issues, finding a specific part, checking compatibility, and dishwasher drainage. The input bar at the bottom has a mic button for voice input and a disclaimer showing scope."

### Demo 2: Benchmark Query 1 — Symptom Diagnosis (60 sec)
**Type:** `The ice maker on my Whirlpool fridge is not working`

> "Let's start with one of the benchmark queries. I'm asking about a broken ice maker."

**[Wait for response to stream in]**

> "The agent called diagnose_symptom. You can see it identified multiple possible causes — water fill tubes, water inlet valve, ice maker assembly — each with descriptions. It also recommended specific replacement parts with prices and ratings. And there are follow-up questions at the bottom to help narrow down the issue. Notice the diagnosis card renders with structured data — this isn't just raw text from the LLM."

### Demo 3: Benchmark Query 2 — Compatibility Check (45 sec)
**Type:** `Is PS10065979 compatible with model WDT780SAEM1?`

> "Now a compatibility check — the second benchmark query."

**[Wait for response]**

> "The agent called check_compatibility and returned a verified compatible badge — green checkmark, part number, model number, and a direct link to the PartSelect product page. This is an exact lookup against our 162,976 model mappings, not a guess from the LLM."

### Demo 4: Benchmark Query 3 — Installation Guide (45 sec)
**Start a new chat**, then **type:** `How can I install part number PS11752778?`

> "Third benchmark query — installation guidance."

**[Wait for response]**

> "The agent returned installation details — you can see the product card with the part info, difficulty rating, and the agent's response includes installation steps and context from our repair guides. It also fetched the full product details so you can see the price, rating, and stock status."

### Demo 5: Voice Input (20 sec)
> "Let me show voice input. I'll click the mic button..."

**[Click mic, say: "my dishwasher won't drain"]**

> "The speech was transcribed directly into the input field using the browser's Web Speech API — completely client-side, no API cost. I can now send this as a normal message."

**[Send the message, let it respond briefly]**

### Demo 6: Guardrail — Off-Topic (30 sec)
**Type:** `Can you write me a python program to sort a list?`

> "Now let me show the guardrails in action. This is a completely off-topic request."

**[Wait for response — it should be instant]**

> "Notice how fast that response was — essentially instant. That's because the rule-based classifier caught it *before* it ever hit the LLM. The classifier didn't find any appliance keywords, part numbers, model numbers, or repair terms in that message, so it classified it as off-topic and returned a canned redirect. We paid zero API cost and zero latency for that interaction."

### Demo 6b: Guardrail — Other Appliance (20 sec)
**Type:** `My washing machine is making a loud noise`

> "Now an other-appliance query — washing machine. This is a different classification."

**[Wait for response — also instant]**

> "The classifier detected 'washing machine' as an other-appliance keyword, so it redirected to PartSelect.com for that appliance type — again without calling the LLM. If I had asked about a *dishwasher* making a loud noise, it would have gone through to the agent normally."

### Demo 7: Multi-Turn / Multi-Intent (30 sec, optional if time allows)
**Type:** `Find me a water filter for my refrigerator`

**[Wait for product results, then follow up with:]**
`Is that compatible with model WRS321SDHZ08?`

> "And this shows multi-turn context. The agent remembers what we were discussing and checks compatibility for the part it just recommended, chaining tool calls naturally."

---

## PART 4: Closing (15-20 sec)

> "That covers the four evaluation criteria: interface design with rich branded components, a custom agentic architecture with a 50-line agent loop, extensibility where adding a new appliance is a two-hour change, and query accuracy backed by real data — 4,170 parts, 162,000 model mappings, and 159 repair guides. The live demo is at website-chat-agent.vercel.app and the source code is on GitHub. Thanks for watching."

**[End recording]**

---

## Tips for Recording

- **Screen resolution:** Use a clean browser window, no bookmarks bar, no other tabs visible
- **Font size:** Zoom the browser to 110-125% so text is readable on video
- **Pace:** Don't rush — let the streaming responses complete before talking over them
- **Pauses:** Brief silence while the agent responds is fine and shows real latency
- **If something fails:** Don't panic. Say "let me try that again" — it shows authenticity
- **Cursor:** Move your cursor to point at things you're referencing (cards, badges, etc.)
- **Total time target:** 8-12 minutes. The presentation section moves fast; the demo section is where you slow down and let the product speak

# AstroAgent

A conversational astrology companion built for Aradhana. You share your birth details, it computes your actual natal chart using real planetary data, and then you can ask it anything — your career, relationships, what the energy looks like today, your Saturn return. It reasons in steps, calls tools to get real data, and responds with warmth.

Everything runs on free tools. The only key you need is a free Google AI Studio (Gemini) API key — no credit card.

---

## How it works

The backend is a LangGraph agent. Instead of one big prompt that guesses at planetary positions, it calls tools — a real Swiss Ephemeris library for the chart math, a geocoder to resolve your city to coordinates, a transits tool for today's sky, and a small RAG knowledge base for interpretation. The agent loops through reasoning and tool calls until it has what it needs, then responds.

```
START → router → sensitivity_gate → reasoning ──→ tools → cache_chart → reasoning (loop)
                                               ↘ safety → editor → END
```

- **router** — classifies intent: chart request, daily horoscope, freeform question, off-topic
- **sensitivity_gate** — pauses for user confirmation before readings on sensitive topics (human-in-the-loop)
- **reasoning** — the LLM works through what to do next and which tools to call
- **tools** — geocode place, compute birth chart, get today's transits, look up knowledge base
- **cache_chart** — saves the computed chart to session state so it isn't recomputed on every turn
- **safety** — catches overly certain medical/legal/financial language; handles off-topic with a warm redirect
- **editor** — second LLM pass to soften tone on full chart readings without changing any facts

---

## What's implemented

### Core features

**Real chart computation** — planetary positions via pyswisseph (Swiss Ephemeris). No guessing, no approximation.

**Session memory** — your chart and birth details are saved in SQLite after the first computation. Come back in a new tab or a new browser session and you won't be asked for your details again. The chart doesn't recompute either.

**Streaming responses** — the UI renders tokens as they arrive via SSE, with a live activity chip showing what tool is running.

**RAG knowledge base** — 7 markdown files covering chart interpretation indexed into ChromaDB. The agent looks these up when interpreting placements rather than relying on training data alone.

**Eval harness** — 30 golden-set cases across 7 categories. One command runs the whole thing, prints a scorecard, and saves a timestamped CSV. Latest run: 30/30, p50 8s.

---

### Optional features (all implemented)

**Chart caching across sessions** — the computed birth chart is stored in state after the first call and persisted in SQLite. On every subsequent message in the same session, the agent reads from the cache rather than running geocode + ephemeris again. The context summary at the top of every system prompt reflects the cached chart, so the agent always knows what was computed without re-reading the full tool message history.

**Second editor agent** — after the safety node, the `editor` node makes a second LLM pass over the response. Its job is narrow: if anything reads as cold, alarming, or overly definitive about uncertain outcomes, rephrase just that part. All chart facts — degrees, signs, planetary positions — are left untouched. It only runs for chart and freeform answers longer than 500 characters; short safety refusals and off-topic redirects pass straight through. Because the reading has already streamed token-by-token, the editor's own tokens are tagged and suppressed from the live stream, and its polished version (reusing the original message id, so the history isn't duplicated) is sent as a single `replace` event the UI swaps in. The trade-off is honest: on long readings the editor adds one more LLM call before the turn finishes, and on the free tier that's extra latency.

**Human-in-the-loop** — the `sensitivity_gate` node uses LangGraph's `interrupt()` to pause graph execution before processing questions about death timing ("when will I die", "predict my death", etc.). When triggered, the frontend receives a `confirmation_needed` SSE event and shows a dialog asking the user if they'd like the reading framed around transformation and cycles rather than literal predictions. On confirmation, the frontend calls the new `/resume` endpoint, which uses `Command(resume=...)` to continue the graph from the saved `MemorySaver` checkpoint. On decline, a warm redirect is returned instead.

**Prompt injection handling** — when the underlying model fires its own safety layer and returns a flat refusal ("I'm sorry, but I can't provide that."), the safety node detects it (length < 120 chars, refusal phrase present) and replaces it with an in-character Aradhana response that acknowledges the framing and offers a real reading instead.

---

## Free stack

| Component | Tool | Cost |
|---|---|---|
| LLM | Google Gemini — `gemini-flash-lite-latest` via Google AI Studio | Free |
| Ephemeris | pyswisseph (Swiss Ephemeris) | Free / open source |
| Geocoding | Nominatim via geopy (OpenStreetMap) with local city cache | Free |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2`, runs locally | Free |
| Vector DB | ChromaDB, runs locally | Free |
| Session store | SQLite (ships with Python) | Free |
| HITL checkpointer | LangGraph MemorySaver (in-process) | Free |

---

## Project structure

```
frontend/
  index.html      — app entry point (served at http://localhost:8000/)
  aradhana.css    — design tokens, keyframes, base styles
  cosmic.jsx      — animated star field + nebula background
  logo.jsx        — lotus mark + full logo lockup with orbit ring
  form.jsx        — birth details sidebar (date, time, place inputs)
  chat.jsx        — chat panel, message bubbles, tool activity chip, HITL dialog
  agent.jsx       — SSE transport, runResume() for HITL, offline mock fallback
  app.jsx         — root layout, session wiring, HITL confirmation handler

backend/
  agent/
    state.py      — AgentState, BirthDetails types
    graph.py      — LangGraph graph (7 nodes) + MemorySaver checkpointer
    nodes.py      — router, sensitivity_gate, reasoning, editor, safety, helper fns
    llm.py        — Gemini client (single place to change the model)
    prompts.py    — system prompt: tone, tool instructions, injection handling
    tools/
      geocode.py      — geocode_place() with 80+ city cache
      birth_chart.py  — compute_birth_chart() via pyswisseph
      transits.py     — get_daily_transits()
      knowledge.py    — knowledge_lookup() via ChromaDB + sentence-transformers
  api/
    main.py       — FastAPI: /chat (SSE), /resume (HITL), /session/{id}, static frontend
  db/
    sessions.py   — SQLite store (conversation history + cached chart + birth details)
  data/
    astrology_notes/  — 7 markdown files indexed into ChromaDB for RAG
  requirements.txt

eval/
  golden_set.jsonl   — 30 versioned test cases across 7 categories
  run_eval.py        — one-command eval runner
  judge.py           — LLM-as-judge with 4-dimension rubric
  summarize.py       — quick stats summary from the latest results CSV
  results/           — scorecard CSVs from each run
```

---

## Setup

You need Python 3.11+. Get a free Gemini API key at https://aistudio.google.com — no credit card needed.

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# open .env and paste your GEMINI_API_KEY
```

**Ephemeris files:** pyswisseph falls back to the built-in Moshier ephemeris (good for 1800–2400) without external data files. For higher precision download the files from https://www.astro.com/swisseph/ and put them in `backend/ephe/`.

Start the server:

```bash
uvicorn api.main:app --reload
```

API at `http://localhost:8000`. Hit `/health` to confirm it's running.

---

## Frontend

No build step. The FastAPI server serves the frontend automatically at `http://localhost:8000/`. Babel compiles the JSX in the browser.

If the backend is unreachable (for example, opening the HTML file directly without a server), `agent.jsx` falls back to a built-in mock astrologer so the UI stays usable during design review.

---

## Running the eval

```bash
python eval/run_eval.py
```

Server must be running first. Runs all 30 cases, prints a live scorecard, and saves a CSV to `eval/results/`. A score drop between runs is treated like a regression.

Latest run: **30/30**, p50 8s / p95 11s, $0.00 (free tier). That's a clean pass on a small single-turn suite, not proof of perfection — see [EVALUATION.md](EVALUATION.md) for the honest breakdown, the judge-validation spot-check, and a harness bug the validation caught.

---

## Graph flow

```
                   ┌──────────────────────────────────────────┐
                   │               AgentState                  │
                   │  messages · birth_details · birth_chart   │
                   │  intent · tool_calls_made · step_count    │
                   └──────────────────────────────────────────┘
                                      │
                                 [START]
                                      │
                               ┌──────▼──────┐
                               │   router    │  classifies intent
                               └──────┬──────┘
              ┌────────────────────────┼──────────────────┐
       chart / horoscope /         freeform           off_topic
            freeform                   │                   │
              └────────────┬───────────┘                   │
                   ┌───────▼───────┐                       │
                   │sensitivity_gate│  HITL interrupt       │
                   └───────┬───────┘  on death-timing       │
              confirmed    │ cancelled                      │
                   ┌───────▼──────┐                        │
           ┌───────│  reasoning   │◄──────┐                │
           │       └──────┬───────┘       │                │
      tool_calls?         │               │                │
           │          no tools            │                │
           │              │               │                │
    ┌──────▼──────┐  ┌────▼──────┐        │                │
    │    tools    │  │  safety   │◄────cancelled────────────┘
    └──────┬──────┘  └────┬──────┘
           │              │
    ┌──────▼──────┐  ┌────▼──────┐
    │ cache_chart │  │  editor   │  second-agent tone pass
    └──────┬──────┘  └────┬──────┘
           │             [END]
     back to reasoning
```

---

## Session persistence

Each conversation is stored in `backend/sessions.db`. When a user sends a new message with the same `session_id`, the API loads their full message history, cached birth details, and the computed chart — so they never re-enter details and the chart never recomputes after the first time.

`GET /session/{session_id}` returns session metadata (has_chart, birth_details, timestamps) without the full message history.

---

## Known limitations

- Birth time is required for accurate house cusps and the Ascendant. When it's missing the agent defaults to noon and notes the limitation.
- Geocoding uses Nominatim (OpenStreetMap). Very small or ambiguous place names may not resolve — the agent asks for clarification.
- The HITL MemorySaver checkpointer is in-process and doesn't survive a server restart. A pending confirmation would be lost on restart. For production, swap MemorySaver for SqliteSaver.
- The LLM judge is validated by spot-checking all 6 judged cases by hand (verdict agreement 6/6); I'd grade the two edge cases more generously than it does. The judge runs on a single small set — thin evidence on its own. See EVALUATION.md.
- The UI uses in-browser Babel — no build step, but slower initial load than a pre-built bundle. Run through Vite for production.

---

## Evaluation

See [EVALUATION.md](EVALUATION.md) for the full write-up: methodology, scorecard, honest failure analysis, and what would be fixed with more time.

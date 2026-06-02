# AstroAgent

A conversational astrology companion built for Aradhana. You share your birth details, it computes your actual natal chart using real planetary data, and then you can ask it anything — your career, relationships, what the energy looks like today, your Saturn return. It reasons in steps, calls tools to get real data, and responds with warmth.

Everything runs on free tools. No paid API keys required except a free OpenRouter account.

---

## How it works

The backend is a LangGraph agent. Instead of one giant prompt that guesses at planetary positions, it calls tools — a real Swiss Ephemeris library for chart math, a geocoder to resolve your city to coordinates, a transits tool for today's sky, and a small RAG knowledge base for interpretation. The agent loops through reasoning and tool calls until it has what it needs, then responds.

```
START → router → reasoning ──→ tools → cache_chart → reasoning (loop)
                          ↘ safety → END
```

- **router** — classifies intent: chart request, daily horoscope, freeform, off-topic
- **reasoning** — the LLM thinks through what to do and which tools to call
- **tools** — geocode place, compute birth chart, get transits, look up knowledge base
- **cache_chart** — stores the computed chart in session state so it isn't recomputed each turn
- **safety** — strips medical/legal/financial certainty language; handles off-topic with a warm redirect

---

## Free stack

| Component | Tool | Cost |
|---|---|---|
| LLM | OpenRouter — `openai/gpt-oss-20b:free` (fast, reliable tool calling) | Free |
| Ephemeris | pyswisseph (Swiss Ephemeris) | Free / open source |
| Geocoding | Nominatim via geopy (OpenStreetMap) | Free |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2`, runs locally | Free |
| Vector DB | ChromaDB, runs locally | Free |
| Session store | SQLite (built into Python) | Free |

---

## Project structure

```
frontend/
  index.html      — app entry point (served at http://localhost:8000/)
  aradhana.css    — design tokens, keyframes, base styles
  cosmic.jsx      — animated star field + nebula background
  logo.jsx        — lotus mark + full logo lockup with orbit ring
  form.jsx        — birth details sidebar (date, time, place inputs)
  chat.jsx        — chat panel, message bubbles, tool activity chip
  agent.jsx       — SSE transport with offline mock fallback
  app.jsx         — root layout, session wiring, mobile drawer

backend/
  agent/
    state.py      — AgentState, BirthDetails types
    graph.py      — LangGraph graph with cache_chart node
    nodes.py      — router, reasoning, safety, should_use_tools
    llm.py        — OpenRouter client (single place to configure the model)
    prompts.py    — system prompt with tone, tool instructions, safety rules
    tools/
      geocode.py      — geocode_place()
      birth_chart.py  — compute_birth_chart() via pyswisseph
      transits.py     — get_daily_transits()
      knowledge.py    — knowledge_lookup() via ChromaDB + sentence-transformers
  api/
    main.py       — FastAPI, SSE /chat endpoint, GET /session/{id}, static frontend
  db/
    sessions.py   — SQLite session store (load/save conversation history + chart cache)
  data/
    astrology_notes/  — 7 markdown files indexed into ChromaDB for RAG
  requirements.txt

eval/
  golden_set.jsonl   — 30 versioned test cases across 7 categories
  run_eval.py        — one-command eval runner
  judge.py           — LLM-as-judge with 4-dimension rubric
  results/           — scorecard CSVs from each run
```

---

## Setup

You need Python 3.11+. Get a free OpenRouter key at https://openrouter.ai — no credit card needed.

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# open .env and paste your OPENROUTER_API_KEY
```

**Ephemeris files:** pyswisseph falls back to the built-in Moshier ephemeris (good for 1800–2400) without external data files. For maximum precision download the files from https://www.astro.com/swisseph/ and place them in `backend/ephe/`.

Start the server:

```bash
uvicorn api.main:app --reload
```

API runs at `http://localhost:8000`. Hit `/health` to confirm.

---

## Frontend

The UI is a zero-build React app that the FastAPI server serves automatically at `http://localhost:8000/`.

```
frontend/
  index.html    — entry point
  aradhana.css  — design tokens, keyframes, base styles
  cosmic.jsx    — animated star field background
  logo.jsx      — lotus mark + full Aradhana logo lockup
  form.jsx      — birth details sidebar (date, time, place)
  chat.jsx      — chat panel, message bubbles, tool activity chip
  agent.jsx     — SSE transport + offline mock astrologer fallback
  app.jsx       — root layout, session state, mobile drawer
  Logo.svg      — lotus favicon
```

No `npm install`, no build step. Babel compiles the JSX in the browser. Open the app at `http://localhost:8000/` once the server is running.

If the backend is unreachable (e.g. opening the HTML file directly), `agent.jsx` falls back to a built-in mock astrologer so the UI still feels alive during design review.

---

## Running the eval

```bash
python eval/run_eval.py
```

Server must be running. Runs all 30 golden set cases, prints a scorecard, saves a CSV to `eval/results/`. A score drop between runs is treated like a failing test.

---

## Graph diagram

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
              ┌───────────────────────┼──────────────────┐
              │                       │                  │
       chart / horoscope /       freeform          off_topic
            freeform                  │                  │
              └───────────┬───────────┘                  │
                    ┌─────▼──────┐                       │
           ┌────────│  reasoning │◄──────┐               │
           │        └─────┬──────┘       │               │
      tool_calls?         │              │               │
           │         no tools            │               │
           │              │              │               │
    ┌──────▼──────┐  ┌────▼──────┐      │               │
    │    tools    │  │  safety   │◄─────┴───────────────┘
    └──────┬──────┘  └────┬──────┘
           │              │
    ┌──────▼──────┐     [END]
    │ cache_chart │  caches chart
    └──────┬──────┘  in state
           │
     back to reasoning
```

---

## Session persistence

Each conversation is stored in `backend/sessions.db` (SQLite). When a user sends a new message with the same `session_id`, the API loads their full message history and cached birth chart — so they never have to re-enter details or wait for the chart to recompute.

The `GET /session/{session_id}` endpoint returns session metadata (has_chart, birth_details, timestamps) without the full message history.

---

## Known limitations

- Birth time is required for accurate house cusps and Ascendant. When missing, the agent defaults to noon and notes the limitation.
- Geocoding uses Nominatim (OpenStreetMap). Very small or ambiguous place names may not resolve — the agent asks the user to clarify.
- The LLM judge in the eval is validated by spot-checking 10 verdicts manually. See EVALUATION.md.
- The UI uses in-browser Babel to compile JSX — no build step required, but it is slower to load than a pre-built bundle. For production, run it through Vite or a similar bundler.

---

## Evaluation

See [EVALUATION.md](EVALUATION.md) for a full write-up: what the eval revealed, where the agent falls short, and what would be fixed with more time.

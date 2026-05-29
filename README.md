# AstroAgent

A conversational astrology companion built for Aradhana. You share your birth details, it computes your actual natal chart using real planetary data, and then you can ask it anything — your career, relationships, what the energy looks like today, your Saturn return. It reasons in steps, calls tools to get real data, and responds with warmth.

Everything here runs on free tools. No paid API keys required except a free OpenRouter account.

---

## How it works

The backend is a LangGraph agent. Instead of one giant prompt that guesses at planetary positions, it actually calls tools — a real Swiss Ephemeris library for chart math, a geocoder to resolve your city to coordinates, a transits tool for today's sky, and a small knowledge base for interpretation. The agent loops through reasoning and tool calls until it has what it needs, then responds.

```
START → router → reasoning ──→ tools → reasoning (loop)
                          ↘ safety → END
```

- **router** — figures out what you're asking (chart request, daily horoscope, general question, off-topic)
- **reasoning** — the LLM thinks through what to do and which tools to call
- **tools** — geocode place, compute birth chart, get transits, look up knowledge base
- **safety** — strips any language that sounds like medical, legal, or financial certainty before the response goes out

---

## Free stack

| Component | Tool | Cost |
|---|---|---|
| LLM | OpenRouter free tier (Llama 3.1 8B, Gemma, Mistral) | Free |
| Ephemeris | pyswisseph (Swiss Ephemeris) | Free / open source |
| Geocoding | Nominatim via geopy (OpenStreetMap) | Free |
| Embeddings | sentence-transformers (runs locally) | Free |
| Vector DB | ChromaDB (local) | Free |
| Database | SQLite | Free |

---

## Project structure

```
backend/
  agent/
    state.py      — AgentState, BirthDetails types
    graph.py      — LangGraph graph definition
    nodes.py      — router, reasoning, tool, safety nodes
    llm.py        — OpenRouter client (single place to configure the model)
    tools/        — geocode, birth chart, transits, knowledge lookup
  api/
    main.py       — FastAPI server, SSE streaming endpoint
  requirements.txt

eval/
  golden_set.jsonl   — 29 test cases, versioned
  run_eval.py        — one-command eval runner
  judge.py           — LLM-as-judge rubric
  results/           — scorecard CSVs from each run
```

---

## Setup

You need Python 3.11+. No paid API keys — just a free OpenRouter account.

**Get your free OpenRouter key:** sign up at https://openrouter.ai. No credit card needed. The free models have generous rate limits for a project like this.

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

One note on `pyswisseph` — it needs the Swiss Ephemeris data files to compute accurate planetary positions. Download them from https://www.astro.com/swisseph/ and put them in `backend/ephe/`. The tools look there by default. Without these files it falls back to approximate positions, which is fine for development but not for the eval.

Start the server:

```bash
uvicorn api.main:app --reload
```

The API runs at `http://localhost:8000`. Hit `/health` to confirm it's up.

---

## Running the eval

```bash
python eval/run_eval.py
```

Make sure the server is running first. This runs all 29 golden set cases, prints a scorecard table, and saves a CSV to `eval/results/`. A score drop between runs is treated like a failing test.

---

## Graph diagram

```
                        ┌─────────────────────────────────────┐
                        │              AgentState              │
                        │  messages, birth_details, intent,    │
                        │  birth_chart, tool_calls_made,       │
                        │  step_count, session_id              │
                        └─────────────────────────────────────┘
                                         │
                                    [START]
                                         │
                                    ┌────▼────┐
                                    │ router  │  classifies intent
                                    └────┬────┘
                        ┌───────────────┼───────────────────┐
                        │               │                   │
                ┌───────▼──────┐  ┌─────▼──────┐   ┌───────▼──────┐
                │chart_request │  │daily_horosc│   │  off_topic   │
                └───────┬──────┘  └─────┬──────┘   └───────┬──────┘
                        └───────┬───────┘                   │
                           ┌────▼─────┐                     │
                           │reasoning │ ◄──────────┐        │
                           └────┬─────┘            │        │
                    ┌───────────┴──────────┐        │        │
               tool_calls?           no tools        │        │
                    │                    │           │        │
               ┌────▼─────┐        ┌────▼─────┐    │        │
               │  tools   │ ───────►  safety  │◄───┘────────┘
               └──────────┘        └────┬─────┘
                                        │
                                      [END]
```

---

## Known limitations

The skeleton is in place but the reasoning node still returns a placeholder response — real LLM call and tools come in the next commit. No conversation persistence yet either.

Check the git log to see what landed in each commit.

---

## Evaluation

See [EVALUATION.md](EVALUATION.md) for a write-up of what the eval revealed and what would be improved with more time.

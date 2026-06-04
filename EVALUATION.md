# Evaluation Notes

How the agent is evaluated, what the harness measures, and an honest read on where it stands.

---

## How to run

```bash
# server must be running
cd backend && uvicorn api.main:app --reload

# in another terminal
python eval/run_eval.py
```

Results print as a scorecard and save to `eval/results/run_YYYYMMDD_HHMMSS.csv`. Run it after every significant change — a drop in pass rate is treated like a failing test. `python eval/summarize.py` re-prints the stats for the latest CSV.

---

## What the golden set covers

30 cases across 7 categories, written before the tools were built.

| Category | Cases | What it tests |
|---|---|---|
| chart_request | C01–C09 | Valid charts, missing time, impossible dates, bad places, very old years, future dates |
| daily_horoscope | H01–H04 | Transit tool gets called; asks for details when none are given |
| freeform_question | F01–F05 | Career, relationships, Saturn return, vague "something's changing", a friend's chart |
| safety | S01–S04 | Medical, financial, legal, death — each must refuse without certainty |
| adversarial | A01–A03 | Prompt injection, jailbreak via roleplay, an attempt to skip the ephemeris |
| off_topic | O01–O02 | Weather, recipes — warm redirect |
| edge_case | E01–E03 | Empty message, single-word greeting, non-English (Hindi) input |

---

## Check types

**Deterministic** — asserted in code, no model needed: was the right tool called (`expected_tools`), is a banned phrase present (`must_not_contain`), is the correct sun sign in the text, did the agent return without crashing on bad input.

**Behavioral** — a keyword-signal check. The response is scanned for words that indicate the expected behavior. This is a proxy, not a guarantee — it can pass a response that hit the right keywords for the wrong reasons, so behavioral cases are the ones most worth reading by hand.

**LLM-as-judge** — used only where code can't grade it. Four dimensions (helpfulness, tone, groundedness, safety), graded one at a time at temperature 0, scored 1–5. An average ≥ 3.0 passes.

---

## Judge validation

The judge is itself a model, so it needs checking before its scores count as evidence. The golden set has 6 `llm_judge` cases, so all 6 were spot-checked by hand against the run below.

| ID | Question | Judge (H/T/G/S → avg) | My verdict | Agree? |
|---|---|---|---|---|
| F01 | Career reading | 5/5/5/5 → 5.0 | Pass — real Midheaven-led career reading | ✓ |
| F02 | Love & relationships | 5/5/5/5 → 5.0 | Pass — Venus + Ascendant, chart-specific | ✓ |
| F03 | Saturn return | 5/5/5/5 → 5.0 | Pass — explains the return against their chart | ✓ |
| F04 | "Something big is changing" | 5/5/5/5 → 5.0 | Pass — grounds it in the Virgo stellium + today's sky | ✓ |
| E02 | "hi" | 1/5/1/5 → 3.0 | Pass — correct warm greeting | ✓ (verdict); I'd score helpfulness higher |
| E03 | Hindi chart request | 1/5/5/5 → 4.0 | Pass — full reading in Hindi | ✓ (verdict); I'd score helpfulness higher |

**Verdict agreement: 6/6.** I agreed with every pass/fail call. On the two edge cases I'd grade more generously than the judge: it scores a greeting (E02) and a non-English reading (E03) as helpfulness=1, because neither leans on chart data the way a full reading does. That's defensible — a "hi" genuinely can't be grounded in a chart that doesn't exist yet — but it's stricter than my own read. The judge's tone=5 and safety=5 across the board match the agent's actual behavior.

One thing the validation caught: the judge was silently returning `None` for every dimension. Gemini Flash-Lite returns message content as a list of typed parts, and the parser called `.strip()` on that list, threw, and swallowed the error into `None`. Normalizing the content (and spacing the four calls so they don't trip the per-minute limit) is what made real scores appear. Worth stating plainly — an unvalidated judge had been reporting nothing, and the numbers would have looked fine on a quick glance.

---

## Scorecard (run 2026-06-04)

| Metric | Value |
|---|---|
| Pass rate | 30/30 (100%) |
| p50 latency | 8,071 ms |
| p95 latency | 11,025 ms |
| Mean latency | 7,131 ms |
| Judge dimensions (n=6) | helpfulness 3.67 · tone 5.0 · groundedness 4.33 · safety 5.0 |
| Cost/request | $0.00 (free-tier Gemini; see note below) |
| Judge verdict agreement | 6/6 |

**By category:**

| Category | Pass |
|---|---|
| chart_request | 9/9 |
| daily_horoscope | 4/4 |
| freeform_question | 5/5 |
| safety | 4/4 |
| adversarial | 3/3 |
| off_topic | 2/2 |
| edge_case | 3/3 |

A 100% pass on 30 single-turn cases means the agent is solid on this suite — not that it's flawless. The suite is small and single-turn; treat it as a regression contract, not proof of perfection. Two cases that failed in earlier runs (C02, a rate-limit cascade between tool calls; A01, the model's own safety layer firing a flat refusal) both passed cleanly here. C02-style failures are non-deterministic free-tier artifacts rather than logic bugs — on a slower day one can still 429 mid-chain.

---

## What the eval revealed

**The judge needed evaluating before the agent did.** The silent-`None` bug above is the clearest lesson of the whole exercise: the eval looked like it ran, but the part doing the grading was returning nothing. Spot-checking by hand is the only reason it surfaced.

**Latency is honest now, and the editor is the long pole.** Simple cases (greeting, off-topic, empty) return in ~2 s. Chart and freeform readings sit at 8–12 s because they chain a Python pre-compute, the reasoning pass, a knowledge lookup, and then the second editor pass. The editor adds one more model call to every long reading — that's a real cost, visible in the p95. Earlier runs reported p50 ~57 s; that was almost entirely free-tier rate-limit backoff, removed here by disabling Gemini's thinking budget and pre-computing the chart in Python so a chart request spends ~1 model round instead of 3–4.

**Behavioral checks are a keyword proxy.** They're cheap and catch gross regressions, but a determined wrong answer that uses the right vocabulary would slip through. The judged and deterministic cases carry the real weight.

**The token count is a proxy, not real usage.** The harness counts streamed SSE chunks per response (mean ~14), which is coarse — Gemini sends a few large chunks, not one-per-token. It is not an LLM token count, and the free tier doesn't bill, so cost shows as $0.00. Both columns are kept honest in the CSV rather than faked.

---

## What I'd fix with more time

- **Real token and cost accounting** — read `usage_metadata` off the Gemini responses instead of counting SSE chunks, so the cost column means something on a paid key.
- **Multi-turn cases** — every golden case is single-turn. The interesting failures (does it remember the chart across turns, does it re-ask for a birth time it already has) only show up in 3–5 turn conversations.
- **A second judge model for cross-check** — one judge on a small set is thin evidence. Running two different models and reporting where they disagree would tighten it; the pinned Flash models exhaust their daily free quota too fast to do this reliably today.
- **LLM router** — intent routing is keyword-based, which is fast but brittle (e.g. "what's my vibe this week?" can miss the horoscope intent). A short classification call would handle the edges.
- **Rate-limit headroom** — the one genuinely flaky case (C02) is a free-tier artifact. A paid key or a local model removes it entirely.

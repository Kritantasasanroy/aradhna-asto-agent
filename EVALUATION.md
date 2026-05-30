# Evaluation Notes

This document covers the eval approach, what the harness measures, and honest reflections on where the agent stands.

---

## How to run

```bash
# server must be running
cd backend && uvicorn api.main:app --reload

# in another terminal
python eval/run_eval.py
```

Results print as a scorecard table and save to `eval/results/run_YYYYMMDD_HHMMSS.csv`. Run it after every significant change — a drop in pass rate is treated like a failing test.

---

## What the golden set covers

29 cases across 7 categories, written before any tool was implemented.

| Category | Cases | What it tests |
|---|---|---|
| chart_request | C01–C09 | Valid charts, missing time, bad dates, bad places, old years, future dates |
| daily_horoscope | H01–H04 | Transit tool called, asks for details when none given |
| freeform_question | F01–F05 | Career, relationships, Saturn return, vague questions |
| safety | S01–S04 | Medical, financial, legal, death — must refuse each |
| adversarial | A01–A03 | Prompt injection, jailbreak via roleplay, trying to skip tool calls |
| off_topic | O01–O02 | Weather, recipes — warm redirect |
| edge_case | E01–E03 | Empty message, single word, non-English input |

---

## Check types

**Deterministic** — asserted in code, no LLM needed:
- Did the right tool get called? (checked against `expected_tools`)
- Does the response contain a banned phrase? (checked against `must_not_contain`)
- Does the response mention the correct sun sign?
- Did the agent return without crashing on bad input?

**Behavioral** — signal-based automated check:
- Does the response contain words that indicate the right behavior (asking for birth details, redirecting warmly, etc.)?
- These are a proxy, not a guarantee. Mark cases that fail for manual review.

**LLM-as-judge** — used only where code can't grade it:
- Graded on 4 dimensions: helpfulness, tone, groundedness, safety (1–5 each)
- One dimension at a time — more reliable than asking for all at once
- Temperature 0 for consistency
- Average ≥ 3.0 counts as a pass

---

## Judge validation

The assignment requires spot-checking at least 10 judge verdicts against your own judgment and reporting the agreement rate. Use the spot-check report printed at the end of `run_eval.py`, fill in your own scores, and record the agreement rate below.

**Agreement rate: ___/10** — fill this in after running the full eval.

---

## Scorecard (latest run)

*Fill in after running `python eval/run_eval.py` end-to-end.*

| Metric | Value |
|---|---|
| Pass rate | — |
| p50 latency | — |
| p95 latency | — |
| Avg tokens/request | — |
| Avg cost/request | — |
| Judge agreement rate | — |

---

## What the eval revealed

*Fill in after the first full run. Be honest — a low score reported truthfully scores higher than a perfect score that can't be reproduced.*

Things to address:
- Does the router misclassify anything? (freeform vs chart_request?)
- Do safety cases pass cleanly, or does the model sometimes slip through?
- What's the latency on chart requests vs simple freeform questions?
- Does the LLM judge agree with your intuition on tone?

---

## What would be fixed with more time

- **LLM router instead of keyword matching** — the current router uses keyword signals which miss edge cases. A small LLM classification call would handle ambiguous phrasing better.
- **Multi-turn eval cases** — the golden set has single-turn cases. A proper eval would include 3–5 turn conversations to test whether the agent remembers the chart across turns.
- **Cost tracking** — the scorecard logs token count but not dollar cost per request, because OpenRouter's free models don't report usage the same way. Wiring up proper cost tracking via the API response headers would complete the scorecard.
- **Judge calibration** — the agreement rate between judge and human would ideally be ≥ 80%. If it's lower, the rubric needs tightening or the judge model needs upgrading.

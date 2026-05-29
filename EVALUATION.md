# Evaluation Notes

This file grows as the project progresses. Each section covers what a given eval run revealed and what it would take to fix.

---

## Day 1 — Skeleton run

The eval harness exists and the golden set has 29 cases. The agent is a placeholder that echoes a static message, so all deterministic checks fail (no tools are called yet, no LLM reasoning happens). That's expected and honest.

What's real right now:
- The golden set covers the full range of inputs we care about — valid charts, bad data, safety cases, adversarial attempts, off-topic requests
- The eval runner can call the API and parse SSE events
- Deterministic checks (tool called, banned phrases absent, sun sign in response) are in code
- LLM-as-judge stub returns None until Day 7

Score as of Day 1: 0/29 pass — because the agent doesn't do anything yet. That's the baseline.

---

## What each eval category is testing

**chart_request (C01–C09)** — does the agent actually call the ephemeris library with real data? Does it handle missing time gracefully? Does it survive bad dates and bad place names without crashing?

**daily_horoscope (H01–H04)** — does the agent call the transits tool? Does it ask for birth details when it has none?

**freeform_question (F01–F05)** — is the response grounded in actual chart data, or is it generic? This is where the knowledge_lookup tool matters most.

**safety (S01–S04)** — the most important category. An agent that says "you will get cancer" or "buy stocks on Tuesday" is a liability. These cases check for specific banned phrases in code, not just vibes.

**adversarial (A01–A03)** — prompt injection, jailbreak via roleplay, and a user trying to skip tool calls. The agent should ignore all of these and stay in character.

**off_topic (O01–O02)** — weather, recipes. The agent should redirect warmly, not crash or pretend to answer.

**edge_case (E01–E03)** — empty input, single word, non-English. The agent must handle all of these without exploding.

---

## What I would fix with more time

This section will be filled in honestly after the Day 7 eval run, once the agent is actually doing something meaningful. For now, the placeholder.

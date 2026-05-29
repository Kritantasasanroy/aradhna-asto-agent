"""
Eval harness for AstroAgent.

Run the full golden set with:
    python eval/run_eval.py

By default it hits the local API at http://localhost:8000. Pass a different
base URL as the first argument if you need to:
    python eval/run_eval.py http://your-host:8000

Results are printed as a scorecard table and saved to eval/results/.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
API_BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TIMEOUT = 60  # seconds per case


def load_golden_set() -> list[dict]:
    cases = []
    with open(GOLDEN_SET) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def call_agent(case: dict, client: httpx.Client) -> dict:
    """Calls /chat and returns the full response plus timing info."""
    payload = {
        "message": case["input"].get("message", ""),
        "birth_details": case["input"].get("birth_details"),
        "session_id": f"eval-{case['id']}",
    }

    start = time.perf_counter()
    tools_seen: list[str] = []
    response_text = ""
    token_count = 0
    error: Optional[str] = None

    try:
        with client.stream("POST", f"{API_BASE}/chat", json=payload, timeout=TIMEOUT) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[len("data:"):].strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if event.get("type") == "token":
                    response_text += event.get("content", "")
                    token_count += 1
                elif event.get("type") == "tool_start":
                    tools_seen.append(event.get("tool", ""))
                elif event.get("type") == "done":
                    break

    except httpx.ConnectError:
        error = "API not running — start the server first: uvicorn api.main:app --reload"
    except httpx.HTTPStatusError as e:
        error = f"HTTP {e.response.status_code}"
    except Exception as e:
        error = str(e)

    latency_ms = round((time.perf_counter() - start) * 1000)

    return {
        "response_text": response_text,
        "tools_seen": tools_seen,
        "latency_ms": latency_ms,
        "token_count": token_count,
        "error": error,
    }


def check_deterministic(case: dict, run: dict) -> tuple[bool, str]:
    """
    Asserts things we can check in code without an LLM.
    Returns (passed, reason).
    """
    if run["error"]:
        return False, f"error: {run['error']}"

    text = run["response_text"].lower()

    # check must_not_contain strings
    for banned in case.get("must_not_contain", []):
        if banned.lower() in text:
            return False, f"response contains banned phrase: '{banned}'"

    # check expected tools were called
    for expected_tool in case.get("expected_tools", []):
        if expected_tool not in run["tools_seen"]:
            return False, f"expected tool '{expected_tool}' was not called"

    # check expected sun sign appears in response
    if expected_sign := case.get("expected_sun_sign"):
        if expected_sign.lower() not in text:
            return False, f"expected sun sign '{expected_sign}' not in response"

    return True, "ok"


def llm_judge(case: dict, run: dict) -> Optional[int]:
    """
    Scores the response 1–5 on helpfulness and tone.
    Only called for cases with check_type == 'llm_judge'.
    Returns None if the judge can't run (no API key etc).
    """
    # TODO: wire up the LLM judge on Day 7
    # For now, return None so the scorecard shows — rather than a made-up score
    return None


def run_case(case: dict, client: httpx.Client) -> dict:
    run = call_agent(case, client)
    check_type = case.get("check_type", "behavioral")

    passed = False
    reason = "not checked"
    judge_score = None

    if check_type == "deterministic":
        passed, reason = check_deterministic(case, run)
    elif check_type == "behavioral":
        # behavioral checks are manual for now — mark as needs_review
        passed = run["error"] is None
        reason = "needs_manual_review" if not run["error"] else f"error: {run['error']}"
    elif check_type == "llm_judge":
        judge_score = llm_judge(case, run)
        passed = run["error"] is None
        reason = "llm_judge_pending" if judge_score is None else f"judge: {judge_score}/5"

    return {
        "id": case["id"],
        "category": case["category"],
        "description": case["description"],
        "check_type": check_type,
        "tools_called": ", ".join(run["tools_seen"]) or "—",
        "latency_ms": run["latency_ms"],
        "tokens": run["token_count"] or "—",
        "cost_usd": None,   # wired up once we track token types
        "judge_score": judge_score,
        "pass": passed,
        "reason": reason,
        "error": run.get("error"),
    }


def print_scorecard(results: list[dict]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["pass"])

    header = f"{'ID':<6} {'CATEGORY':<20} {'CHECK':<14} {'TOOLS':<30} {'LATENCY':>10} {'TOKENS':>7} {'JUDGE':>6} {'PASS':>5}"
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))

    for r in results:
        judge = f"{r['judge_score']}/5" if r["judge_score"] is not None else "—"
        latency = f"{r['latency_ms']}ms"
        tokens = str(r["tokens"])
        status = "✓" if r["pass"] else "✗"
        tools = (r["tools_called"] or "—")[:28]

        print(
            f"{r['id']:<6} {r['category']:<20} {r['check_type']:<14} "
            f"{tools:<30} {latency:>10} {tokens:>7} {judge:>6} {status:>5}"
        )
        if r.get("error"):
            print(f"       ^ {r['error']}")

    print("=" * len(header))
    p50 = sorted(r["latency_ms"] for r in results)[len(results) // 2]
    p95_idx = int(len(results) * 0.95)
    p95 = sorted(r["latency_ms"] for r in results)[p95_idx]
    print(f"PASS: {passed}/{total}  |  p50 latency: {p50}ms  |  p95 latency: {p95}ms")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def save_results(results: list[dict]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"run_{timestamp}.csv"

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to {path}")


def main() -> None:
    print(f"AstroAgent Eval  —  API: {API_BASE}")
    print("Loading golden set...")

    cases = load_golden_set()
    print(f"Found {len(cases)} test cases.\n")

    results = []
    with httpx.Client() as client:
        for case in cases:
            print(f"  {case['id']} ({case['category']})...", end="", flush=True)
            result = run_case(case, client)
            results.append(result)
            status = "ok" if result["pass"] else f"FAIL — {result['reason']}"
            print(f" {status}")

    print_scorecard(results)
    save_results(results)


if __name__ == "__main__":
    main()

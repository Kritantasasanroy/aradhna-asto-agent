"""
Summarize the latest eval CSV into the numbers EVALUATION.md needs.

    python eval/summarize.py            # newest run_*.csv
    python eval/summarize.py <file.csv> # a specific run

Prints overall pass rate, p50/p95 latency, avg tokens, per-category breakdown,
judge averages, and the list of failures with reasons — everything required to
fill the scorecard honestly.
"""
from __future__ import annotations

import csv
import glob
import statistics
import sys
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(int(len(s) * p), len(s) - 1)
    return s[idx]


def main() -> None:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        runs = sorted(glob.glob(str(RESULTS_DIR / "run_*.csv")))
        if not runs:
            print("No run_*.csv found. Run eval/run_eval.py first.")
            return
        path = Path(runs[-1])

    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    total = len(rows)
    passed = sum(1 for r in rows if r["pass"] == "True")

    lat = [int(r["latency_ms"]) for r in rows if r["latency_ms"].isdigit()]
    toks = [int(r["tokens"]) for r in rows if r["tokens"].isdigit()]

    print(f"\nFILE: {path.name}")
    print(f"PASS RATE : {passed}/{total} = {round(100*passed/total)}%")
    print(f"LATENCY   : p50 {round(_pct(lat,0.5))}ms  p95 {round(_pct(lat,0.95))}ms  "
          f"mean {round(statistics.mean(lat)) if lat else 0}ms")
    print(f"TOKENS    : mean {round(statistics.mean(toks)) if toks else 0}  "
          f"(streamed token events per response)")

    # per category
    print("\nBY CATEGORY")
    cats: dict[str, list[dict]] = {}
    for r in rows:
        cats.setdefault(r["category"], []).append(r)
    for cat, rs in cats.items():
        p = sum(1 for r in rs if r["pass"] == "True")
        print(f"  {cat:<18} {p}/{len(rs)}")

    # judge dimensions
    print("\nJUDGE AVERAGES (llm_judge cases)")
    for dim in ("helpfulness", "tone", "groundedness", "safety"):
        vals = [int(r[f"judge_{dim}"]) for r in rows
                if r.get(f"judge_{dim}", "").strip().isdigit()]
        if vals:
            print(f"  {dim:<13} {round(statistics.mean(vals),2)}  (n={len(vals)})")
        else:
            print(f"  {dim:<13} —  (no scores)")

    # failures
    fails = [r for r in rows if r["pass"] != "True"]
    print(f"\nFAILURES ({len(fails)})")
    for r in fails:
        reason = r["reason"].encode("ascii", "replace").decode()
        print(f"  {r['id']:<5} [{r['check_type']:<13}] {reason[:80]}")


if __name__ == "__main__":
    main()

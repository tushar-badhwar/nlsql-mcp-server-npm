"""Gold-on-gold sanity sweep across the full BIRD dev set.

Predicted SQL = gold SQL for every question. Expected EX = 1.00 across all
1,534 questions; any cell where it isn't is either a scorer bug or a quirky
BIRD question worth flagging.

Output: analytics_bird/runs/eval/gold_sanity.jsonl (one record per question).
A summary is also written to gold_sanity.summary.json.

Known quirky BIRD questions (gold SQL exceeds the upstream 30s default):
  * qid=518 (card_games, moderate)        — gold runs ~32s
  * qid=701 (codebase_community, challenging) — gold runs ~165s
Both produce EX=1 if you raise timeout_s to ~300s. The 30s default matches
upstream `meta_time_out`, so these will also miss in BIRD's official scorer.
Not scorer bugs.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from bird.dataset import load_questions
from bird.score import DIFFICULTIES, aggregate, score_one

# Per-query wall-clock cap. BIRD's official scorer uses 30s; we match.
TIMEOUT_S = 30.0


def main() -> int:
    out_dir = Path(__file__).parent / "runs" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "gold_sanity.jsonl"
    summary_path = out_dir / "gold_sanity.summary.json"

    print(f"Loading BIRD dev questions ...")
    questions = load_questions()
    print(f"  {len(questions)} questions, "
          f"{len(set(q.db_id for q in questions))} databases")

    results = []
    misses = []  # question_ids where EX != 1
    started = time.perf_counter()

    with jsonl_path.open("w") as fh:
        for i, q in enumerate(questions, 1):
            r = score_one(
                question_id=q.question_id,
                db_path=q.db_path,
                predicted_sql=q.gold_sql,
                gold_sql=q.gold_sql,
                timeout_s=TIMEOUT_S,
                difficulty=q.difficulty,
            )
            results.append(r)
            rec = asdict(r)
            rec["db_id"] = q.db_id
            fh.write(json.dumps(rec) + "\n")

            if r.ex != 1:
                misses.append({
                    "qid": q.question_id, "db": q.db_id,
                    "difficulty": q.difficulty,
                    "error": r.error, "timeout": r.timeout,
                    "rows": f"{r.predicted_rows}/{r.gold_rows}",
                    "gold_sql": q.gold_sql,
                })

            if i % 100 == 0 or i == len(questions):
                elapsed = time.perf_counter() - started
                ex_so_far = sum(r.ex for r in results) / len(results)
                print(f"  [{i}/{len(questions)}] EX={ex_so_far:.4f} "
                      f"misses={len(misses)} elapsed={elapsed:.1f}s")

    agg = aggregate(results)
    summary = {
        "n": agg.n,
        "ex": agg.ex,
        "ex_sum": agg.ex_sum,
        "failures": agg.failures,
        "timeouts": agg.timeouts,
        "by_difficulty": {
            d: {"n": agg.by_difficulty.get(d, (0, 0))[0],
                "ex_sum": agg.by_difficulty.get(d, (0, 0))[1],
                "ex": agg.ex_for(d)}
            for d in DIFFICULTIES
        },
        "miss_count": len(misses),
        "miss_by_db": Counter(m["db"] for m in misses).most_common(),
        "miss_by_difficulty": Counter(m["difficulty"] for m in misses).most_common(),
        "miss_kinds": Counter(
            "timeout" if m["timeout"]
            else ("error" if m["error"] else "row-mismatch")
            for m in misses
        ).most_common(),
        "misses": misses,
    }
    with summary_path.open("w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"\n=== Aggregate ===")
    print(f"  n={agg.n}  EX={agg.ex:.4f}  failures={agg.failures}  timeouts={agg.timeouts}")
    for d in DIFFICULTIES:
        ex_d = agg.ex_for(d)
        n_d = agg.by_difficulty.get(d, (0, 0))[0]
        print(f"  {d:12s} n={n_d:<5d} EX={ex_d:.4f}" if ex_d is not None
              else f"  {d:12s} n=0     EX=n/a")
    print(f"  jsonl   → {jsonl_path}")
    print(f"  summary → {summary_path}")

    return 0 if agg.ex == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())

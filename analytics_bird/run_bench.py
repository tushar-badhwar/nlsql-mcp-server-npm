"""BIRD benchmark runner.

Usage:
    python run_bench.py --n 50 --adapter claude --model claude-sonnet-4-6

Picks the first `n` BIRD dev questions, dispatches each through the selected
adapter, scores predictions with `bird.score`, and prints an aggregate EX.
Per-question JSONL traces land under `runs/<adapter>-<timestamp>/qNNN.jsonl`.
A `summary.jsonl` next to them records one line per question with predicted
SQL, EX, tokens, cost, and elapsed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from bird.dataset import load_questions
from bird.score import aggregate, score_one


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=50, help="number of questions (BIRD-mini=50)")
    p.add_argument("--adapter", choices=["claude"], default="claude",
                   help="which SDK adapter to run (only claude in week 2)")
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--max-turns", type=int, default=15)
    p.add_argument(
        "--out-dir", type=Path, default=None,
        help="trace dir (default: runs/<adapter>-<timestamp>/)",
    )
    p.add_argument(
        "--start", type=int, default=0,
        help="start offset into the question list (for resuming)",
    )
    return p.parse_args()


async def _run_claude(questions, model: str, max_turns: int, out_dir: Path):
    from adapters.claude import run_task

    summary_path = out_dir / "summary.jsonl"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_fh = summary_path.open("w")

    scores = []
    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] q{q.question_id} db={q.db_id} "
              f"[{q.difficulty}] {q.question[:70]}")
        trace_path = out_dir / f"q{q.question_id:04d}.jsonl"
        t0 = time.perf_counter()
        try:
            result = await run_task(q, model=model, trace_path=trace_path,
                                    max_turns=max_turns)
        except Exception as e:
            print(f"  ! adapter raised: {type(e).__name__}: {e}")
            summary_fh.write(json.dumps({
                "qid": q.question_id, "db": q.db_id,
                "predicted_sql": None, "ex": 0,
                "error": f"adapter raised: {type(e).__name__}: {e}",
                "elapsed_s": round(time.perf_counter() - t0, 2),
            }) + "\n")
            summary_fh.flush()
            continue

        elapsed = time.perf_counter() - t0

        if result.predicted_sql is None:
            print(f"  ✗ no SQL extracted in {result.num_turns} turns "
                  f"(stop={result.stop_reason})  {elapsed:.1f}s")
            summary_fh.write(json.dumps({
                "qid": q.question_id, "db": q.db_id,
                "predicted_sql": None, "ex": 0, "num_turns": result.num_turns,
                "error": result.error,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.total_cost_usd,
                "elapsed_s": round(elapsed, 2),
                "trace": str(result.trace_path),
            }) + "\n")
            summary_fh.flush()
            continue

        s = score_one(
            question_id=q.question_id,
            db_path=q.db_path,
            predicted_sql=result.predicted_sql,
            gold_sql=q.gold_sql,
        )
        scores.append(s)
        tag = "✓" if s.ex else "✗"
        err = f"  err={s.error}" if s.error else ""
        print(f"  {tag} EX={s.ex}  rows={s.predicted_rows}/{s.gold_rows}  "
              f"turns={result.num_turns}  ${result.total_cost_usd or 0:.4f}  "
              f"{elapsed:.1f}s{err}")

        summary_fh.write(json.dumps({
            "qid": q.question_id, "db": q.db_id,
            "predicted_sql": result.predicted_sql,
            "gold_sql": q.gold_sql,
            "ex": s.ex,
            "predicted_rows": s.predicted_rows,
            "gold_rows": s.gold_rows,
            "score_error": s.error,
            "num_turns": result.num_turns,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": result.total_cost_usd,
            "elapsed_s": round(elapsed, 2),
            "trace": str(result.trace_path),
        }) + "\n")
        summary_fh.flush()

    summary_fh.close()
    return scores


async def amain() -> int:
    args = parse_args()

    try:
        questions = load_questions()
    except FileNotFoundError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    pool = questions[args.start : args.start + args.n]
    if not pool:
        print(f"✗ empty slice: start={args.start} n={args.n} "
              f"(have {len(questions)} questions)", file=sys.stderr)
        return 2

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = args.out_dir or Path(__file__).parent / "runs" / f"{args.adapter}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"adapter={args.adapter}  model={args.model}  n={len(pool)}  "
          f"out={out_dir}\n")

    started = time.perf_counter()

    if args.adapter == "claude":
        scores = await _run_claude(pool, args.model, args.max_turns, out_dir)
    else:  # pragma: no cover — argparse choices limits this
        print(f"unknown adapter: {args.adapter}", file=sys.stderr)
        return 2

    wall = time.perf_counter() - started
    agg = aggregate(scores)

    print("\n=== Aggregate ===")
    print(f"  n_scored={agg.n}  EX={agg.ex:.3f}  "
          f"correct={agg.ex_sum}  failures={agg.failures}")
    print(f"  wall_clock={wall:.1f}s  out={out_dir}")
    (out_dir / "aggregate.json").write_text(json.dumps({
        "adapter": args.adapter, "model": args.model,
        "n_requested": len(pool), "n_scored": agg.n,
        "ex": agg.ex, "ex_sum": agg.ex_sum, "failures": agg.failures,
        "wall_clock_s": round(wall, 2),
    }, indent=2))
    return 0


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())

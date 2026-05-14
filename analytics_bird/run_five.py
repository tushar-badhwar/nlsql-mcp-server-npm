"""Week-1 success-signal script: run 5 BIRD questions end-to-end.

No model. Uses the gold SQL as the "prediction" — this proves the dataset
loader, the tool primitives, the scorer, and the trace writer all compose
correctly against real BIRD data. Once we have a model adapter (week 2),
the only change is swapping gold_sql for model_output.
"""

from __future__ import annotations

import sys
from pathlib import Path

from bird.dataset import filter_questions, load_questions
from bird.score import aggregate, score_one
from tools.sql import connect, describe_schema, disconnect, execute_sql, list_tables
from tracing.jsonl import open_trace


def main() -> int:
    try:
        questions = load_questions()
    except FileNotFoundError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    # Take 5 questions from the first available DB for tighter signal
    if not questions:
        print("✗ No questions loaded.", file=sys.stderr)
        return 2
    first_db = questions[0].db_id
    sample = filter_questions(questions, db_id=first_db, limit=5)
    if len(sample) < 5:
        sample = questions[:5]

    print(f"Running {len(sample)} questions from db={sample[0].db_id}\n")

    results = []
    trace_path = Path(__file__).parent / "runs" / "week1" / "five.jsonl"

    with open_trace(trace_path, meta={"task": "week1-five-questions"}) as trace:
        for q in sample:
            print(f"q{q.question_id} [{q.difficulty}] {q.question[:80]}")
            trace.tool_call("question", {
                "qid": q.question_id, "db": q.db_id,
                "question": q.question, "difficulty": q.difficulty,
            })

            # Connect to the real BIRD DB
            r = connect(q.dsn)
            cid = r["connection_id"]
            trace.tool_call("connect", {"dsn": q.dsn})
            trace.tool_result("connect", r)

            # Light schema introspection (exercises tools against real schemas)
            tables = list_tables(cid)["tables"]
            trace.tool_call("list_tables", {})
            trace.tool_result("list_tables", {"tables": tables})

            # Execute the gold SQL via our tools (read-only enforced)
            exec_r = execute_sql(cid, q.gold_sql, max_rows=1000)
            trace.tool_call("execute_sql", {"sql": q.gold_sql})
            trace.tool_result("execute_sql", exec_r)

            # Score: predicted = gold → should be EX=1 by definition
            s = score_one(
                question_id=q.question_id,
                db_path=q.db_path,
                predicted_sql=q.gold_sql,
                gold_sql=q.gold_sql,
            )
            trace.tool_result("score", s.__dict__)
            results.append(s)

            disconnect(cid)

            tag = "✓" if s.ex else "✗"
            err = f"  err={s.error}" if s.error else ""
            print(f"  {tag} EX={s.ex}  rows={s.predicted_rows}/{s.gold_rows}  "
                  f"gold_ms={s.gold_ms:.1f}{err}\n")

        agg = aggregate(results)
        trace.final(
            predicted_sql=None,
            success=agg.failures == 0,
            error=None if agg.failures == 0 else f"{agg.failures} failure(s)",
        )

    print(f"\n=== Aggregate ===")
    print(f"  n={agg.n}  EX={agg.ex:.2f}  failures={agg.failures}")
    print(f"  trace → {trace_path}")
    return 0 if agg.failures == 0 and agg.ex == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())

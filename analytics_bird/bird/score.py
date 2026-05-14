"""BIRD execution-accuracy scorer.

Per BIRD's official spec: a predicted SQL gets EX=1 iff its result set equals
the gold SQL's result set on the same database. Set comparison by default
(BIRD ignores row order unless the query has ORDER BY — we approximate by
comparing as sorted tuples).

VES (Valid Efficiency Score) is stubbed; implement properly only when we have
real model predictions to measure against.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScoreResult:
    question_id: int
    ex: int                    # 0 or 1
    predicted_rows: int        # row count of predicted result
    gold_rows: int             # row count of gold result
    predicted_ms: float | None
    gold_ms: float
    error: str | None = None


def _run(db_path: Path, sql: str, timeout_s: float = 30.0) -> tuple[list[tuple], float]:
    """Execute SQL on the BIRD SQLite DB, return (rows, elapsed_ms)."""
    conn = sqlite3.connect(str(db_path), timeout=timeout_s)
    try:
        start = time.perf_counter()
        rows = conn.execute(sql).fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return rows, elapsed_ms
    finally:
        conn.close()


def _normalize(rows: list[tuple]) -> list[tuple]:
    """Order-insensitive comparison key. Sort rows; do not sort within a row."""
    try:
        return sorted(rows)
    except TypeError:
        # Mixed types — fall back to stringified comparison
        return sorted(rows, key=lambda r: tuple(str(c) for c in r))


def score_one(
    question_id: int,
    db_path: Path,
    predicted_sql: str,
    gold_sql: str,
    timeout_s: float = 30.0,
) -> ScoreResult:
    try:
        gold_rows, gold_ms = _run(db_path, gold_sql, timeout_s)
    except Exception as e:
        return ScoreResult(
            question_id=question_id, ex=0, predicted_rows=0, gold_rows=0,
            predicted_ms=None, gold_ms=0.0,
            error=f"gold SQL failed: {e}",
        )

    try:
        pred_rows, pred_ms = _run(db_path, predicted_sql, timeout_s)
    except Exception as e:
        return ScoreResult(
            question_id=question_id, ex=0, predicted_rows=0, gold_rows=len(gold_rows),
            predicted_ms=None, gold_ms=gold_ms,
            error=f"predicted SQL failed: {e}",
        )

    ex = int(_normalize(pred_rows) == _normalize(gold_rows))
    return ScoreResult(
        question_id=question_id,
        ex=ex,
        predicted_rows=len(pred_rows),
        gold_rows=len(gold_rows),
        predicted_ms=pred_ms,
        gold_ms=gold_ms,
    )


@dataclass
class Aggregate:
    n: int
    ex_sum: int
    failures: int

    @property
    def ex(self) -> float:
        return self.ex_sum / self.n if self.n else 0.0


def aggregate(results: list[ScoreResult]) -> Aggregate:
    return Aggregate(
        n=len(results),
        ex_sum=sum(r.ex for r in results),
        failures=sum(1 for r in results if r.error is not None),
    )

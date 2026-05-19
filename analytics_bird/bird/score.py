"""BIRD execution-accuracy scorer.

Hardened against BIRD's official evaluator:
  https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/bird/llm/src
  (evaluation.py for EX, evaluation_ves.py for VES)

Upstream-aligned semantics (deliberate match):
  * EX uses set comparison: `set(pred_rows) == set(gold_rows)`. This makes
    the metric multiset-blind and order-blind — duplicates collapse, ORDER BY
    is ignored. This is how BIRD scores its leaderboard, so we match it even
    though it under-penalises queries where order or row multiplicity matter.
  * Timeout is wall-clock and kills the running query. Upstream uses
    `func_timeout`; we use the stdlib equivalent: a threading.Timer that calls
    `sqlite3.Connection.interrupt()` to abort the in-flight query. The
    original scorer's `sqlite3.connect(timeout=...)` was wrong — that argument
    only bounds *busy-lock waits*, not query runtime.
  * Errors and timeouts both produce ex=0, no exception escapes scoring.
  * Mixed/NULL types: no stringification fallback — Python tuples of
    hashable atoms (incl. None) compare cleanly inside sets. The previous
    `sorted()` path could TypeError on int-vs-None columns.

Deliberate divergences from upstream:
  * We capture per-query gold/pred timings on the EX path for downstream
    analysis (upstream throws them away). VES re-times separately, as
    upstream does.
  * We report difficulty alongside each ScoreResult so `Aggregate` can split
    EX by simple/moderate/challenging without a second pass over dev.json.
  * Upstream parallelises via multiprocessing; we don't here (the caller
    owns concurrency).
"""

from __future__ import annotations

import math
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev


# ---------- low-level execution -----------------------------------------------

class QueryTimeout(Exception):
    """Wall-clock timeout fired while a query was running."""


def _run(db_path: Path, sql: str, timeout_s: float) -> tuple[list[tuple], float]:
    """Execute SQL on a fresh SQLite connection, return (rows, elapsed_ms).

    Enforces a wall-clock timeout by arming a threading.Timer that calls
    `Connection.interrupt()` if the query is still running when it fires.
    On interrupt, SQLite raises OperationalError('interrupted'); we re-raise
    as QueryTimeout so callers can distinguish timeout from other SQL errors.
    """
    conn = sqlite3.connect(str(db_path))
    timed_out = {"flag": False}

    def _interrupt():
        timed_out["flag"] = True
        try:
            conn.interrupt()
        except Exception:
            pass

    timer = threading.Timer(timeout_s, _interrupt)
    timer.daemon = True
    timer.start()
    try:
        start = time.perf_counter()
        rows = conn.execute(sql).fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return rows, elapsed_ms
    except sqlite3.OperationalError as e:
        if timed_out["flag"] or "interrupt" in str(e).lower():
            raise QueryTimeout(f"query exceeded {timeout_s}s") from e
        raise
    finally:
        timer.cancel()
        conn.close()


# ---------- EX (Execution Accuracy) -------------------------------------------

@dataclass
class ScoreResult:
    question_id: int
    ex: int                    # 0 or 1
    predicted_rows: int        # row count of predicted result (0 on failure)
    gold_rows: int             # row count of gold result (0 if gold also failed)
    predicted_ms: float | None
    gold_ms: float
    error: str | None = None
    difficulty: str | None = None   # 'simple' | 'moderate' | 'challenging' | None
    timeout: bool = False


def _compare(pred_rows: list[tuple], gold_rows: list[tuple]) -> bool:
    """Order- and multiplicity-blind comparison, per BIRD upstream."""
    return set(pred_rows) == set(gold_rows)


def score_one(
    question_id: int,
    db_path: Path,
    predicted_sql: str,
    gold_sql: str,
    timeout_s: float = 30.0,
    difficulty: str | None = None,
) -> ScoreResult:
    try:
        gold_rows, gold_ms = _run(db_path, gold_sql, timeout_s)
    except QueryTimeout as e:
        return ScoreResult(
            question_id=question_id, ex=0, predicted_rows=0, gold_rows=0,
            predicted_ms=None, gold_ms=0.0,
            error=f"gold SQL timed out: {e}", difficulty=difficulty, timeout=True,
        )
    except Exception as e:
        return ScoreResult(
            question_id=question_id, ex=0, predicted_rows=0, gold_rows=0,
            predicted_ms=None, gold_ms=0.0,
            error=f"gold SQL failed: {e}", difficulty=difficulty,
        )

    try:
        pred_rows, pred_ms = _run(db_path, predicted_sql, timeout_s)
    except QueryTimeout as e:
        return ScoreResult(
            question_id=question_id, ex=0, predicted_rows=0, gold_rows=len(gold_rows),
            predicted_ms=None, gold_ms=gold_ms,
            error=f"predicted SQL timed out: {e}",
            difficulty=difficulty, timeout=True,
        )
    except Exception as e:
        return ScoreResult(
            question_id=question_id, ex=0, predicted_rows=0, gold_rows=len(gold_rows),
            predicted_ms=None, gold_ms=gold_ms,
            error=f"predicted SQL failed: {e}", difficulty=difficulty,
        )

    return ScoreResult(
        question_id=question_id,
        ex=int(_compare(pred_rows, gold_rows)),
        predicted_rows=len(pred_rows),
        gold_rows=len(gold_rows),
        predicted_ms=pred_ms,
        gold_ms=gold_ms,
        difficulty=difficulty,
    )


# ---------- VES (Valid Efficiency Score) --------------------------------------

@dataclass
class VESResult:
    question_id: int
    correct: int               # 0 or 1 — same set comparison as EX
    time_ratio: float          # mean of cleaned (gold_t / pred_t) ratios; 0 if incorrect
    iterations: int            # iterations that survived ±3σ outlier rejection
    error: str | None = None
    difficulty: str | None = None
    timeout: bool = False

    @property
    def score(self) -> float:
        """Per-query VES contribution: sqrt(time_ratio) * 100, 0 if incorrect."""
        return math.sqrt(self.time_ratio) * 100 if self.time_ratio > 0 else 0.0


def _clean_abnormal(values: list[float]) -> list[float]:
    """Drop samples outside ±3σ of the mean. Matches upstream clean_abnormal."""
    if len(values) < 2:
        return list(values)
    m = mean(values)
    s = stdev(values)
    return [x for x in values if (m - 3 * s) < x < (m + 3 * s)]


def ves_one(
    question_id: int,
    db_path: Path,
    predicted_sql: str,
    gold_sql: str,
    iterate_num: int = 100,
    timeout_s: float = 30.0,
    difficulty: str | None = None,
) -> VESResult:
    """Compute VES contribution for one question.

    Upstream flow (evaluation_ves.iterated_execute_sql):
      1. Run both SQLs once; set-compare results. If unequal → time_ratio = 0.
      2. Otherwise, re-run each `iterate_num` times, collecting
         gold_time/pred_time on each iteration.
      3. Drop ratios outside ±3σ.
      4. Mean the survivors → time_ratio.
    """
    try:
        gold_rows, _ = _run(db_path, gold_sql, timeout_s)
    except QueryTimeout as e:
        return VESResult(question_id=question_id, correct=0, time_ratio=0.0,
                         iterations=0, error=f"gold SQL timed out: {e}",
                         difficulty=difficulty, timeout=True)
    except Exception as e:
        return VESResult(question_id=question_id, correct=0, time_ratio=0.0,
                         iterations=0, error=f"gold SQL failed: {e}",
                         difficulty=difficulty)

    try:
        pred_rows, _ = _run(db_path, predicted_sql, timeout_s)
    except QueryTimeout as e:
        return VESResult(question_id=question_id, correct=0, time_ratio=0.0,
                         iterations=0, error=f"predicted SQL timed out: {e}",
                         difficulty=difficulty, timeout=True)
    except Exception as e:
        return VESResult(question_id=question_id, correct=0, time_ratio=0.0,
                         iterations=0, error=f"predicted SQL failed: {e}",
                         difficulty=difficulty)

    if not _compare(pred_rows, gold_rows):
        return VESResult(question_id=question_id, correct=0, time_ratio=0.0,
                         iterations=0, difficulty=difficulty)

    ratios: list[float] = []
    try:
        for _ in range(iterate_num):
            _, pred_ms = _run(db_path, predicted_sql, timeout_s)
            _, gold_ms = _run(db_path, gold_sql, timeout_s)
            if pred_ms <= 0:
                continue
            ratios.append(gold_ms / pred_ms)
    except QueryTimeout as e:
        return VESResult(question_id=question_id, correct=1, time_ratio=0.0,
                         iterations=len(ratios),
                         error=f"timing iteration timed out: {e}",
                         difficulty=difficulty, timeout=True)
    except Exception as e:
        return VESResult(question_id=question_id, correct=1, time_ratio=0.0,
                         iterations=len(ratios),
                         error=f"timing iteration failed: {e}",
                         difficulty=difficulty)

    cleaned = _clean_abnormal(ratios)
    if not cleaned:
        return VESResult(question_id=question_id, correct=1, time_ratio=0.0,
                         iterations=0, difficulty=difficulty)
    return VESResult(
        question_id=question_id,
        correct=1,
        time_ratio=mean(cleaned),
        iterations=len(cleaned),
        difficulty=difficulty,
    )


# ---------- aggregation ------------------------------------------------------

DIFFICULTIES = ("simple", "moderate", "challenging")


@dataclass
class Aggregate:
    n: int
    ex_sum: int
    failures: int
    timeouts: int = 0
    by_difficulty: dict[str, tuple[int, int]] = field(default_factory=dict)
    # by_difficulty[difficulty] = (n, ex_sum)

    @property
    def ex(self) -> float:
        return self.ex_sum / self.n if self.n else 0.0

    def ex_for(self, difficulty: str) -> float | None:
        bucket = self.by_difficulty.get(difficulty)
        if not bucket or bucket[0] == 0:
            return None
        return bucket[1] / bucket[0]


def aggregate(results: list[ScoreResult]) -> Aggregate:
    by_diff: dict[str, list[int]] = {}
    for r in results:
        if r.difficulty is None:
            continue
        by_diff.setdefault(r.difficulty, [0, 0])
        by_diff[r.difficulty][0] += 1
        by_diff[r.difficulty][1] += r.ex

    return Aggregate(
        n=len(results),
        ex_sum=sum(r.ex for r in results),
        failures=sum(1 for r in results if r.error is not None),
        timeouts=sum(1 for r in results if r.timeout),
        by_difficulty={k: (n, ex) for k, (n, ex) in by_diff.items()},
    )


@dataclass
class VESAggregate:
    n: int
    score: float                                    # mean of per-query VES scores
    correct: int
    by_difficulty: dict[str, tuple[int, float]] = field(default_factory=dict)
    # by_difficulty[difficulty] = (n, ves_score)

    def score_for(self, difficulty: str) -> float | None:
        bucket = self.by_difficulty.get(difficulty)
        if not bucket or bucket[0] == 0:
            return None
        return bucket[1]


def aggregate_ves(results: list[VESResult]) -> VESAggregate:
    """Matches upstream compute_ves: mean(sqrt(time_ratio)*100) over ALL queries."""
    n = len(results)
    overall = sum(r.score for r in results) / n if n else 0.0

    by_diff: dict[str, list[float]] = {}
    for r in results:
        if r.difficulty is None:
            continue
        by_diff.setdefault(r.difficulty, []).append(r.score)

    return VESAggregate(
        n=n,
        score=overall,
        correct=sum(r.correct for r in results),
        by_difficulty={
            k: (len(scores), sum(scores) / len(scores) if scores else 0.0)
            for k, scores in by_diff.items()
        },
    )

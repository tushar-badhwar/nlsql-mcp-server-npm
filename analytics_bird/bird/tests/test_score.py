"""Edge-case tests for bird/score.py.

What these pin down:
  * BIRD-style set comparison (multiset-blind, order-blind).
  * NULL/None rows survive comparison.
  * Mixed-type columns don't trigger TypeError fallbacks.
  * ORDER BY queries score equal regardless of direction — by design,
    matching BIRD's upstream evaluator.
  * Predicted SQL that errors or times out → ex=0 with a populated error.
  * Aggregate splits EX by difficulty.
  * VES: time_ratio=0 when wrong, >0 when correct; aggregate uses sqrt*100.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from bird.score import (
    Aggregate,
    QueryTimeout,
    ScoreResult,
    VESResult,
    _clean_abnormal,
    _compare,
    _run,
    aggregate,
    aggregate_ves,
    score_one,
    ves_one,
)


# ---------- fixtures ---------------------------------------------------------

@pytest.fixture
def db(tmp_path: Path) -> Path:
    """A small SQLite DB with deliberately ugly rows: NULLs, mixed types, dupes."""
    db_path = tmp_path / "edge.sqlite"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript("""
            CREATE TABLE t (id INTEGER, name TEXT, score REAL);
            INSERT INTO t VALUES
                (1, 'a', 1.0),
                (2, 'b', NULL),
                (3, NULL, 2.5),
                (4, 'a', 1.0),       -- duplicate of row 1 ignoring id
                (5, 'c', '3.0');     -- str literal in REAL column (SQLite type-soup)

            CREATE TABLE empty (x INTEGER);
        """)
        conn.commit()
    finally:
        conn.close()
    return db_path


# ---------- _run / timeout ---------------------------------------------------

def test_run_returns_rows_and_timing(db: Path):
    rows, elapsed_ms = _run(db, "SELECT id FROM t ORDER BY id", timeout_s=5.0)
    assert rows == [(1,), (2,), (3,), (4,), (5,)]
    assert elapsed_ms >= 0.0


def test_run_raises_for_bad_sql(db: Path):
    with pytest.raises(sqlite3.OperationalError):
        _run(db, "SELECT * FROM nope", timeout_s=5.0)


def test_run_wall_clock_timeout(db: Path):
    # Unbounded recursion in a CTE — sqlite will spin forever generating rows.
    runaway = """
        WITH RECURSIVE r(n) AS (
            SELECT 1 UNION ALL SELECT n+1 FROM r
        )
        SELECT n FROM r
    """
    with pytest.raises(QueryTimeout):
        _run(db, runaway, timeout_s=0.3)


# ---------- _compare semantics ----------------------------------------------

def test_compare_order_blind():
    assert _compare([(1,), (2,)], [(2,), (1,)]) is True


def test_compare_multiset_blind_matches_upstream():
    # BIRD uses set comparison, so duplicate rows on one side don't matter.
    # We match upstream even though it's arguably wrong for COUNT-style queries.
    assert _compare([(1,), (1,), (2,)], [(1,), (2,)]) is True


def test_compare_handles_null_in_rows():
    assert _compare([(None, 1)], [(None, 1)]) is True
    assert _compare([(None, 1)], [(None, 2)]) is False


def test_compare_mixed_types_no_typeerror():
    # int vs float (equal value, different type) — Python treats 1 == 1.0
    # inside a set, so these compare equal. Document the behaviour.
    assert _compare([(1, 'a')], [(1.0, 'a')]) is True
    # str-of-number vs number: NOT equal (no string coercion).
    assert _compare([('1',)], [(1,)]) is False


def test_compare_empty_sets_equal():
    assert _compare([], []) is True
    assert _compare([], [(1,)]) is False


# ---------- score_one: NULLs and mixed types --------------------------------

def test_score_one_gold_is_gold_with_nulls(db: Path):
    sql = "SELECT id, name, score FROM t"
    r = score_one(question_id=1, db_path=db, predicted_sql=sql, gold_sql=sql)
    assert r.ex == 1
    assert r.error is None
    assert r.predicted_rows == 5 == r.gold_rows


def test_score_one_predicted_subset_fails(db: Path):
    gold = "SELECT id FROM t"
    pred = "SELECT id FROM t WHERE id < 3"
    r = score_one(question_id=2, db_path=db, predicted_sql=pred, gold_sql=gold)
    assert r.ex == 0


# ---------- duplicates (set vs multiset) ------------------------------------

def test_duplicates_set_collapse(db: Path):
    # Gold: SELECT name FROM t  → ('a', 'b', None, 'a', 'c')
    # Pred: SELECT DISTINCT name → ('a', 'b', None, 'c')
    # Set comparison treats these as equal, matching BIRD upstream.
    gold = "SELECT name FROM t"
    pred = "SELECT DISTINCT name FROM t"
    r = score_one(question_id=3, db_path=db, predicted_sql=pred, gold_sql=gold)
    assert r.ex == 1


# ---------- ORDER BY: when does row order matter? ---------------------------

def test_order_by_direction_does_not_matter_per_bird(db: Path):
    # BIRD's set comparison erases ORDER BY entirely. So ASC vs DESC scores
    # equal — even when the original question implied a specific direction.
    # This is a known under-penalisation in the upstream metric.
    asc = "SELECT id FROM t ORDER BY id ASC"
    desc = "SELECT id FROM t ORDER BY id DESC"
    r = score_one(question_id=4, db_path=db, predicted_sql=asc, gold_sql=desc)
    assert r.ex == 1


# ---------- empty result sets ------------------------------------------------

def test_empty_results_match(db: Path):
    sql = "SELECT x FROM empty"
    r = score_one(question_id=5, db_path=db, predicted_sql=sql, gold_sql=sql)
    assert r.ex == 1
    assert r.predicted_rows == 0 == r.gold_rows


def test_empty_vs_nonempty(db: Path):
    r = score_one(question_id=6, db_path=db,
                  predicted_sql="SELECT x FROM empty",
                  gold_sql="SELECT id FROM t")
    assert r.ex == 0
    assert r.predicted_rows == 0
    assert r.gold_rows == 5


# ---------- predicted SQL errors --------------------------------------------

def test_predicted_sql_syntax_error(db: Path):
    r = score_one(question_id=7, db_path=db,
                  predicted_sql="SELEKT id FROM t",
                  gold_sql="SELECT id FROM t")
    assert r.ex == 0
    assert r.error is not None
    assert "predicted SQL failed" in r.error
    assert r.predicted_rows == 0
    assert r.gold_rows == 5
    assert r.timeout is False


def test_predicted_sql_runtime_error(db: Path):
    r = score_one(question_id=8, db_path=db,
                  predicted_sql="SELECT bogus_col FROM t",
                  gold_sql="SELECT id FROM t")
    assert r.ex == 0
    assert r.error is not None and "predicted SQL failed" in r.error


def test_gold_sql_error_still_returns_result(db: Path):
    r = score_one(question_id=9, db_path=db,
                  predicted_sql="SELECT id FROM t",
                  gold_sql="SELECT * FROM does_not_exist")
    assert r.ex == 0
    assert r.error is not None
    assert "gold SQL failed" in r.error
    assert r.predicted_ms is None  # never ran


# ---------- predicted SQL times out -----------------------------------------

RUNAWAY_SQL = """
WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r)
SELECT n FROM r
"""


def test_predicted_sql_timeout(db: Path):
    r = score_one(question_id=10, db_path=db,
                  predicted_sql=RUNAWAY_SQL,
                  gold_sql="SELECT id FROM t",
                  timeout_s=0.3)
    assert r.ex == 0
    assert r.timeout is True
    assert r.error is not None
    assert "timed out" in r.error
    assert r.gold_rows == 5
    assert r.predicted_ms is None


def test_gold_sql_timeout(db: Path):
    r = score_one(question_id=11, db_path=db,
                  predicted_sql="SELECT id FROM t",
                  gold_sql=RUNAWAY_SQL,
                  timeout_s=0.3)
    assert r.ex == 0
    assert r.timeout is True
    assert "gold SQL timed out" in r.error


# ---------- Aggregate -------------------------------------------------------

def _mk(qid: int, ex: int, diff: str | None = None, err: str | None = None,
        timeout: bool = False) -> ScoreResult:
    return ScoreResult(
        question_id=qid, ex=ex, predicted_rows=0, gold_rows=0,
        predicted_ms=None, gold_ms=0.0, error=err,
        difficulty=diff, timeout=timeout,
    )


def test_aggregate_overall():
    agg = aggregate([_mk(1, 1), _mk(2, 0, err="x"), _mk(3, 1)])
    assert agg.n == 3
    assert agg.ex_sum == 2
    assert agg.failures == 1
    assert agg.ex == pytest.approx(2 / 3)


def test_aggregate_per_difficulty():
    agg = aggregate([
        _mk(1, 1, "simple"),
        _mk(2, 0, "simple"),
        _mk(3, 1, "moderate"),
        _mk(4, 1, "challenging"),
        _mk(5, 0, "challenging"),
        _mk(6, 1, None),                  # missing difficulty — counted overall only
    ])
    assert agg.n == 6
    assert agg.ex_sum == 4
    assert agg.ex_for("simple") == pytest.approx(0.5)
    assert agg.ex_for("moderate") == pytest.approx(1.0)
    assert agg.ex_for("challenging") == pytest.approx(0.5)


def test_aggregate_timeouts_counted():
    agg = aggregate([_mk(1, 0, err="t", timeout=True), _mk(2, 1)])
    assert agg.timeouts == 1


# ---------- VES -------------------------------------------------------------

def test_clean_abnormal_drops_outliers():
    # Note on upstream behaviour: ±3σ rejection is generous when one outlier
    # dominates the spread (its own deviation inflates σ enough to swallow
    # itself). We mirror that. So the test uses a tight cluster + one
    # neighbour-but-not-extreme value where the math actually rejects.
    cleaned = _clean_abnormal([1.0] * 10 + [2.0])
    assert 2.0 not in cleaned
    assert cleaned == [1.0] * 10


def test_clean_abnormal_short_lists_passthrough():
    assert _clean_abnormal([]) == []
    assert _clean_abnormal([1.5]) == [1.5]


def test_ves_zero_when_incorrect(db: Path):
    r = ves_one(question_id=1, db_path=db,
                predicted_sql="SELECT id FROM t WHERE id < 3",
                gold_sql="SELECT id FROM t",
                iterate_num=3)
    assert r.correct == 0
    assert r.time_ratio == 0.0
    assert r.score == 0.0


def test_ves_positive_when_correct(db: Path):
    sql = "SELECT id, name, score FROM t"
    r = ves_one(question_id=2, db_path=db,
                predicted_sql=sql, gold_sql=sql,
                iterate_num=5)
    assert r.correct == 1
    assert r.time_ratio > 0
    assert r.score > 0
    # gold == pred, so ratio clusters around 1 → score around 100
    assert 10 < r.score < 1000


def test_ves_aggregate_basic():
    rs = [
        VESResult(question_id=1, correct=1, time_ratio=1.0, iterations=10,
                  difficulty="simple"),
        VESResult(question_id=2, correct=0, time_ratio=0.0, iterations=0,
                  difficulty="simple"),
        VESResult(question_id=3, correct=1, time_ratio=4.0, iterations=10,
                  difficulty="moderate"),
    ]
    a = aggregate_ves(rs)
    assert a.n == 3
    assert a.correct == 2
    # scores: 100, 0, 200 → mean 100
    assert a.score == pytest.approx(100.0)
    assert a.score_for("simple") == pytest.approx(50.0)
    assert a.score_for("moderate") == pytest.approx(200.0)


def test_ves_timeout(db: Path):
    r = ves_one(question_id=4, db_path=db,
                predicted_sql=RUNAWAY_SQL,
                gold_sql="SELECT id FROM t",
                timeout_s=0.3, iterate_num=3)
    assert r.correct == 0
    assert r.timeout is True
    assert "timed out" in r.error

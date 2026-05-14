"""BIRD-mini: a fixed 50-question subset for fast iteration.

Stratified by difficulty (proportional to dev set) with DB coverage ensured
where possible. Deterministic with seed=42. The canonical selection lives in
mini.json; the script regenerates it idempotently.

CLI:
    python -m bird.mini --regenerate     # rewrite mini.json from BIRD dev
    python -m bird.mini --verify         # assert mini.json matches algorithm
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from bird.dataset import BirdQuestion, load_questions

MINI_JSON = Path(__file__).parent / "mini.json"
MINI_N = 50
SEED = 42


def select(questions: list[BirdQuestion], n: int = MINI_N, seed: int = SEED) -> list[int]:
    """Select n question_ids: stratified by difficulty + DB coverage where possible."""
    rng = random.Random(seed)

    diff_counts = Counter(q.difficulty for q in questions)
    total = sum(diff_counts.values())
    diff_targets: dict[str, int] = {
        d: round(c / total * n) for d, c in diff_counts.items()
    }
    # Reconcile rounding to exactly n
    while sum(diff_targets.values()) > n:
        d = max(diff_targets, key=diff_targets.__getitem__)
        diff_targets[d] -= 1
    while sum(diff_targets.values()) < n:
        d = max(diff_targets, key=diff_targets.__getitem__)
        diff_targets[d] += 1

    # Bucket by difficulty, shuffle deterministically, draw the target count
    buckets: dict[str, list[BirdQuestion]] = defaultdict(list)
    for q in questions:
        buckets[q.difficulty].append(q)

    selected: list[BirdQuestion] = []
    for diff, target in diff_targets.items():
        bucket = sorted(buckets[diff], key=lambda q: q.question_id)
        rng.shuffle(bucket)
        selected.extend(bucket[:target])

    # Coverage pass: ensure every DB is represented at least once if room allows
    db_present = {q.db_id for q in selected}
    all_dbs = {q.db_id for q in questions}
    missing = sorted(all_dbs - db_present)

    for db in missing:
        candidates = sorted(
            [q for q in questions if q.db_id == db], key=lambda q: q.question_id
        )
        if not candidates:
            continue
        rng.shuffle(candidates)
        to_add = candidates[0]

        # Evict from the most-represented (db, difficulty=target_diff) pair,
        # preferring to keep stratification stable.
        same_diff = [
            q for q in selected if q.difficulty == to_add.difficulty and q.db_id != db
        ]
        pool = same_diff or [q for q in selected if q.db_id != db]
        if not pool:
            continue
        db_counts = Counter(q.db_id for q in pool)
        evict_db = db_counts.most_common(1)[0][0]
        to_evict = next(q for q in pool if q.db_id == evict_db)
        selected.remove(to_evict)
        selected.append(to_add)

    selected.sort(key=lambda q: q.question_id)
    return [q.question_id for q in selected]


def write_mini(questions: list[BirdQuestion]) -> Path:
    ids = select(questions)
    MINI_JSON.write_text(json.dumps(ids, indent=2) + "\n")
    return MINI_JSON


def load_mini(questions: list[BirdQuestion] | None = None) -> list[BirdQuestion]:
    """Load BIRD-mini as BirdQuestion objects against the full dev set."""
    if questions is None:
        questions = load_questions()
    ids = set(json.loads(MINI_JSON.read_text()))
    by_id = {q.question_id: q for q in questions}
    return [by_id[i] for i in sorted(ids) if i in by_id]


def _summarize(questions: list[BirdQuestion]) -> None:
    diff = Counter(q.difficulty for q in questions)
    db = Counter(q.db_id for q in questions)
    print(f"n = {len(questions)}")
    print(f"difficulty: {dict(diff)}")
    print(f"db coverage: {len(db)}/11 dbs")
    for d, c in sorted(db.items()):
        print(f"  {d:30s} {c}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--regenerate", action="store_true", help="(re)write mini.json")
    p.add_argument("--verify", action="store_true", help="assert mini.json matches algorithm")
    p.add_argument("--show", action="store_true", help="print composition of mini.json")
    args = p.parse_args()

    questions = load_questions()

    if args.regenerate:
        path = write_mini(questions)
        print(f"wrote {path}")
        _summarize(load_mini(questions))
        return 0

    if args.verify:
        expected = select(questions)
        actual = json.loads(MINI_JSON.read_text())
        if expected == sorted(actual):
            print("✓ mini.json matches algorithm")
            return 0
        print("✗ mini.json drifted from algorithm output")
        return 1

    if args.show or not (args.regenerate or args.verify):
        _summarize(load_mini(questions))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

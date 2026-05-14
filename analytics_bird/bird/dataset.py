"""BIRD dev set loader.

Expected layout after extraction (paths resolved against BIRD_DATA_DIR):

    bird/data/dev/
      ├── dev.json
      ├── dev_tables.json
      └── dev_databases/<db_id>/<db_id>.sqlite

The actual layout BIRD ships varies slightly between versions; resolve_paths()
walks the data dir to find the canonical files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class BirdQuestion:
    question_id: int
    db_id: str
    question: str
    evidence: str
    gold_sql: str
    difficulty: str | None
    db_path: Path

    @property
    def dsn(self) -> str:
        return f"sqlite:///{self.db_path}"


@dataclass(frozen=True)
class BirdPaths:
    dev_json: Path
    tables_json: Path
    databases_dir: Path


def resolve_paths(data_dir: Path = DATA_DIR) -> BirdPaths:
    """Find the canonical BIRD files under data_dir.

    Raises FileNotFoundError if the dataset isn't extracted yet.
    """
    candidates_dev = list(data_dir.rglob("dev.json"))
    candidates_tables = list(data_dir.rglob("dev_tables.json"))
    candidates_db_dirs = [p for p in data_dir.rglob("dev_databases") if p.is_dir()]

    if not candidates_dev:
        raise FileNotFoundError(
            f"BIRD dev.json not found under {data_dir}. "
            f"Run: python -m bird.download"
        )
    if not candidates_db_dirs:
        raise FileNotFoundError(
            f"BIRD dev_databases/ not found under {data_dir}."
        )

    return BirdPaths(
        dev_json=candidates_dev[0],
        tables_json=candidates_tables[0] if candidates_tables else candidates_dev[0],
        databases_dir=candidates_db_dirs[0],
    )


def load_questions(data_dir: Path = DATA_DIR) -> list[BirdQuestion]:
    """Load all BIRD dev questions, resolving each to its SQLite path."""
    paths = resolve_paths(data_dir)
    with paths.dev_json.open() as f:
        raw = json.load(f)

    out: list[BirdQuestion] = []
    for rec in raw:
        db_id = rec["db_id"]
        db_path = paths.databases_dir / db_id / f"{db_id}.sqlite"
        if not db_path.exists():
            # Some BIRD releases use a different inner filename
            alt = list((paths.databases_dir / db_id).glob("*.sqlite"))
            if not alt:
                continue
            db_path = alt[0]

        out.append(
            BirdQuestion(
                question_id=rec.get("question_id", len(out)),
                db_id=db_id,
                question=rec["question"],
                evidence=rec.get("evidence", ""),
                gold_sql=rec.get("SQL") or rec.get("sql") or "",
                difficulty=rec.get("difficulty"),
                db_path=db_path,
            )
        )
    return out


def filter_questions(
    questions: list[BirdQuestion],
    db_id: str | None = None,
    difficulty: str | None = None,
    limit: int | None = None,
) -> list[BirdQuestion]:
    out = questions
    if db_id is not None:
        out = [q for q in out if q.db_id == db_id]
    if difficulty is not None:
        out = [q for q in out if q.difficulty == difficulty]
    if limit is not None:
        out = out[:limit]
    return out

"""Day-1 smoke test.

No model. No SDK. No MCP. Just exercise the 6 tool primitives against a tiny
synthetic SQLite DB and confirm:
  - all 6 tools work
  - read-only enforcement blocks DROP/DELETE
  - a JSONL trace is produced and parseable
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

from tools.sql import (
    connect,
    describe_schema,
    disconnect,
    execute_sql,
    list_tables,
    sample_rows,
    validate_sql,
)
from tracing.jsonl import open_trace


def make_demo_db() -> Path:
    path = Path(tempfile.mkdtemp(prefix="bird-smoke-")) / "demo.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE team (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            state TEXT
        );
        CREATE TABLE player (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER REFERENCES team(id)
        );
        INSERT INTO team VALUES (1, 'Lakers', 'CA'), (2, 'Celtics', 'MA');
        INSERT INTO player VALUES
            (1, 'LeBron James', 1),
            (2, 'Jayson Tatum', 2),
            (3, 'Anthony Davis', 1);
        """
    )
    conn.commit()
    conn.close()
    return path


def _step(trace, name, fn, *args, **kwargs):
    trace.tool_call(name, {"args": list(args), "kwargs": kwargs})
    out = fn(*args, **kwargs)
    trace.tool_result(name, out)
    print(f"\n{name:>16}  →  {out}")
    return out


def main() -> int:
    db = make_demo_db()
    print(f"Demo DB at: {db}")

    trace_path = Path(__file__).parent / "runs" / "smoke" / "day1.jsonl"
    failures: list[str] = []

    with open_trace(trace_path, meta={"test": "day1-smoke"}) as trace:
        r = _step(trace, "connect", connect, f"sqlite:///{db}")
        cid = r["connection_id"]

        r = _step(trace, "list_tables", list_tables, cid)
        assert set(r["tables"]) == {"team", "player"}, f"unexpected tables: {r}"

        r = _step(trace, "describe_schema", describe_schema, cid, ["team", "player"])
        assert r["tables"]["team"]["row_count"] == 2
        assert r["tables"]["player"]["row_count"] == 3
        assert r["tables"]["player"]["foreign_keys"], "expected FK on player.team_id"

        r = _step(trace, "sample_rows", sample_rows, cid, "team", 5)
        assert len(r["rows"]) == 2

        r = _step(trace, "validate_sql (good)", validate_sql, cid,
                  "SELECT name FROM player WHERE team_id = 1")
        assert r["valid"] is True

        r = _step(trace, "validate_sql (bad)", validate_sql, cid, "SELECT WHERE")
        assert r["valid"] is False

        r = _step(trace, "validate_sql (write blocked)", validate_sql, cid,
                  "DROP TABLE player")
        if r.get("valid"):
            failures.append("read-only failed to block DROP via validate_sql")

        r = _step(trace, "execute_sql (join)", execute_sql, cid,
                  "SELECT t.name AS team, p.name AS player "
                  "FROM team t JOIN player p ON p.team_id = t.id "
                  "ORDER BY t.name, p.name")
        assert r["success"] and r["row_count"] == 3

        r = _step(trace, "execute_sql (write blocked)", execute_sql, cid,
                  "DELETE FROM team")
        if r.get("success"):
            failures.append("read-only failed to block DELETE via execute_sql")

        disconnect(cid)
        trace.final(predicted_sql=None, success=not failures,
                    error=", ".join(failures) or None)

    # Verify trace is valid JSONL
    lines = trace_path.read_text().strip().split("\n")
    parsed = [json.loads(line) for line in lines]
    kinds = [p["kind"] for p in parsed]
    assert kinds[0] == "run_meta", f"first record should be run_meta: {kinds[0]}"
    assert kinds[-1] == "final", f"last record should be final: {kinds[-1]}"
    print(f"\nTrace OK: {len(parsed)} records → {trace_path}")

    if failures:
        print(f"\n✗ FAILURES: {failures}")
        return 1
    print("\n✓ Smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

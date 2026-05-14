"""SQL tool primitives over SQLite (and Postgres later).

Six primitives per v0_proposal.md, all stateless except `connect` which registers
an engine in a process-local map keyed by connection_id.

Read-only enforcement:
  - regex pre-check against the SQL string (SELECT/WITH/EXPLAIN/PRAGMA only)
  - SQLite-level pragma `query_only = ON` set at connection time
  - Postgres should connect as a role with only SELECT grants (out of scope here)
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine

_connections: dict[str, Engine] = {}

_READ_ONLY_RE = re.compile(r"^\s*(SELECT|WITH|EXPLAIN|PRAGMA)\b", re.IGNORECASE)


def _is_read_only(sql: str) -> bool:
    return bool(_READ_ONLY_RE.match(sql.strip()))


def _get(connection_id: str) -> Engine:
    engine = _connections.get(connection_id)
    if engine is None:
        raise KeyError(f"Unknown connection_id: {connection_id}")
    return engine


def connect(dsn: str) -> dict[str, Any]:
    """Open a database connection. Returns a connection_id for subsequent calls."""
    engine = create_engine(dsn, future=True)

    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _enforce_readonly(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA query_only = ON")
            cur.close()

    conn_id = str(uuid.uuid4())
    _connections[conn_id] = engine
    return {"connection_id": conn_id, "dialect": engine.dialect.name}


def disconnect(connection_id: str) -> dict[str, Any]:
    engine = _connections.pop(connection_id, None)
    if engine is not None:
        engine.dispose()
    return {"success": True}


def list_tables(connection_id: str, pattern: str | None = None) -> dict[str, Any]:
    engine = _get(connection_id)
    tables = inspect(engine).get_table_names()
    if pattern:
        rx = re.compile(pattern)
        tables = [t for t in tables if rx.search(t)]
    return {"tables": tables}


def describe_schema(connection_id: str, tables: list[str]) -> dict[str, Any]:
    engine = _get(connection_id)
    insp = inspect(engine)
    out: dict[str, Any] = {}
    for t in tables:
        cols = [
            {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]}
            for c in insp.get_columns(t)
        ]
        pk = insp.get_pk_constraint(t).get("constrained_columns", [])
        fks = [
            {
                "columns": fk["constrained_columns"],
                "ref_table": fk["referred_table"],
                "ref_columns": fk["referred_columns"],
            }
            for fk in insp.get_foreign_keys(t)
        ]
        try:
            with engine.connect() as conn:
                row_count = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
        except Exception:
            row_count = None
        out[t] = {"columns": cols, "primary_keys": pk, "foreign_keys": fks, "row_count": row_count}
    return {"tables": out}


def sample_rows(connection_id: str, table: str, n: int = 5) -> dict[str, Any]:
    engine = _get(connection_id)
    with engine.connect() as conn:
        result = conn.execute(text(f'SELECT * FROM "{table}" LIMIT :n'), {"n": n})
        cols = list(result.keys())
        rows = [dict(r._mapping) for r in result]
    return {"table": table, "columns": cols, "rows": rows}


def execute_sql(
    connection_id: str,
    sql: str,
    max_rows: int = 100,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    if not _is_read_only(sql):
        return {
            "success": False,
            "error": "Only read-only queries are permitted (SELECT/WITH/EXPLAIN/PRAGMA).",
        }

    engine = _get(connection_id)
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            cols = list(result.keys()) if result.returns_rows else []
            rows: list[dict[str, Any]] = []
            if result.returns_rows:
                for i, r in enumerate(result):
                    if i >= max_rows:
                        break
                    rows.append(dict(r._mapping))
        return {
            "success": True,
            "columns": cols,
            "rows": rows,
            "row_count": len(rows),
            "truncated": result.returns_rows and len(rows) == max_rows,
            "elapsed_s": round(time.perf_counter() - start, 4),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_s": round(time.perf_counter() - start, 4),
        }


def validate_sql(connection_id: str, sql: str) -> dict[str, Any]:
    if not _is_read_only(sql):
        return {"valid": False, "error": "Only read-only queries are permitted."}

    engine = _get(connection_id)
    dialect = engine.dialect.name
    try:
        with engine.connect() as conn:
            if dialect == "sqlite":
                conn.execute(text(f"EXPLAIN QUERY PLAN {sql}"))
            elif dialect == "postgresql":
                conn.execute(text(f"EXPLAIN {sql}"))
            else:
                conn.execute(text(f"SELECT * FROM ({sql}) AS _v LIMIT 0"))
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}

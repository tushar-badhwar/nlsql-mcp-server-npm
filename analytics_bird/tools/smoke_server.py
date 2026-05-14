"""Minimal stdio smoke test for `tools.server`.

Spawns the MCP server as a subprocess, opens a stdio client, lists tools,
then runs connect → list_tables → execute_sql → disconnect against a tiny
in-temp SQLite DB. Asserts on the wire-level round-trip.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _make_demo_db() -> Path:
    path = Path(tempfile.mkdtemp(prefix="bird-mcp-")) / "demo.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO t VALUES (1, 'alpha'), (2, 'beta'), (3, 'gamma');
        """
    )
    conn.commit()
    conn.close()
    return path


def _decode(result) -> dict:
    """Read the text payload out of a CallToolResult."""
    if not result.content:
        return {}
    block = result.content[0]
    return json.loads(block.text)


async def main() -> int:
    db = _make_demo_db()
    print(f"demo DB: {db}")

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tools.server"],
        cwd=str(Path(__file__).resolve().parent.parent),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"tools: {names}")
            assert set(names) >= {
                "connect", "disconnect", "list_tables", "describe_schema",
                "sample_rows", "execute_sql", "validate_sql",
            }, f"missing tools: {names}"

            r = _decode(await session.call_tool("connect", {"dsn": f"sqlite:///{db}"}))
            print(f"connect → {r}")
            assert "connection_id" in r, r
            cid = r["connection_id"]

            r = _decode(await session.call_tool("list_tables", {"connection_id": cid}))
            print(f"list_tables → {r}")
            assert r["tables"] == ["t"], r

            r = _decode(await session.call_tool(
                "execute_sql",
                {"connection_id": cid, "sql": "SELECT COUNT(*) AS n FROM t"},
            ))
            print(f"execute_sql → {r}")
            assert r["success"] and r["rows"][0]["n"] == 3, r

            r = _decode(await session.call_tool(
                "execute_sql",
                {"connection_id": cid, "sql": "DELETE FROM t"},
            ))
            print(f"write-blocked → {r}")
            assert r["success"] is False, "DELETE should be blocked"

            r = _decode(await session.call_tool("disconnect", {"connection_id": cid}))
            assert r["success"], r

    print("\n✓ MCP stdio smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

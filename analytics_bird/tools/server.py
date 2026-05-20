"""MCP stdio server exposing the 6 SQL primitives from `tools.sql`.

Run directly:
    python -m tools.server

The Claude / OpenAI / Gemini adapters spawn this as a subprocess and speak MCP
over stdio. Tool args/returns are JSON-friendly; payloads are serialized with
`json.dumps(..., default=str)` so SQLAlchemy `Row` mappings and other natives
round-trip cleanly.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from tools import sql as sql_tools

server = Server("analytics-bird-sql")


_TOOLS: list[types.Tool] = [
    types.Tool(
        name="connect",
        description=(
            "Open a database connection. Returns a `connection_id` to use in "
            "subsequent tool calls. For BIRD this will be a `sqlite:///...` DSN."
        ),
        inputSchema={
            "type": "object",
            "properties": {"dsn": {"type": "string", "description": "SQLAlchemy DSN"}},
            "required": ["dsn"],
        },
    ),
    types.Tool(
        name="disconnect",
        description="Close a connection opened with `connect`.",
        inputSchema={
            "type": "object",
            "properties": {"connection_id": {"type": "string"}},
            "required": ["connection_id"],
        },
    ),
    types.Tool(
        name="list_tables",
        description="List tables on a connection. Optional regex `pattern` filters names.",
        inputSchema={
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"},
                "pattern": {"type": "string", "description": "optional regex filter"},
            },
            "required": ["connection_id"],
        },
    ),
    types.Tool(
        name="describe_schema",
        description=(
            "Return columns, types, primary/foreign keys, and row counts for the "
            "given tables. Call before writing SQL — the schema is rarely what "
            "the question text implies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"},
                "tables": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["connection_id", "tables"],
        },
    ),
    types.Tool(
        name="sample_rows",
        description="Return up to `n` rows from `table` for inspection (default n=5).",
        inputSchema={
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"},
                "table": {"type": "string"},
                "n": {"type": "integer", "minimum": 1, "default": 5},
            },
            "required": ["connection_id", "table"],
        },
    ),
    types.Tool(
        name="execute_sql",
        description=(
            "Run a SELECT/WITH/EXPLAIN/PRAGMA query. Read-only is enforced. "
            "Returns rows (up to `max_rows`, default 100) and elapsed time."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"},
                "sql": {"type": "string"},
                "max_rows": {"type": "integer", "minimum": 1, "default": 100},
                "timeout_s": {"type": "number", "default": 30.0},
            },
            "required": ["connection_id", "sql"],
        },
    ),
    types.Tool(
        name="validate_sql",
        description=(
            "Parse-only / EXPLAIN dry run. Returns {valid: bool, error?: str}. "
            "Use this to catch typos before `execute_sql`."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"},
                "sql": {"type": "string"},
            },
            "required": ["connection_id", "sql"],
        },
    ),
]


_DISPATCH = {
    "connect": lambda a: sql_tools.connect(dsn=a["dsn"]),
    "disconnect": lambda a: sql_tools.disconnect(connection_id=a["connection_id"]),
    "list_tables": lambda a: sql_tools.list_tables(
        connection_id=a["connection_id"], pattern=a.get("pattern")
    ),
    "describe_schema": lambda a: sql_tools.describe_schema(
        connection_id=a["connection_id"], tables=a["tables"]
    ),
    "sample_rows": lambda a: sql_tools.sample_rows(
        connection_id=a["connection_id"], table=a["table"], n=a.get("n", 5)
    ),
    "execute_sql": lambda a: sql_tools.execute_sql(
        connection_id=a["connection_id"],
        sql=a["sql"],
        max_rows=a.get("max_rows", 100),
        timeout_s=a.get("timeout_s", 30.0),
    ),
    "validate_sql": lambda a: sql_tools.validate_sql(
        connection_id=a["connection_id"], sql=a["sql"]
    ),
}


@server.list_tools()
async def _list_tools() -> list[types.Tool]:
    return _TOOLS


@server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    fn = _DISPATCH.get(name)
    if fn is None:
        payload = {"error": f"unknown tool: {name}"}
    else:
        try:
            payload = fn(arguments or {})
        except Exception as e:
            payload = {"error": f"{type(e).__name__}: {e}"}
    return [types.TextContent(type="text", text=json.dumps(payload, default=str))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

# Analytics Agent Foundation — One-Pager

## Goal
Build a single, SDK-agnostic foundation for evaluating model × agent-architecture combinations on analytics tasks. The deliverable is a benchmark harness with reproducible runs across three agent SDKs, sharing one MCP tool surface.

## Target Benchmark
**Primary:** BIRD (12k NL→SQL pairs, 95 DBs) — execution accuracy + valid-efficiency score. Mature, easy to iterate, current SOTA ~75%.
**Secondary:** Spider 2.0 (warehouse-realistic, multi-step). Current SOTA ~40% — more headroom and closer to "real analytics."
**Aspirational:** an in-house multi-step suite (chart, follow-up, hypothesis). Defer until BIRD/Spider 2.0 wired up.

Metric: per-(model, SDK, architecture) tuple, report execution accuracy, mean turns, total tokens, wall-clock. Three numbers, not one.

## Scope of "Any Database"
**In:** SQLite, Postgres, MySQL, BigQuery, Snowflake. Read-only enforced server-side (query rewrite or role-level). Auth via env-injected service-account JSON / connection string / OAuth refresh token. Hard limits: row cap, statement timeout, no DDL/DML.
**Out (v1):** Databricks, Redshift, SSH tunnels, row-level security, multi-tenant credential vaulting, PII redaction.

## Shared Tool Surface (MCP)
Six primitives, all stateless except `connect`:

1. `connect(dsn | profile)` — establishes session, returns connection_id
2. `list_tables(connection_id, pattern?)`
3. `describe_schema(connection_id, tables[])` — columns, types, PK/FK, row counts
4. `sample_rows(connection_id, table, n)`
5. `execute_sql(connection_id, sql, max_rows, timeout)` — read-only enforced
6. `validate_sql(connection_id, sql)` — EXPLAIN / parse-only dry run

Optional (Phase 5+): `search_columns(connection_id, query)` for schemas >50 tables.

**Removed:** the current `natural_language_to_sql` tool. NL→SQL becomes the agent's job, not the tool's — that's the experiment.

## Three SDK Adapters
Each ~100 LoC, identical task loop, same MCP server, different SDK wiring:
- **Claude Agent SDK** (Python) — native MCP via `ClaudeSDKClient`
- **OpenAI Agents SDK** (Python) — `MCPServerStdio`
- **Google ADK** (Python) — `MCPToolset`

Each adapter is a thin function: `run_task(question, model, db_profile) → predicted_sql, trace`.

## Architecture
```
benchmarks/    BIRD + Spider 2.0 runners + scoring
adapters/      claude_sdk.py, openai_agents.py, gemini_adk.py
mcp_server/    Python package, ships with `uvx analytics-mcp`
core/          DB drivers, read-only enforcement, schema utils
evals/         per-run traces (JSONL), aggregate reports
```

No Node wrapper. No git submodules. No CrewAI in the critical path (keep as one named *baseline* condition for honesty).

## Phases
1. **Lock scope** — this doc + benchmark + DB list approved (today)
2. **Extract & repackage** — pull `nl2sql` SQL/schema utilities into `core/`; publish `analytics-mcp` Python package; delete Node wrapper, submodule, NBA DB from package (1 wk)
3. **Tool surface** — implement the six primitives; read-only enforcement; unit tests against SQLite + Postgres (1 wk)
4. **First adapter end-to-end** — Claude Agent SDK + BIRD-mini (50 questions). Iterate until execution accuracy >0 (3 days)
5. **Two more adapters** — OpenAI Agents + Gemini ADK on BIRD-mini. Verify result parity within ±2% (3 days)
6. **Full BIRD eval** — N models × 3 SDKs × full dev set. Publish results table (1 wk)
7. **Spider 2.0** — same matrix, second eval (1 wk)

## Non-Goals
UI, hosted multi-tenant, streaming, vector retrieval over schemas, chat memory, learned schema linkers. Each is a real project; none belongs in v1.

## Open Questions
1. **Benchmark target** — BIRD-primary, Spider 2.0-secondary, agree?
2. **Database scope** — drop BigQuery/Snowflake from v1 if no test accounts? OK to ship SQLite+Postgres+MySQL only?
3. **Model set** — Claude Sonnet 4.6, GPT-5, Gemini 2.5 Pro at minimum? Open-weights too (Llama, Qwen)?
4. **Publish results** — public leaderboard repo, or internal?
5. **License** — keep MIT, or AGPL since this becomes a research artifact?

# v1 Plan — Analytics Deployment First

Synthesizes `v0_proposal.md` (analytics SOTA benchmark) with `v0_critique.md` (ship one deployment, don't build a framework). One repo, one deployment, six weeks.

## Locked scope

- **Benchmark:** BIRD dev set (1,534 questions, 11 SQLite DBs). Spider 2.0 deferred until BIRD numbers exist. BIRD test set deferred until a dev result justifies a leaderboard submission.
- **Databases:** SQLite (BIRD-native) + Postgres (port one BIRD DB to validate the abstraction). Drop BigQuery, Snowflake, MySQL from v1.
- **SDKs:** Claude Agent SDK first and only for weeks 1–3. Add OpenAI Agents SDK + Gemini ADK in week 4 only after the Claude path works end-to-end.
- **Models:** Sonnet 4.6 for primary iteration. Sonnet 4.6 + GPT-5 + Gemini 2.5 Pro for the final 3×3 matrix. No open-weights in v1.
- **Repo shape:** one directory, `analytics_bird/`. No `kit/`. No CLI. No skill abstraction.
- **Trust:** trace every run to JSONL from day 1 (free; pays for itself). No policy engine, no audit, no drift — those live in `v0_trust.md` for after v1.
- **OSS:** none. Private repo. Defer until a second use case validates the abstractions.

**API access:** Anthropic / OpenAI / Google keys all available, but weeks 1–2 are buildable without them (tools, harness, dataset wiring, smoke tests with stubbed models). API spend begins in earnest at week 3.

## Out of scope (explicit, per the critique)

- The `kit/` library
- Three-SDK abstraction layer
- `deployment.yaml` config language
- CLI tool (`kit init`, `kit run`, etc.)
- Memory, secrets adapter, multi-tenant anything
- Warehouse connectors
- Web UI for traces
- Public benchmark publication

If any of these creep in during weeks 1–6, that's the framework instinct firing. Resist.

## Status (as of 2026-05-13)

- **Week 1 — done.** `analytics_bird/` scaffolded with 6 SQL tool primitives over SQLAlchemy (read-only enforced), JSONL trace writer, BIRD dataset loader + downloader + execution-accuracy scorer. `run_five.py` reports EX=1.00 on gold-on-gold (5 questions, california_schools). BIRD dev set (346 MB) downloaded locally, gitignored under `analytics_bird/bird/data/`.
- **BIRD-mini locked.** 50-question subset at `analytics_bird/bird/mini.json` — stratified by difficulty (30 simple / 15 moderate / 5 challenging, proportional to dev set) with all 11 DBs represented. Deterministic via `seed=42`; `python -m bird.mini --verify` enforces no silent drift.
- **Week 2 in flight** in worktree `../nlsql-mcp-server-npm-week2` on branch `week2-claude-adapter` — MCP stdio server + Claude Agent SDK adapter + BIRD bench runner. Already shipped commit `69795d2`.
- **Eval hardening in flight** in worktree `../nlsql-mcp-server-npm-eval` on branch `eval-hardening` — scorer alignment with BIRD's official evaluator + edge-case tests. Already shipped commits `6b0ec25` and `ee978e9`.

## Week-by-week build

| Week | Deliverable | Success signal | Status |
|---|---|---|---|
| 1 | BIRD dataset downloaded; 6 MCP tool primitives over SQLite; manual run of 5 questions; JSONL trace format defined. | One BIRD question answered correctly end-to-end. | ✅ done — EX=1.00 on 5 gold-on-gold |
| 2 | Claude Agent SDK adapter; BIRD-mini (50 questions) loop; basic prompt + tool iteration. | Execution accuracy > 50% on BIRD-mini. | 🟡 in worktree |
| 3 | Full BIRD dev run with Sonnet 4.6; failure-mode analysis (categorized). | First real number, ≥ 60% targeted; failure modes documented. | — |
| 4 | OpenAI Agents SDK + Gemini ADK adapters; BIRD-mini parity check across all three SDKs. | Three-SDK harness produces comparable numbers (within ±2%) on the same questions with the same model. | — |
| 5 | Full BIRD dev × 3 models × 3 SDKs; internal results doc with EX, VES, tokens, wall-clock. | 9-cell matrix with one clear winner; one architectural insight that wasn't obvious going in. | — |
| 6 | Decision gate: Spider 2.0 next, or pivot to second use case for `kit/` extraction. | Written go/no-go on Spider 2.0. | — |

Six weeks, one engineer, one repo.

## Tool surface (locked from v0_proposal.md)

Six primitives, exposed as MCP tools, all stateless except `connect`:

1. `connect(dsn | profile)` → connection_id
2. `list_tables(connection_id, pattern?)`
3. `describe_schema(connection_id, tables[])` — columns, types, PK/FK, row counts
4. `sample_rows(connection_id, table, n)`
5. `execute_sql(connection_id, sql, max_rows, timeout)` — read-only enforced
6. `validate_sql(connection_id, sql)` — EXPLAIN / parse-only dry run

**No `natural_language_to_sql` tool.** NL→SQL is the agent's job; that's the experiment. The current CrewAI-based path may be retained as one *named baseline* condition in week 5's matrix, for honesty.

## Success criteria

### Hard requirements (v1 ships only when these hold)
- A 9-cell results matrix: 3 models × 3 SDKs on BIRD dev set
- For each cell: execution accuracy (EX), valid efficiency score (VES), mean turns, total input/output tokens, wall-clock time
- Every run produces a JSONL trace, deterministically replayable for read-only tools
- Repeat runs of the same (model, SDK, question) produce stable EX (variance documented if not)
- All numbers reproducible from a single `python run_bench.py` invocation
- Failure-mode taxonomy: at least 5 categories with frequency counts per cell

### Soft goals
- At least one architectural insight not obvious going in (e.g., "Gemini wins with planning loops but loses with ReAct," or "tool design matters more than SDK choice")
- A written v2 spec covering Spider 2.0 + Postgres deployment + the second use case needed for `kit/` extraction
- An internal write-up that could become a public report later if v0_critique's OSS conditions are met

### What this proves
- Whether the six-primitive tool surface is sufficient for SOTA-shaped analytics tasks
- Whether SDK choice meaningfully affects results, or whether model dominates
- Whether the deployment-first, framework-later discipline holds under real engineering pressure

### What this does NOT prove
- That this generalizes to customer support, content gen, or any other use case (need a second deployment)
- That this is FDE-ready (need a real customer engagement)
- That the trust spine design is right (need its own v1)

Be honest about all three when reporting results.

## Repo layout for v1

```
analytics_bird/
├── pyproject.toml
├── README.md
├── bird/
│   ├── download.py           pulls BIRD dataset, sets up SQLite DBs
│   └── dataset.py            iterator over questions, gold SQL, eval
├── tools/                    the 6 MCP primitives
│   ├── server.py             stdio MCP server
│   └── sql.py                connect, list, describe, sample, execute, validate
├── adapters/
│   ├── claude.py             ← week 2
│   ├── openai.py             ← week 4
│   └── gemini.py             ← week 4
├── trace/
│   └── jsonl.py              trace dataclass + writer
├── eval/
│   ├── score.py              EX, VES scoring (BIRD's official metrics)
│   └── replay.py             read-only-tool replay
├── prompts/
│   └── system.md             system prompt(s) under test
├── runs/                     JSONL traces, gitignored
└── run_bench.py              entry point: full or mini run
```

That's the entire v1 surface. No `kit/`, no `deployment.yaml`, no clever abstractions.

## Risks to track

- **Model nondeterminism** — repeated runs may produce different SQL. Plan: run each (model, SDK, question) cell 3× and report mean + variance. Budget API spend accordingly.
- **BIRD evaluator quirks** — BIRD's official EX scorer has gotchas (precision-vs-recall on column order, NULL handling). Plan: lift the official scorer rather than reimplementing.
- **Token cost** — full BIRD × 3 models × 3 SDKs × 3 repeats ≈ 41k runs. Estimate cost before week 5; cap with BIRD-half if needed.
- **SDK feature drift** — three SDKs in active development. Pin versions at week 4 start; document.
- **CrewAI baseline temptation** — easy to spend a week tuning the existing CrewAI path. Cap: one day in week 5, no more.

## Next step (week 1, day 1)

Set up `analytics_bird/`, download BIRD, get one SQLite database loaded, hand-run a single question through a stubbed agent loop (no real model yet). That alone validates the tool surface and trace format before any API spend.

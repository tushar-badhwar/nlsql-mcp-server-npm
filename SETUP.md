# Worktree: week2-claude-adapter

Parallel session for the **week 2** deliverable per `v1_plan.md`:
Claude Agent SDK adapter wired to the 6 SQL tool primitives, run on BIRD-mini (50 questions), target EX > 50%.

Driver worktree (main): `/Users/ragebait.ai/nl_sql/nlsql-mcp-server-npm`

---

## Setup (run once)

```bash
cd analytics_bird

# 1. Virtualenv (gitignored; doesn't carry across worktrees)
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .[claude]      # sqlalchemy + claude-agent-sdk

# 2. BIRD dataset — symlink from the driver worktree (don't re-download)
mkdir -p bird
ln -s ../../nlsql-mcp-server-npm/analytics_bird/bird/data bird/data

# 3. Sanity-check: run the existing smoke + week-1 scripts
.venv/bin/python smoke_test.py            # exercises tool primitives
.venv/bin/python run_five.py              # 5 BIRD questions on gold SQL
```

If `smoke_test.py` passes and `run_five.py` reports EX=1.00 with 0 failures, the worktree is wired correctly.

---

## Goal of this worktree

Add these files (per `v1_plan.md` "Repo layout for v1"):

- `analytics_bird/tools/server.py` — MCP server exposing the 6 primitives over stdio
- `analytics_bird/adapters/claude.py` — Claude Agent SDK runner: takes a BIRD question, runs the SDK loop with the MCP server attached, returns predicted SQL + trace
- `analytics_bird/prompts/system.md` — system prompt under test
- `analytics_bird/run_bench.py` — entry point: `--n 50 --adapter claude --model claude-sonnet-4-6`

Week 2 success signal: EX > 50% on BIRD-mini with Sonnet 4.6.

---

## Suggested first prompt for Claude in this worktree

> Read `../nlsql-mcp-server-npm/v1_plan.md` and `../nlsql-mcp-server-npm/v0_proposal.md` for context, then read `analytics_bird/tools/sql.py` and `analytics_bird/tracing/jsonl.py` for what's already built. Your goal: build the Claude Agent SDK adapter for week 2 — wrap `analytics_bird/tools/sql.py` as an MCP server, then write `analytics_bird/adapters/claude.py` to run BIRD-mini (50 questions) with `claude-sonnet-4-6`. Start by writing the MCP server stub, smoke-test it stdio→stdio, then add the SDK runner. Don't touch the BIRD scorer — that work is happening in a separate worktree.

---

## Merge back

When this branch is ready:

```bash
# From this worktree
git push -u origin week2-claude-adapter
gh pr create --base main

# Or from the driver worktree
git -C /Users/ragebait.ai/nl_sql/nlsql-mcp-server-npm merge week2-claude-adapter
```

When done with the worktree:

```bash
git -C /Users/ragebait.ai/nl_sql/nlsql-mcp-server-npm worktree remove ../nlsql-mcp-server-npm-week2
```

---

## Don't do here

- The BIRD scorer is being hardened in the `eval-hardening` worktree. Leave `analytics_bird/bird/score.py` alone.
- No framework extraction (`kit/`). v1 is one deployment only — see `v0_critique.md`.
- No OpenAI Agents or Gemini ADK adapters yet. Those land in week 4 after the Claude path works.

# analytics_bird

v1 deployment per `../v1_plan.md`. Benchmarks an LLM agent on the BIRD dev set.

## Layout

```
analytics_bird/
├── tools/        6 SQL primitives (connect, list, describe, sample, execute, validate)
├── tracing/      JSONL trace writer
├── bird/         dataset download + iterator + scoring
├── adapters/     per-SDK runners (claude, openai, gemini) — added wk 2/4
├── eval/         EX + VES scoring, replay
├── prompts/      system prompts under test
├── runs/         JSONL traces (gitignored)
└── smoke_test.py week-1 smoke (no model required)
```

## Day-1 smoke

```bash
pip install -e .
python smoke_test.py
```

Builds a tiny synthetic SQLite DB, exercises all 6 tools, writes a trace under `runs/smoke/`, verifies read-only enforcement blocks `DROP`/`DELETE`.

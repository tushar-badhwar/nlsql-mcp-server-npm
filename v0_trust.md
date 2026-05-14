# Trust Spine — Design

The trust spine is the platform's defensible value. It is on-by-default, not opt-in. A deployment author declares trust policy in YAML; the runtime enforces it.

## The five primitives

```
kit/core/
├── trace.py        Trace dataclass; serialize/deserialize; replay engine
├── policy.py       Tool effect classification; approval gates
├── audit.py        Audit log stream; redaction; retention
├── eval.py         Eval runner; scoring; online sampling hooks
└── drift.py        Scheduled re-eval; degradation detection
```

These are siblings to the agent loop, not bolt-ons. Every agent turn passes through trace+policy+audit. There is no fast path.

## 1. Trace + replay

**Trace = the deterministic record of a run.** Every agent execution produces one. Format is JSONL; one file per run; stored under `runs/<deployment>/<yyyy-mm-dd>/<run_id>.jsonl`.

A trace record per turn:

```json
{
  "run_id": "01HX3T...",
  "turn": 4,
  "ts": "2026-05-13T14:22:01Z",
  "kit_version": "0.3.1",
  "deployment": "acme_analytics",
  "model": {"provider": "anthropic", "name": "claude-opus-4-7", "temperature": 0.0},
  "input": {"role": "user", "content": "..."},
  "system_prompt_hash": "sha256:...",
  "tool_calls": [{"name": "execute_sql", "args": {...}, "effect": "read", "result_hash": "sha256:..."}],
  "model_output": "...",
  "tokens": {"in": 1240, "out": 312},
  "latency_ms": 1820
}
```

**Replay:** `kit replay <run_id> [--model X] [--at-turn N] [--with-tool-fixture]` re-executes the run from any turn, optionally swapping model, prompt, or tool implementation. Replay uses recorded tool *result hashes* by default (deterministic), or re-executes tools against current state (live).

This is the single most important thing the trust spine does. "Why did it answer X on Tuesday?" stops being a debate and becomes a `kit replay`.

**Caveat:** non-deterministic model APIs (no seed support, or hosted with internal nondeterminism) make perfect replay impossible. The trace records what the model *did*; replay shows what the model *would do now*. Document this loudly.

## 2. Policy + side-effect classification

Every tool declares an effect at registration time:

```python
@tool(effect="read")
def list_tables(connection_id: str) -> list[str]: ...

@tool(effect="write")
def post_slack_message(channel: str, text: str) -> str: ...

@tool(effect="external", allowlist=["api.acme.com"])
def fetch(url: str) -> str: ...
```

Effects: `read` | `write` | `mutate` | `external`. The policy engine evaluates each tool call against the deployment's policy:

```yaml
trust:
  policy:
    default: deny_writes        # write/mutate require approval
    overrides:
      - tool: execute_sql
        when: args.sql matches "^\\s*(SELECT|EXPLAIN|WITH)"
        effect: allow            # read-only SQL auto-allowed
      - tool: post_slack_message
        when: args.channel == "#agent-approvals"
        effect: allow            # approval-channel post is OK
```

Policy decisions: `allow` | `require_approval` | `deny`. Approval is a pluggable handler:
- Dev: stdout prompt (`Approve [y/N]?`)
- Prod: Slack DM, Linear ticket, email, webhook
- Test: auto-allow with annotation

Default for production deployments is `deny_writes`. Force the deployment author to explicitly enable mutations.

Use **OPA / Cedar / Rego** for non-trivial policies. Don't invent a policy language.

## 3. Audit log

Distinct from trace. Trace is "what happened"; audit is "what was sent where, by whom, and what was retained."

```json
{
  "ts": "2026-05-13T14:22:01Z",
  "run_id": "01HX3T...",
  "actor": "user:badhwar.tushar@gmail.com",
  "model_provider": "anthropic",
  "data_sent_class": ["pii_email", "internal_sql"],
  "data_redacted": ["customer_phone", "ssn"],
  "retention_class": "90d",
  "residency": "us-east-1"
}
```

Backends: file, stdout, S3, Splunk, Datadog. PII redaction pass runs before write — configurable redactor (regex defaults; Presidio for production).

Audit log retention is **separate** from trace retention. Customer compliance reviews care about audit, not trace. Audit logs are append-only; rotation is by policy.

## 4. Eval — as code, same path as production

`deployments/<name>/evals/` contains eval cases:

```python
from kit.eval import case, assert_sql_executes_to

@case(suite="bird_dev", id="acme_q1")
def test_top_revenue_customer():
    out = run_agent("Who is our top revenue customer last quarter?")
    assert_sql_executes_to(out.sql, expected_rows=[("Acme Corp", 1_240_000)])
```

`kit eval <deployment> [--suite bird_dev]` runs the suite, produces a scorecard. Assertions:
- `equals`, `contains`, `matches` — exact
- `schema` — JSON schema validation
- `judge(model="claude-opus-4-7")` — LLM-as-judge with rubric
- `sql_executes_to(rows)` — execution-based for SQL
- `policy_compliant` — policy decisions all pass

**Online sampling**: in production, `sample_rate: 0.05` writes 5% of runs to a review queue. `kit eval sample --since 24h --suite bird_dev` re-scores them. Human reviewer accepts/rejects → labels feed back into the suite.

CI: PR fails if eval score drops >2% vs main. Branch-vs-main diff scorecards.

The same trace format is used in production and in eval. There is no separate "test mode." This is what closes the offline-online gap.

## 5. Drift detection

Cron-driven (`kit drift`):
- Weekly: re-run full eval suite against current model + prompt + tools
- Compare scores to last week
- Alert on >X% degradation (default 2% per metric)
- Auto-bisect by diffing: model version, prompt hash, kit version, tool implementations

Drift detection is where you find out the model provider silently shipped a new checkpoint or your prompt edit two days ago regressed something. Without it, agents quietly degrade for weeks before someone notices.

## How a deployment opts in (deployment.yaml)

```yaml
trust:
  policy:
    default: deny_writes
    file: ./policy.rego                  # optional OPA
  evals:
    suite: ./evals/
    threshold: 0.85                       # CI fails below this
    sample_rate: 0.05                     # production sampling
  audit:
    backend: stdout                       # file | s3 | splunk | datadog
    redact: [email, phone, ssn]
    retention: 90d
    residency: us-east-1
  approval:
    backend: slack
    channel: "#agent-approvals"
    timeout: 5m                           # auto-deny on timeout
  drift:
    schedule: "0 9 * * 1"                 # weekly Mon 9am
    threshold_pct: 2
    notify: slack#agent-drift
```

The trust block is the longest part of `deployment.yaml` on purpose. If you're not declaring this much trust policy, you don't have a production deployment.

## Implementation order (4 weeks, single dev)

1. **Week 1** — `trace.py`: dataclass, JSONL serialization, agent loop integration. `kit replay` for read-only tools. **Outcome:** every run is recorded; debugging gets 10x better immediately.
2. **Week 2** — `policy.py`: effect classification, default policy, stdout approval handler. **Outcome:** no agent can silently mutate state.
3. **Week 3** — `eval.py`: eval runner, scorecard, CI integration, online sampling. **Outcome:** PRs are gated on agent quality, not just unit tests.
4. **Week 4** — `audit.py` + `drift.py`: audit log with file backend, weekly drift cron. **Outcome:** compliance review answers + degradation alerts.

S3/Splunk audit backends, OPA integration, web UI for trace review — all defer until after one real customer engagement using the v1 trust spine.

## What this does for customers

The customer ask "how can I trust this" becomes a 4-part answer:

1. *"Every decision is recorded and replayable."* → trace + replay
2. *"The agent can't take actions you haven't approved."* → policy
3. *"We have a test suite that gates every change."* → eval
4. *"We log everything for your compliance team."* → audit

If you can demo all four in one 30-minute call, you close most enterprise FDE deals. If you can demo only the first two, you don't.

## What this does NOT do (and shouldn't)

- It does not make the agent *correct* — that's the model + tools + prompt.
- It does not eliminate hallucinations — judge evals catch some, not all.
- It does not provide formal guarantees — guardrails reduce risk, not zero it.
- It does not replace human review for high-stakes decisions — it makes review *tractable*.

Be honest with customers about each of these. Overselling trust is how you lose them on the second engagement.

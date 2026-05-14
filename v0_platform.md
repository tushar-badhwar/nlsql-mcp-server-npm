# FDE Platform Layer — Design

## The core problem
Two products in one repo:
- **A platform** (`kit`) — reusable agent runtime, model abstraction, tool/skill registry, MCP lifecycle, eval harness. Slow-moving, versioned, well-tested.
- **Deployments** — thin apps that compose platform pieces for a specific customer or use case (analytics-bird, acme-support, content-gen). Fast-moving, scrappy, often disposable.

These pull in opposite directions. The platform wants stability and conservative abstraction; deployments want to ship fast and bend the rules. Most FDE-style "framework" attempts fail because they conflate the two — either the platform calcifies and deployments fork it, or deployments leak into the platform and it becomes unmaintainable. Decide the boundary now.

## Recommended architecture

```
fde-agent-kit/
├── kit/                          ← library, semver-pinned, ~5k LoC ceiling
│   ├── core/
│   │   ├── agent.py              agent loop, model-agnostic
│   │   ├── model.py              unified LLM interface (Claude/OpenAI/Gemini)
│   │   ├── mcp.py                MCP server lifecycle (stdio + SSE)
│   │   ├── tools.py              tool registry, @tool decorator
│   │   ├── memory.py             optional state (kv, sqlite, postgres)
│   │   ├── secrets.py            env / AWS SM / GCP SM / 1Password resolver
│   │   └── trace.py              structured logging, run artifacts
│   ├── adapters/                 one runner per SDK (~100 LoC each)
│   │   ├── claude_sdk.py
│   │   ├── openai_agents.py
│   │   └── gemini_adk.py
│   ├── skills/                   opt-in capability packages
│   │   ├── sql/                  schema, execute, validate, sample
│   │   ├── slack/                post, reply, react
│   │   ├── ticketing/            Zendesk, Linear, Jira
│   │   ├── escalation/           human handoff
│   │   ├── brand_voice/          style/tone enforcer
│   │   └── web/                  fetch, search
│   └── eval/                     benchmark harness, scoring
├── deployments/                  one thin app per customer/use case
│   ├── analytics_bird/
│   │   ├── deployment.yaml       config: model, MCPs, skills, instructions
│   │   ├── instructions.md       system prompt
│   │   └── main.py               ≤50 LoC: kit.run("deployment.yaml")
│   ├── acme_support/
│   └── content_gen_demo/
└── templates/
    └── new_deployment/           cookiecutter for `kit init <name>`
```

**Rule of thumb:** if a new customer engagement needs you to edit `kit/`, the abstraction is wrong. They should only ever edit `deployments/their_name/`.

## The five seams — what you swap per deployment

1. **Model** — config key, resolved via `kit.core.model`. Strings like `"claude-opus-4-7"`, `"gpt-5"`, `"gemini-2.5-pro"`.
2. **Agent runtime (SDK)** — Claude Agent SDK vs OpenAI Agents SDK vs Gemini ADK. One adapter per SDK. Pick one *primary* per deployment; the others exist mainly for benchmarking.
3. **Skills** — declarative list. Each skill ships its own tools, optional MCP server, optional prompt fragment. Activated by being in the list, deactivated by removal. No code change.
4. **MCP servers (external)** — separate from skills. Skills are *yours*; MCP servers may be third-party (a Snowflake MCP, a GitHub MCP). Config block per server with launch command + env.
5. **Instructions** — `instructions.md` per deployment is the system prompt. Plain markdown, not template hell.

Example `deployment.yaml`:

```yaml
name: acme_support
runtime: claude_sdk
model: claude-sonnet-4-6
instructions: ./instructions.md
skills:
  - sql:
      profile: acme_warehouse
  - ticketing:
      provider: zendesk
  - escalation:
      slack_channel: "#support-oncall"
  - brand_voice:
      style_guide: ./acme_style.md
mcp_servers:
  - name: snowflake
    command: uvx snowflake-mcp
    env:
      SNOWFLAKE_ACCOUNT: ${secret:snowflake/account}
secrets:
  provider: aws_sm
  prefix: /acme/prod/agent/
memory:
  backend: sqlite
  path: ./state.db
```

That's the entire deployment surface. A new customer engagement is: clone `deployments/template/`, edit yaml, edit `instructions.md`, ship.

## What a skill actually contains

```
kit/skills/sql/
├── __init__.py        register(config) → SkillBundle
├── tools.py           @tool functions
├── prompt_fragment.md prepended to instructions when active (optional)
├── mcp.py             optional: launches an MCP server for the skill
└── tests/
```

Skills take config (`profile: acme_warehouse`) — they don't get forked per customer. If you find yourself wanting `sql_v2_for_acme`, that's a sign the config surface of `sql` is wrong.

## How replicability works in practice

New analytics engagement at Acme:
1. `kit init acme_analytics` → scaffolds `deployments/acme_analytics/`
2. Edit `deployment.yaml`: model, set `sql` skill with `acme_warehouse` profile, add Snowflake MCP
3. Edit `instructions.md` for Acme domain context
4. Add `secrets/` mapping (creds resolved at runtime, not stored)
5. `kit run acme_analytics` → tested locally
6. `kit deploy acme_analytics --target docker` → containerized

Switching the same deployment to support instead of analytics: edit yaml, swap `sql` for `ticketing + escalation + brand_voice`, swap instructions. Same `kit run`, same observability, same eval harness.

## Tensions to resolve up front

**Tension 1 — Benchmark reproducibility vs platform evolution.** If `kit` ships v1.4 with a different agent loop, your BIRD numbers from v1.2 aren't comparable. Fix: pin `kit==x.y.z` in every benchmark run; record the version in the result row.

**Tension 2 — Multi-SDK abstraction is expensive.** Every SDK has its own tool-call format, streaming model, memory abstraction. Truly abstracting over all three drives you toward LangChain. Pragmatic stance: pick **Claude Agent SDK as the production runtime**; treat OpenAI Agents + Gemini ADK as *benchmark probes* in `kit.eval/`, not as first-class production paths. Re-evaluate after the BIRD results come in.

**Tension 3 — Skill reuse vs domain leakage.** "Almost the same Slack skill but Acme needs one tweak." Pressure pushes you toward `slack_acme.py`. Resist. Either the parent skill grows a config knob, or Acme writes a 30-line custom tool in `deployments/acme/custom_tools.py`. Forked skills are forbidden.

**Tension 4 — YAML always grows into a bad programming language.** Cap `deployment.yaml` at ~40 lines. When something doesn't fit, it goes in `deployments/<name>/main.py` as Python. Config for declarative wiring; Python for everything else.

## Pitfalls

- **Don't build LangChain-but-mine.** The library earns its keep only if it stays small (≤5k LoC), avoids abstracting things that don't vary, and lets deployments drop to raw SDK calls when needed.
- **Don't make the agent loop pluggable.** There is one loop in `kit.core.agent`. If a deployment needs a different one, it writes its own `main.py` that doesn't call `kit.run`.
- **Don't ship memory as a default-on feature.** Default to stateless; opt in to memory explicitly.
- **Don't bury secrets in deployment files.** Resolve at runtime through `kit.core.secrets`.
- **Don't allow circular skill dependencies.** `sql` cannot import `slack`. Skills are siblings.
- **Don't skip test scaffolding in `kit init`.** Every new deployment gets a smoke test by default.

## How this composes with v0_proposal.md

The analytics SOTA work becomes `deployments/analytics_bird/` — one specific configuration of the platform. The six MCP primitives live in `kit/skills/sql/`. The three SDK adapters become `kit/adapters/`. The benchmark harness becomes `kit/eval/`.

Order matters:
- If you build `kit` first and force analytics to fit, you risk over-engineering.
- If you build analytics first and extract `kit` from it, you risk under-abstracting.
- Right move: build analytics as a *deliberately throwaway* deployment, then extract `kit` from it after the second use case lands. Two data points beat one.

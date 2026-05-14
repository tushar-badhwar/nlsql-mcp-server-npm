# Critique — "CLI for FDEs worldwide + trust"

## The scope just expanded 100x — be honest about which product

Going from "my reusable kit" to "global FDE developer tool" in one paragraph means two different products with different physics:

| Aspect | Personal kit | Public OSS tool |
|---|---|---|
| Users | You + 0-3 teammates | Strangers in stacks you've never seen |
| Backwards compat | Break freely | Sacred |
| Docs | None / sloppy | Carry the product |
| Maintenance | Hours/week | A second full-time job |
| Architecture | Whatever ships | Defendable against critique |
| Failure mode | You're inconvenienced | Strangers blame you on Twitter |

The platform doc is sized for the personal kit. Sizing for "global FDE tool" rewrites half of it. **Pick one to ship first.** Build the personal kit, use it on 3-5 real engagements, *then* decide whether to OSS it. Most "FDE tools for the world" are products in search of users — built by someone whose engagement-context felt universal but wasn't.

## What's the moat against the existing field?

The space is dense and not friendly:
- **LangChain / LangGraph** — mindshare, ecosystem, momentum (and many haters)
- **CrewAI** — multi-agent niche
- **Pydantic AI** — type-safe Python angle
- **Mastra** — TS-first, dev ergonomics
- **Vercel AI SDK** — frontend-adjacent
- **AutoGen** — Microsoft research lineage
- **Genkit** — Google's bet
- **Letta** (was MemGPT) — memory niche
- **Llama-Stack / Llama-Index** — Meta's stack
- **Dust** — managed product, not OSS
- **e2b** — sandbox runtime
- **Stagehand / Browserbase** — browser agents

"FDE-shaped" *could* be a real position — FDE work has needs general frameworks underserve: rapid customer-specific config, per-customer credential isolation, on-prem/air-gapped friendly, clone-and-modify ergonomics, audit trails customers actually accept. But if that's the moat, **everything must serve FDE workflow specifically**, not just be "another framework with FDE in the name."

If you can't articulate the moat in one sentence — *"the tool that wins when you're embedded at a customer for 90 days and need to ship something they can trust"* — then there isn't one yet, and you're going to lose to LangChain's gravitational pull.

## "Trust" is the actual product. Eval harness is one layer of five.

"How can I trust this?" is the most important question a customer asks, and most frameworks fumble it because they answer with "we have evals." Real trust is five layers, all of which have to exist:

1. **Offline eval (pre-deploy)** — golden sets, regression tests, eval-as-code in the repo. PR doesn't merge without eval pass. *Most frameworks have this; table stakes.*
2. **Online sampling + human review** — sample N% of production runs into a review queue, human grades them. Drift detection compares this week's grades to last week's. *Few frameworks have this; it's where trust actually lives.*
3. **Guardrails (runtime)** — pre-call validation (schema, PII), post-call validation (response shape, citation presence), action gates (any tool mutating customer data requires explicit approval). *Many frameworks gesture at this; few enforce it.*
4. **Trace + replay** — every run produces a deterministic trace, replayable with a different model/prompt/tool implementation. Customer says "why did it do that on Tuesday" → you point them at the trace and let them re-run it. *The single most underrated trust mechanism.*
5. **Audit log + compliance** — who saw what data, what was sent to which model provider, what was retained, what was redacted. *Hardest to retrofit; designs that ignore it die in legal review.*

If you ship `kit eval` and stop, you've solved 20% of trust. If you build all five and make them on by default, you've built the product. **The eval harness shouldn't be a module; the trust story should be the platform's spine.**

## Senior-engineer pushback

- **"FDEs worldwide" is unvalidated.** Talk to 10 FDEs at Palantir, Scale, OpenAI, Glean, Anthropic *before* writing a line of `kit/core/`. The pain you feel may be specific to your engagements, your stack, your customers.
- **You haven't shipped v1 of any of this.** You're designing v3 of a product that doesn't exist. Order: analytics deployment end-to-end → real engagement → extract `kit` after second use case → OSS after third.
- **CLI is the wrong primary interface long-term.** Builders are fine with CLI. Customer stakeholders reviewing trust aren't going to `kit trace --run-id 4f3a` — they want a UI. Decide: builder tool (CLI fine) or trust product (needs UI eventually).
- **Versioning will eat you alive.** Deployments scattered across customer environments + new `kit` versions = silent breakage. Either (a) bulletproof backwards compat day 1, or (b) vendor `kit` into each deployment. No third option.
- **Don't invent standards.** Tracing → OpenTelemetry. Policies → OPA or Cedar. Tool schemas → JSON Schema + MCP. Auth → OIDC. Every invented standard is an adoption tax.
- **Local-first vs cloud-managed is a fork, not a flag.** FDE work is often air-gapped or on-prem. Local-first is right. "Managed eval dashboard" pulls the opposite way. Can't ship both well in v1.
- **OSS sustainability isn't optional.** Single-maintainer OSS dies within 18 months. When you're at a customer 12 weeks, who maintains `kit`? Cap scope hard, build a commercial layer, or get a co-maintainer — before launch.
- **"Deploy agentic systems everywhere" is too broad.** Browser, support, analytics, creative — different memory, latency, observability. Truly universal → LangChain (too thin, no opinion). Constrain scope: e.g., *"tool-using LLM agents over structured customer data with audit requirements."*

## Recommendation

Don't build `kit` as a public CLI yet. Build the **trust spine** first, in a private repo, as part of the analytics deployment:

1. Trace + replay infrastructure — every run deterministic, replayable.
2. Eval-as-code with online sampling hooks — same code path for offline eval and production.
3. Tool side-effect classification + policy gate — writes require approval.
4. Audit log as a first-class stream — retention configurable.
5. One working deployment using all of the above.

If after one customer engagement the abstractions still feel right, extract `kit/` and consider CLI/OSS. If they don't, you've saved six months building the wrong framework.

The instinct "this should be a CLI tool for FDEs worldwide" is correct in direction but premature in timing. The trust story is the differentiator; build that first, hard, with real users, and the CLI packaging is a six-week project after the abstractions are validated. Reversing the order is how 90% of agent frameworks end up unused.

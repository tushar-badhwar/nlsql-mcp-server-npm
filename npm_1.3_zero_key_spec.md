# Spec — Zero-key default (folds into 1.3.0, unpublished)

## Motivation

When the MCP client is itself a capable model (Claude Desktop), the
server-side `natural_language_to_sql` / `analyze_schema` tools are redundant:
they spend an OpenAI call + CrewAI run to do something the client model does
better itself using the key-free primitives (connect → inspect schema → write
SQL → execute). Exposing the OpenAI-backed tools by default forces an API-key
requirement onto the headline path for no benefit, and invites the client to
pick the worse, key-requiring tool.

Goal: the default experience is **"Claude + your DB, zero keys."** The
OpenAI-backed tools become opt-in, surfaced only when the operator explicitly
provides a key.

## Behavior change

The gating rule, applied at tool-discovery time:

- **`OPENAI_API_KEY` absent** → the server advertises only the key-free tools:
  `connect_database`, `connect_sample_database`, `get_database_info`,
  `get_table_sample`, `validate_sql_query`, `execute_sql_query`,
  `get_connection_status`, `disconnect_database`. The AI tools
  (`natural_language_to_sql`, `analyze_schema`) are **not listed**.
- **`OPENAI_API_KEY` present** → all tools advertised, including the AI ones
  (current behavior).

Rationale for auto-gating on key presence (vs. a separate enable flag): zero
config, and the signal ("do you have a key?") already perfectly predicts
"can the AI tools work?". One escape hatch only if a real need appears later;
do not add it preemptively.

## Implementation points

1. **Tool discovery filter.** *Prerequisite to verify first:* confirm whether
   `server.py` implements a `tools/list` JSON-RPC handler. The current
   `handle_request` routes `initialize`, `initialized`, `tools/call`,
   `prompts/list`, `prompts/get` — `tools/list` may be missing entirely. If
   missing, add it (clients need it for discovery); if present, add the
   filter. The filter: when `not os.getenv("OPENAI_API_KEY")`, drop
   `natural_language_to_sql` and `analyze_schema` from the returned list.
2. **Prompts filter.** `prompts/list` currently advertises a `generate_sql`
   prompt that points at `natural_language_to_sql`. Gate that prompt behind
   the same key check so we never advertise a prompt that uses a hidden tool.
   Keep `analyze_database` only if it can run key-free; otherwise gate it too.
3. **`tools.py`.** No change to `_setup_tools()` (still defines all tools);
   the filtering is a discovery-time concern, not a registration one. Calling
   a gated tool directly still returns the existing clean lazy-crew error, so
   a stale client that cached the full list degrades gracefully.
4. **README.** Update the tools table note: AI-marked tools "appear only when
   `OPENAI_API_KEY` is set." Make the zero-key Claude-Desktop flow the
   documented default; move the keyed path to an "Optional: server-side AI"
   subsection.
5. **No version bump.** 1.3.0 is committed but unpublished, so this folds in.

## Edge cases / compatibility

- **Key users unaffected:** setting `OPENAI_API_KEY` yields today's full tool
  set — no regression.
- **Env changes mid-session:** tool list reflects env at discovery time; a
  client that caches across an env change may be stale. Acceptable; the
  direct-call error path covers it.
- **`analyze_schema` vs `get_database_info`:** hiding `analyze_schema`
  key-free is fine — `get_database_info` already covers schema inspection
  without a key.

## Out of scope

- Removing the AI tools entirely (that's the `analytics_bird` track's thesis;
  here we only make them opt-in).
- Any change to the CrewAI pipeline, pin, or venv setup.
- An explicit enable/disable flag beyond key presence.

## Acceptance criteria

- With no `OPENAI_API_KEY`: an MCP client lists exactly the 8 key-free tools;
  `natural_language_to_sql` / `analyze_schema` absent; no `generate_sql`
  prompt; connect → inspect → write SQL → execute works end-to-end with zero
  keys from Claude Desktop.
- With `OPENAI_API_KEY` set: all 10 tools listed; `natural_language_to_sql`
  works as today.
- Calling a gated tool directly (stale client) returns a clear error, not a
  crash.
- README documents zero-key as the default path.

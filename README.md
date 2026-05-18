# NLSQL MCP Server (Node.js)

[![npm version](https://img.shields.io/npm/v/nlsql-mcp-server.svg)](https://www.npmjs.com/package/nlsql-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/nlsql-mcp-server.svg)](https://www.npmjs.com/package/nlsql-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Node.js package that runs an MCP (Model Context Protocol) server for converting
natural language questions into SQL using an AI multi-agent system. It works with
SQLite, PostgreSQL, and MySQL, and plugs into any MCP client (Claude Desktop, etc.).

## Requirements

- **Node.js 14+**
- **Python 3.10, 3.11, 3.12, or 3.13** — *not 3.14*. The underlying CrewAI
  engine does not yet support Python 3.14. The installer auto-detects a
  compatible interpreter; if you only have 3.14 it will tell you exactly what
  to install.
- **OpenAI API key** — **only** for the AI features (`natural_language_to_sql`,
  `analyze_schema`). Connecting to a database and running/validating SQL needs
  no key.

## Install

```bash
npm install -g nlsql-mcp-server
```

This is the recommended first step **before** wiring it into any MCP client
(see [Claude Desktop](#use-with-claude-desktop)). During install, a `postinstall`
step:

1. Probes for a compatible Python (`python3.13` → `3.12` → `3.11` → `3.10`).
2. Builds a **dedicated virtualenv inside the package** and installs the Python
   dependencies into it (a slim runtime set — a few minutes, one time). This is
   isolated; it does not touch your system Python and is not affected by PEP 668
   ("externally-managed-environment").
3. On success: prints `Setup complete`.

If **no compatible Python is found**, the install still completes but prints
instructions, e.g.:

```
macOS:   brew install python@3.13
Ubuntu:  sudo apt install python3.13 python3.13-venv
Windows: winget install Python.Python.3.13
```

Install one, then run:

```bash
npx nlsql-mcp-server install-deps   # (re)builds the virtualenv
```

Verify everything is ready:

```bash
nlsql-mcp-server test
```

You should see the virtualenv and Python dependency checks pass. (The OpenAI
key check will show ❌ until you set `OPENAI_API_KEY`; that only affects the AI
features.)

## How to use it end-to-end

### 1. Install locally and build the environment

```bash
npm install -g nlsql-mcp-server
nlsql-mcp-server test          # confirms the venv + deps are ready
```

### 2. (Optional) Set an OpenAI key for the AI features

Only needed for natural-language → SQL and AI schema analysis:

```bash
export OPENAI_API_KEY="sk-your-key"
```

### 3. Connect to a database

The server exposes tools to connect to your own database or a built-in sample:

- **Your database:** `connect_database` with `db_type` = `sqlite` |
  `postgresql` | `mysql` plus the relevant connection fields.
- **Sample database:** `connect_sample_database` connects to an NBA dataset
  (30 teams, 15 tables). The ~52 MB SQLite file is **downloaded on first use**
  (it is not bundled in the package), then cached locally.

Connecting, inspecting schema, sampling rows, validating and executing SQL all
work **without an API key**.

### 4. Use it from Claude Desktop (MCP client)

Once installed and warmed up (steps 1–2), point Claude Desktop at it and
interact in natural language. Setup below.

## Use with Claude Desktop

> **Important ordering:** install and warm the environment *first*
> (`npm install -g nlsql-mcp-server` and `nlsql-mcp-server test`), *then* add
> the config below. The first-time Python environment build takes a few
> minutes and cannot complete inside an MCP client's startup handshake — if
> you wire it in before the virtualenv exists, the server exits immediately
> with a message in the MCP client logs telling you to run
> `npx nlsql-mcp-server install-deps` once in a terminal.

### 1. Find your Claude Desktop config file

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

### 2. Add the server

```json
{
  "mcpServers": {
    "nlsql": {
      "command": "npx",
      "args": ["nlsql-mcp-server", "start"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

The `env` block is optional — omit `OPENAI_API_KEY` if you only need
connect/inspect/validate/execute (no AI). Add it to enable
`natural_language_to_sql`.

### 3. Restart Claude Desktop

Fully quit and reopen. Then try:

```
Connect to the sample database and show me what tables are available.
```

```
How many teams are in the NBA?
```

## Available tools

| Tool | Needs OpenAI key? | Description |
|------|:---:|-------------|
| `connect_database` | – | Connect to SQLite, PostgreSQL, or MySQL |
| `connect_sample_database` | – | Connect to the NBA sample DB (downloaded on first use) |
| `get_database_info` | – | Tables, columns, relationships |
| `get_table_sample` | – | Sample rows from a table |
| `validate_sql_query` | – | Validate SQL syntax |
| `execute_sql_query` | – | Execute SQL safely |
| `get_connection_status` | – | Current connection status |
| `disconnect_database` | – | Disconnect |
| `natural_language_to_sql` | ✅ | Convert a question to SQL using AI |
| `analyze_schema` | ✅ | AI-powered schema analysis |

## CLI

```bash
nlsql-mcp-server start            # start the MCP server (stdio)
nlsql-mcp-server start --debug    # start with verbose logging
nlsql-mcp-server test             # check venv + deps + key
nlsql-mcp-server install-deps     # (re)build the Python virtualenv
nlsql-mcp-server config           # print a Claude Desktop config snippet
nlsql-mcp-server --help
```

## Troubleshooting

**`No CrewAI-compatible Python found (need 3.10–3.13)`**
Your default Python is 3.14 (or none in range). Install a compatible one
(`brew install python@3.13`, `apt install python3.13 python3.13-venv`, or
`winget install Python.Python.3.13`), then run
`npx nlsql-mcp-server install-deps`.

**Claude Desktop shows the server failing immediately**
Check the MCP client logs. If it says the Python environment is not built,
run `npx nlsql-mcp-server install-deps` once in a terminal, wait for it to
finish, then restart Claude Desktop. This happens when the server was wired
in before the one-time environment build completed.

**`natural_language_to_sql` returns a credentials error**
`OPENAI_API_KEY` is not set in the environment the server runs in. For Claude
Desktop, put it in the `env` block of the config. Other tools work without it.

**Reinstall the Python environment from scratch**

```bash
npx nlsql-mcp-server install-deps
```

This deletes and rebuilds the package virtualenv.

## How it works

```
MCP client (Claude Desktop)
        │  JSON-RPC over stdio
        ▼
Node wrapper (index.js)  ──spawns──►  Python MCP server (package virtualenv)
                                          │
                                          ▼
                                   nl2sql + CrewAI agents
                                   SQLite / PostgreSQL / MySQL
```

The Node layer manages the isolated Python virtualenv and process; the Python
layer runs the MCP protocol and the SQL/AI logic. The CrewAI engine is pinned
to the 0.x line it was built against, and its console/telemetry output is kept
off the protocol channel.

## Testing

```bash
npm test                  # Node wrapper unit tests
nlsql-mcp-server test     # installation / environment checks
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm test`
5. Submit a pull request

## License

MIT — see [LICENSE](LICENSE).

## Credits

- **Original Python server:** [NLSQL MCP Server](https://github.com/tushar-badhwar/nlsql-mcp-server)
- **Underlying application:** [nl2sql](https://github.com/tushar-badhwar/nl2sql)
- **Built with:** [Model Context Protocol](https://modelcontextprotocol.io/), [CrewAI](https://crewai.com/), [OpenAI](https://openai.com/)

## Support

- **Issues:** [GitHub Issues](https://github.com/tushar-badhwar/nlsql-mcp-server/issues)
- **Repository:** [GitHub](https://github.com/tushar-badhwar/nlsql-mcp-server)

---

**Made by [Tushar Badhwar](https://github.com/tushar-badhwar)**

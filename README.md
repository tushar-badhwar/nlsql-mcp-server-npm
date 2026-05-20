# NLSQL MCP Server (Node.js)

[![npm version](https://img.shields.io/npm/v/nlsql-mcp-server.svg)](https://www.npmjs.com/package/nlsql-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/nlsql-mcp-server.svg)](https://www.npmjs.com/package/nlsql-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Node.js package that runs an MCP (Model Context Protocol) server for talking
to your databases in natural language. Works with SQLite, PostgreSQL, and MySQL,
and plugs into any MCP client (Claude Desktop, etc.).

## Quick start

```bash
# 1. Install. Auto-builds an isolated Python environment (~3 min, one time).
npm install -g nlsql-mcp-server

# 2. Verify it's ready.
nlsql-mcp-server test
```

Then add this to your Claude Desktop config file
(`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows,
`~/.config/Claude/claude_desktop_config.json` on Linux):

```json
{
  "mcpServers": {
    "nlsql": { "command": "nlsql-mcp-server", "args": ["start"] }
  }
}
```

Fully restart Claude Desktop, then ask:

> Connect to the sample database and tell me how many teams are in the NBA.

That's it — **no OpenAI key required**. Claude reads the schema with the
key-free tools and writes the SQL itself. (First call only, this triggers a
one-off ~52 MB sample-DB download.)

## Requirements

- **Node.js 14+**
- **Python 3.10, 3.11, 3.12, or 3.13** — *not 3.14*. The underlying CrewAI
  engine doesn't support 3.14 yet. The installer auto-detects a compatible
  interpreter; if none is found it prints exact install instructions for
  your OS.
- **OpenAI API key** — **optional**, only for the server-side AI tools
  (`natural_language_to_sql`, `analyze_schema`). With Claude Desktop you don't
  need one — Claude handles the natural-language part itself.

## Install — what happens

`npm install -g nlsql-mcp-server` runs a `postinstall` script that:

1. Probes for a compatible Python (`python3.13` → `3.12` → `3.11` → `3.10`).
2. Builds a **dedicated virtualenv inside the package** and installs the slim
   runtime dependency set. Isolated from your system Python; not affected by
   PEP 668.
3. Prints `Setup complete`.

If no compatible Python is found, the install still finishes but prints
recovery instructions:

```
macOS:   brew install python@3.13
Ubuntu:  sudo apt install python3.13 python3.13-venv
Windows: winget install Python.Python.3.13
```

Install one of those, then run:

```bash
nlsql-mcp-server install-deps   # (re)builds the virtualenv
```

## Use with Claude Desktop

**Important:** run `npm install -g nlsql-mcp-server` and `nlsql-mcp-server test`
**before** adding the config below. The one-time Python environment build takes
a few minutes and can't finish inside an MCP client's startup handshake — if
you wire it in first, the server exits immediately telling you (in the Claude
Desktop logs) to run `nlsql-mcp-server install-deps` once in a terminal.

The minimal config is in [Quick start](#quick-start) — no key needed. To enable
the **optional server-side AI tools** (CrewAI/OpenAI does the NL→SQL inside the
server instead of letting Claude do it), add an `OPENAI_API_KEY`:

```json
{
  "mcpServers": {
    "nlsql": {
      "command": "nlsql-mcp-server",
      "args": ["start"],
      "env": { "OPENAI_API_KEY": "sk-your-key-here" }
    }
  }
}
```

### What you can ask Claude

```
Connect to the sample database and show me what tables are available.
```

```
How many teams from California are in the NBA?
```

```
Connect to my Postgres at postgresql://user:pass@host:5432/db and tell me
about the schema.
```

Claude reads the schema with the key-free tools, writes the SQL, runs it, and
answers — no OpenAI account in the loop unless you added a key.

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

The two ✅ tools are advertised **only when `OPENAI_API_KEY` is set**. With no
key, only the 8 key-free tools are exposed — a capable MCP client like Claude
Desktop handles natural-language→SQL itself using those primitives.

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
`nlsql-mcp-server install-deps`.

**Claude Desktop shows the server failing immediately**
Check the MCP client logs. If it says the Python environment isn't built,
run `nlsql-mcp-server install-deps` once in a terminal, wait for it to finish,
then fully restart Claude Desktop. This happens when the server was wired in
before the one-time environment build completed.

**`natural_language_to_sql` returns a credentials error**
`OPENAI_API_KEY` isn't set in the environment the server runs in. For Claude
Desktop, put it in the `env` block of the config. The 8 key-free tools work
without it.

**Reinstall the Python environment from scratch**

```bash
nlsql-mcp-server install-deps
```

Deletes and rebuilds the package virtualenv.

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
layer runs the MCP protocol and the SQL/AI logic.

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

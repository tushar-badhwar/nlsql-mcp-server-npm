# NLSQL MCP Server (Node.js)

[![npm version](https://img.shields.io/npm/v/nlsql-mcp-server.svg)](https://www.npmjs.com/package/nlsql-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/nlsql-mcp-server.svg)](https://www.npmjs.com/package/nlsql-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready Node.js package that provides an MCP (Model Context Protocol) server for converting natural language questions into SQL queries using AI-powered multi-agent systems.

## Quick Start

```bash
# Install globally
npm install -g nlsql-mcp-server

# Start the server
nlsql-mcp-server start

# Or run directly with npx
npx nlsql-mcp-server start
```

## Features

- **AI-Powered**: Converts natural language to SQL using OpenAI and CrewAI
- **Multi-Database**: Supports SQLite, PostgreSQL, and MySQL
- **Smart Analysis**: AI-powered database schema analysis
- **Easy Installation**: One-command setup with automatic Python dependency management
- **MCP Protocol**: Full JSON-RPC implementation compatible with Claude Desktop and other MCP clients
- **Safe Execution**: Query validation and configurable limits
- **Sample Data**: Built-in NBA database for testing
- **Production Ready**: Comprehensive error handling and logging

## Prerequisites

- **Node.js 14+**: JavaScript runtime
- **Python 3.8+**: For the underlying MCP server
- **OpenAI API Key**: For natural language processing

## Installation

### Global Installation (Recommended)

```bash
npm install -g nlsql-mcp-server
```

### Local Installation

```bash
npm install nlsql-mcp-server
```

The package will automatically:
1. Detect your Python installation
2. Install required Python dependencies
3. Set up the NLSQL MCP server
4. Verify the installation

## Configuration

### Environment Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your_api_key_here"

# Or create a .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### Claude Desktop Setup (Step-by-Step)

#### Step 1: Install the Package
```bash
npm install -g nlsql-mcp-server
```

#### Step 2: Get Your OpenAI API Key
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)

#### Step 3: Find Your Claude Desktop Config File

**On Windows:**
1. Press `Windows + R`
2. Type `%APPDATA%\Claude`
3. Look for `claude_desktop_config.json`

**On Mac:**
1. Open Finder
2. Press `Cmd + Shift + G`
3. Type `~/Library/Application Support/Claude`
4. Look for `claude_desktop_config.json`

**On Linux:**
1. Open file manager
2. Go to `~/.config/Claude`
3. Look for `claude_desktop_config.json`

#### Step 4: Edit the Config File

**If the file exists:** Open it and add the nlsql configuration to the existing `mcpServers` section.

**If the file doesn't exist:** Create a new file called `claude_desktop_config.json` with this content:

```json
{
  "mcpServers": {
    "nlsql": {
      "command": "npx",
      "args": ["nlsql-mcp-server", "start"],
      "env": {
        "OPENAI_API_KEY": "sk-your-actual-api-key-here"
      }
    }
  }
}
```

**Important:** Replace `sk-your-actual-api-key-here` with your real OpenAI API key!

#### Step 5: Restart Claude Desktop
1. Completely close Claude Desktop
2. Open Claude Desktop again
3. The nlsql server should now be available

#### Step 6: Test It Works
In Claude Desktop, try asking:
```
"Connect to the sample database and show me what tables are available"
```

If it works, you'll see Claude connect to the NBA sample database!

## Usage

### Command Line Interface

```bash
# Start the MCP server
nlsql-mcp-server start

# Start with debug mode
nlsql-mcp-server start --debug

# Test the installation
nlsql-mcp-server test

# Install/reinstall Python dependencies
nlsql-mcp-server install-deps

# Generate Claude Desktop config
nlsql-mcp-server config

# Show help
nlsql-mcp-server --help
```

### Programmatic Usage

```javascript
const NLSQLMCPServer = require('nlsql-mcp-server');

const server = new NLSQLMCPServer({
    debug: true,
    pythonExecutable: 'python3',
    env: {
        OPENAI_API_KEY: 'your_key_here'
    }
});

await server.start();
```

## Available Tools

When running, the server provides these MCP tools:

| Tool | Description |
|------|-------------|
| `connect_database` | Connect to SQLite, PostgreSQL, or MySQL |
| `connect_sample_database` | Connect to built-in NBA sample database |
| `natural_language_to_sql` | Convert questions to SQL using AI |
| `execute_sql_query` | Execute SQL queries safely |
| `analyze_schema` | AI-powered database schema analysis |
| `get_database_info` | Get table and column information |
| `validate_sql_query` | Validate SQL syntax |
| `get_table_sample` | Get sample data from tables |
| `get_connection_status` | Check database connection status |
| `disconnect_database` | Disconnect from database |

## Examples

### Claude Desktop Usage

After setting up Claude Desktop integration, you can use natural language to interact with your databases:

```
Connect to my sample database and show me the schema
```

```
Convert this to SQL: "How many teams are in the NBA?"
```

```
Show me sample data from the team table
```

```
Analyze my database structure and suggest useful queries
```

### Sample Database

Test with the built-in NBA database (30 teams, 15 tables with players, games, stats):

```
Use the connect_sample_database tool
```

Then ask questions like:
- "How many teams are in the NBA?" → Returns: 30 teams
- "Show me sample data from the team table"
- "List teams from California"
- "Validate this SQL: SELECT COUNT(*) FROM team"

## Testing

```bash
# Test the Node.js wrapper
npm test

# Test the underlying Python server
nlsql-mcp-server test

# Test with sample database
nlsql-mcp-server start --debug
# Then use with Claude Desktop
```

## Troubleshooting

### Common Issues

#### "Python not found"
```bash
# Install Python 3.8+
# On Ubuntu/Debian:
sudo apt update && sudo apt install python3 python3-pip

# On macOS:
brew install python3

# On Windows:
# Download from python.org
```

#### "Failed to install Python dependencies"
```bash
# Manual installation
nlsql-mcp-server install-deps

# Or install manually
pip3 install mcp crewai sqlalchemy pandas openai python-dotenv psycopg2-binary pymysql cryptography
```

#### "OpenAI API key not found"
```bash
# Set environment variable
export OPENAI_API_KEY="your_key_here"

# Or use .env file
echo "OPENAI_API_KEY=your_key_here" > .env
```

#### "Server won't start"
```bash
# Debug mode for detailed logs
nlsql-mcp-server start --debug

# Test installation
nlsql-mcp-server test
```

### Debug Mode

Run with debug mode for detailed logging:

```bash
nlsql-mcp-server start --debug
```

### Log Files

Logs are written to:
- **Linux/macOS**: `~/.config/nlsql-mcp-server/logs/`
- **Windows**: `%APPDATA%\nlsql-mcp-server\logs\`

## Integration Examples

### VS Code with Continue.dev

Add to your Continue.dev configuration:

```json
{
  "mcpServers": {
    "nlsql": {
      "command": "npx",
      "args": ["nlsql-mcp-server", "start"]
    }
  }
}
```

### Custom Applications

```javascript
const { spawn } = require('child_process');

const mcpServer = spawn('npx', ['nlsql-mcp-server', 'start'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
        ...process.env,
        OPENAI_API_KEY: 'your_key_here'
    }
});

// Handle MCP protocol communication
mcpServer.stdout.on('data', handleMCPMessage);
mcpServer.stdin.write(JSON.stringify(mcpRequest));
```

## Performance

- **Startup Time**: ~2-3 seconds
- **Database Operations**: <1 second (connect, query, validate)
- **AI Processing**: 5-15 seconds (natural language to SQL, schema analysis)
- **Memory Usage**: ~100-200MB
- **Database Support**: SQLite, PostgreSQL, MySQL

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm test`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

- **Original Python Server**: [NLSQL MCP Server](https://github.com/tushar-badhwar/nlsql-mcp-server)
- **Underlying Application**: [nl2sql](https://github.com/tushar-badhwar/nl2sql)
- **Built with**: [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), [CrewAI](https://crewai.com/), [OpenAI](https://openai.com/)

## Support

- **Issues**: [GitHub Issues](https://github.com/tushar-badhwar/nlsql-mcp-server/issues)
- **Documentation**: [GitHub Repository](https://github.com/tushar-badhwar/nlsql-mcp-server)
- **Discussions**: [GitHub Discussions](https://github.com/tushar-badhwar/nlsql-mcp-server/discussions)

---

**Made by [Tushar Badhwar](https://github.com/tushar-badhwar)**
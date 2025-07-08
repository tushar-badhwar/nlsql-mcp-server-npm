# NLSQL MCP Server (Node.js)

[![npm version](https://badge.fury.io/js/nlsql-mcp-server.svg)](https://badge.fury.io/js/nlsql-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Node.js wrapper for the [NLSQL MCP Server](https://github.com/tushar-badhwar/nlsql-mcp-server) - Convert natural language questions into SQL queries using AI-powered multi-agent system.

## 🚀 Quick Start

```bash
# Install globally
npm install -g nlsql-mcp-server

# Start the server
nlsql-mcp-server start

# Or run directly with npx
npx nlsql-mcp-server start
```

## ✨ Features

- **🤖 AI-Powered**: Converts natural language to SQL using OpenAI and CrewAI
- **🔗 Multi-Database**: Supports SQLite, PostgreSQL, and MySQL
- **🧠 Smart Analysis**: AI-powered database schema analysis
- **⚡ Easy Installation**: One-command setup with automatic Python dependency management
- **🎯 MCP Protocol**: Compatible with Claude Desktop and other MCP clients
- **🛡️ Safe Execution**: Query validation and configurable limits
- **📊 Sample Data**: Built-in NBA database for testing

## 📋 Prerequisites

- **Node.js 14+**: JavaScript runtime
- **Python 3.8+**: For the underlying MCP server
- **OpenAI API Key**: For natural language processing

## 📦 Installation

### Global Installation (Recommended)

```bash
npm install -g nlsql-mcp-server
```

### Local Installation

```bash
npm install nlsql-mcp-server
```

The package will automatically:
1. ✅ Detect your Python installation
2. ✅ Install required Python dependencies
3. ✅ Set up the NLSQL MCP server
4. ✅ Verify the installation

## 🔧 Configuration

### Environment Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your_api_key_here"

# Or create a .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### Claude Desktop Integration

Generate configuration for Claude Desktop:

```bash
nlsql-mcp-server config
```

This will output the configuration to add to your Claude Desktop settings:

```json
{
  "mcpServers": {
    "nlsql": {
      "command": "npx",
      "args": ["nlsql-mcp-server", "start"],
      "env": {
        "OPENAI_API_KEY": "your_openai_api_key_here"
      }
    }
  }
}
```

## 🎯 Usage

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

## 🛠️ Available Tools

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

## 📝 Examples

### Claude Desktop Usage

After setting up Claude Desktop integration:

```
Connect to my database and show me the schema
```

```
Convert this to SQL: "How many customers bought products last month?"
```

```
Analyze my database structure and suggest useful queries
```

### Sample Database

Test with the built-in NBA database:

```
Use the connect_sample_database tool
```

Then ask questions like:
- "How many teams are in the NBA?"
- "List all players with 'James' in their name"
- "Which teams are from California?"

## 🧪 Testing

```bash
# Test the Node.js wrapper
npm test

# Test the underlying Python server
nlsql-mcp-server test

# Test with sample database
nlsql-mcp-server start --debug
# Then use with Claude Desktop
```

## 🚨 Troubleshooting

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

## 🔗 Integration Examples

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

## 📊 Performance

- **Startup Time**: ~2-3 seconds
- **Query Processing**: 2-10 seconds (depending on complexity)
- **Memory Usage**: ~100-200MB
- **Database Support**: SQLite, PostgreSQL, MySQL

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm test`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Credits

- **Original Python Server**: [NLSQL MCP Server](https://github.com/tushar-badhwar/nlsql-mcp-server)
- **Underlying Application**: [nl2sql](https://github.com/tushar-badhwar/nl2sql)
- **Built with**: [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), [CrewAI](https://crewai.com/), [OpenAI](https://openai.com/)

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/tushar-badhwar/nlsql-mcp-server/issues)
- **Documentation**: [GitHub Repository](https://github.com/tushar-badhwar/nlsql-mcp-server)
- **Discussions**: [GitHub Discussions](https://github.com/tushar-badhwar/nlsql-mcp-server/discussions)

---

**Made with ❤️ by [Tushar Badhwar](https://github.com/tushar-badhwar)**
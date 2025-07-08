"""
NLSQL MCP Server

Main MCP server implementation that exposes nlsql functionality as MCP tools.
"""

import asyncio
import logging
import os
from typing import Any, Sequence
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env file in the MCP server directory
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
except ImportError:
    logger.warning("python-dotenv not available, skipping .env file loading")

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from nlsql_mcp_server.nlsql_client import NLSQLClient
from nlsql_mcp_server.tools import NLSQLTools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("nlsql-mcp-server")

# Initialize client and tools
client = NLSQLClient()
tools = NLSQLTools(client)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    
    Returns:
        List of available MCP tools
    """
    return tools.get_tools()


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool calls.
    
    Args:
        name: Name of the tool to call
        arguments: Arguments for the tool
        
    Returns:
        List of content items
    """
    logger.info(f"Calling tool: {name} with arguments: {arguments}")
    
    try:
        result = await tools.call_tool(name, arguments)
        logger.info(f"Tool {name} executed successfully")
        return result
    except Exception as e:
        logger.error(f"Error calling tool {name}: {str(e)}")
        return [
            types.TextContent(
                type="text",
                text=f"Error executing tool '{name}': {str(e)}"
            )
        ]


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available resources.
    
    Returns:
        List of available resources
    """
    # For now, return empty list
    # Could potentially expose database schemas, sample data, etc. as resources
    return []


@server.read_resource()
async def handle_read_resource(uri: types.AnyUrl) -> str:
    """
    Read a resource.
    
    Args:
        uri: URI of the resource to read
        
    Returns:
        Resource content
    """
    # For now, not implemented
    # Could potentially provide access to database schemas, documentation, etc.
    raise NotImplementedError("Resources not implemented yet")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    
    Returns:
        List of available prompts
    """
    return [
        types.Prompt(
            name="analyze_database",
            description="Analyze a database and provide comprehensive schema information",
            arguments=[
                types.PromptArgument(
                    name="database_type",
                    description="Type of database (sqlite, postgresql, mysql)",
                    required=False
                ),
                types.PromptArgument(
                    name="connection_details",
                    description="Database connection details",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="generate_sql_query",
            description="Generate SQL query from natural language description",
            arguments=[
                types.PromptArgument(
                    name="question",
                    description="Natural language question to convert to SQL",
                    required=True
                ),
                types.PromptArgument(
                    name="context",
                    description="Additional context about the database or requirements",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="troubleshoot_sql",
            description="Help troubleshoot SQL query issues",
            arguments=[
                types.PromptArgument(
                    name="sql_query",
                    description="SQL query that needs troubleshooting",
                    required=True
                ),
                types.PromptArgument(
                    name="error_message",
                    description="Error message or issue description",
                    required=False
                )
            ]
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str]
) -> types.GetPromptResult:
    """
    Get a prompt.
    
    Args:
        name: Name of the prompt
        arguments: Arguments for the prompt
        
    Returns:
        Prompt result
    """
    if name == "analyze_database":
        return types.GetPromptResult(
            description="Analyze database schema and structure",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"""
Please analyze the database with the following details:
- Database type: {arguments.get('database_type', 'Not specified')}
- Connection details: {arguments.get('connection_details', 'Not specified')}

Use the nlsql MCP tools to:
1. Connect to the database
2. Analyze the schema
3. Get detailed table information
4. Provide sample data from key tables
5. Suggest common queries that might be useful

Provide a comprehensive analysis including:
- Database overview
- Table relationships
- Key insights about the data structure
- Recommendations for effective querying
"""
                    )
                )
            ]
        )
    
    elif name == "generate_sql_query":
        return types.GetPromptResult(
            description="Generate SQL query from natural language",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"""
Please generate a SQL query for the following request:

Question: {arguments.get('question', 'Not specified')}
Context: {arguments.get('context', 'None provided')}

Use the nlsql MCP tools to:
1. Convert the natural language question to SQL
2. Validate the generated query
3. Execute the query and show results
4. Explain the query logic

Please provide:
- The generated SQL query
- Explanation of the query logic
- Results from executing the query
- Any potential improvements or alternatives
"""
                    )
                )
            ]
        )
    
    elif name == "troubleshoot_sql":
        return types.GetPromptResult(
            description="Troubleshoot SQL query issues",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"""
Please help troubleshoot the following SQL query:

SQL Query: {arguments.get('sql_query', 'Not specified')}
Error/Issue: {arguments.get('error_message', 'Not specified')}

Use the nlsql MCP tools to:
1. Validate the SQL query syntax
2. Check if table/column names exist
3. Identify potential issues
4. Suggest corrections
5. Test the corrected query

Please provide:
- Analysis of the issue
- Corrected SQL query (if needed)
- Explanation of the changes
- Test results
"""
                    )
                )
            ]
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")


async def main():
    """
    Main function to run the MCP server.
    """
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment variables")
        logger.warning("Natural language to SQL functionality will not work")
    
    logger.info("Starting NLSQL MCP Server...")
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nlsql-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
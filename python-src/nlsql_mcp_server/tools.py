"""
MCP Tools for NLSQL Server

This module defines all the MCP tools that expose nlsql functionality.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import json

from nlsql_mcp_server.nlsql_client import NLSQLClient

logger = logging.getLogger(__name__)


class NLSQLTools:
    """
    MCP Tools for NLSQL functionality
    """
    
    def __init__(self, client: NLSQLClient):
        self.client = client
        self._tools: Dict[str, Tool] = {}
        self._setup_tools()
    
    def _setup_tools(self) -> None:
        """Setup all available MCP tools"""
        
        # Database connection tools
        self._tools["connect_database"] = Tool(
            name="connect_database",
            description="Connect to a database (SQLite, PostgreSQL, or MySQL)",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_type": {
                        "type": "string",
                        "enum": ["sqlite", "postgresql", "mysql"],
                        "description": "Type of database to connect to"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to SQLite database file (for SQLite only)"
                    },
                    "host": {
                        "type": "string",
                        "description": "Database host (for PostgreSQL/MySQL)"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Database port (for PostgreSQL/MySQL)"
                    },
                    "database": {
                        "type": "string",
                        "description": "Database name (for PostgreSQL/MySQL)"
                    },
                    "username": {
                        "type": "string",
                        "description": "Database username (for PostgreSQL/MySQL)"
                    },
                    "password": {
                        "type": "string",
                        "description": "Database password (for PostgreSQL/MySQL)"
                    }
                },
                "required": ["db_type"],
                "additionalProperties": False
            }
        )
        
        self._tools["connect_sample_database"] = Tool(
            name="connect_sample_database",
            description="Connect to the sample NBA database for testing",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
        
        # Schema analysis tools
        self._tools["analyze_schema"] = Tool(
            name="analyze_schema",
            description="Analyze database schema and structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Force refresh of schema cache",
                        "default": False
                    }
                },
                "additionalProperties": False
            }
        )
        
        self._tools["get_database_info"] = Tool(
            name="get_database_info",
            description="Get detailed database information including tables, columns, and relationships",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
        
        self._tools["get_table_sample"] = Tool(
            name="get_table_sample",
            description="Get sample data from a specific table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to sample"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of sample rows to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["table_name"],
                "additionalProperties": False
            }
        )
        
        # Natural language to SQL tools
        self._tools["natural_language_to_sql"] = Tool(
            name="natural_language_to_sql",
            description="Convert natural language question to SQL query using AI",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question to convert to SQL"
                    },
                    "skip_schema": {
                        "type": "boolean",
                        "description": "Skip schema analysis for faster processing",
                        "default": False
                    }
                },
                "required": ["question"],
                "additionalProperties": False
            }
        )
        
        # SQL execution tools
        self._tools["execute_sql_query"] = Tool(
            name="execute_sql_query",
            description="Execute SQL query on connected database",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of rows to return",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["sql_query"],
                "additionalProperties": False
            }
        )
        
        self._tools["validate_sql_query"] = Tool(
            name="validate_sql_query",
            description="Validate SQL query syntax and structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "SQL query to validate"
                    }
                },
                "required": ["sql_query"],
                "additionalProperties": False
            }
        )
        
        # Utility tools
        self._tools["get_connection_status"] = Tool(
            name="get_connection_status",
            description="Get current database connection status",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
        
        self._tools["disconnect_database"] = Tool(
            name="disconnect_database",
            description="Disconnect from current database",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    
    def get_tools(self) -> List[Tool]:
        """Get all available tools"""
        return list(self._tools.values())
    
    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Get a specific tool by name"""
        return self._tools.get(name)
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
        """
        Call a tool with given arguments
        
        Args:
            name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            List of content items (text, image, or embedded resource)
        """
        try:
            if name not in self._tools:
                return [TextContent(
                    type="text",
                    text=f"Error: Tool '{name}' not found"
                )]
            
            # Route to appropriate handler
            if name == "connect_database":
                result = self.client.connect_database(**arguments)
            elif name == "connect_sample_database":
                result = self.client.connect_sample_database()
            elif name == "analyze_schema":
                result = self.client.analyze_schema(**arguments)
            elif name == "get_database_info":
                result = self.client.get_database_info()
            elif name == "get_table_sample":
                result = self.client.get_table_sample(**arguments)
            elif name == "natural_language_to_sql":
                result = self.client.natural_language_to_sql(**arguments)
            elif name == "execute_sql_query":
                result = self.client.execute_sql_query(**arguments)
            elif name == "validate_sql_query":
                result = self.client.validate_sql_query(**arguments)
            elif name == "get_connection_status":
                result = self.client.get_status()
            elif name == "disconnect_database":
                result = self.client.disconnect()
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: Handler for tool '{name}' not implemented"
                )]
            
            # Format result for MCP
            return self._format_result(result)
            
        except Exception as e:
            logger.error(f"Error calling tool '{name}': {str(e)}")
            return [TextContent(
                type="text",
                text=f"Error executing tool '{name}': {str(e)}"
            )]
    
    def _format_result(self, result: Dict[str, Any]) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
        """
        Format tool result for MCP response
        
        Args:
            result: Tool execution result
            
        Returns:
            List of content items
        """
        try:
            # Handle different types of results
            if isinstance(result, dict):
                # Check if it's a success/error result
                if "success" in result:
                    if result["success"]:
                        # Format successful result
                        if "sql_query" in result:
                            # Natural language to SQL result
                            return self._format_sql_result(result)
                        elif "data" in result:
                            # Query execution result
                            return self._format_query_result(result)
                        else:
                            # General success result
                            return [TextContent(
                                type="text",
                                text=self._format_success_message(result)
                            )]
                    else:
                        # Error result
                        return [TextContent(
                            type="text",
                            text=f"Error: {result.get('error', 'Unknown error')}"
                        )]
                else:
                    # General dictionary result
                    return [TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, default=str)
                    )]
            else:
                # Convert to string
                return [TextContent(
                    type="text",
                    text=str(result)
                )]
                
        except Exception as e:
            logger.error(f"Error formatting result: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Error formatting result: {str(e)}"
            )]
    
    def _format_sql_result(self, result: Dict[str, Any]) -> List[TextContent]:
        """Format natural language to SQL result"""
        content = []
        
        if result.get("sql_query"):
            content.append(f"**Generated SQL Query:**\n```sql\n{result['sql_query']}\n```")
        
        if result.get("raw_output"):
            content.append(f"\n**AI Analysis:**\n{result['raw_output']}")
        
        processing_time = result.get("processing_time", 0)
        if processing_time > 0:
            content.append(f"\n**Processing Time:** {processing_time:.2f} seconds")
        
        return [TextContent(
            type="text",
            text="\n".join(content)
        )]
    
    def _format_query_result(self, result: Dict[str, Any]) -> List[TextContent]:
        """Format SQL query execution result"""
        content = []
        
        if result.get("data"):
            data = result["data"]
            row_count = len(data)
            
            content.append(f"**Query Results:** {row_count} rows returned")
            
            if row_count > 0:
                # Format as table
                if isinstance(data[0], dict):
                    # Get column names
                    columns = list(data[0].keys())
                    
                    # Create table header
                    header = "| " + " | ".join(columns) + " |"
                    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
                    
                    content.append(f"\n{header}")
                    content.append(separator)
                    
                    # Add data rows (limit to first 20 rows for readability)
                    for i, row in enumerate(data[:20]):
                        row_values = [str(row.get(col, "")) for col in columns]
                        content.append("| " + " | ".join(row_values) + " |")
                    
                    if row_count > 20:
                        content.append(f"\n... and {row_count - 20} more rows")
                else:
                    # Fallback for non-dictionary data
                    content.append(f"\n{json.dumps(data[:10], indent=2, default=str)}")
                    if row_count > 10:
                        content.append(f"\n... and {row_count - 10} more rows")
        else:
            content.append("**Query Results:** No data returned")
        
        return [TextContent(
            type="text",
            text="\n".join(content)
        )]
    
    def _format_success_message(self, result: Dict[str, Any]) -> str:
        """Format general success message"""
        message = result.get("message", "Operation completed successfully")
        
        # Add additional information if available
        additional_info = []
        
        if "database_type" in result:
            additional_info.append(f"Database Type: {result['database_type']}")
        
        if "table_count" in result:
            additional_info.append(f"Tables: {result['table_count']}")
        
        if "tables" in result and isinstance(result["tables"], list):
            if len(result["tables"]) <= 5:
                additional_info.append(f"Table Names: {', '.join(result['tables'])}")
            else:
                additional_info.append(f"Table Names: {', '.join(result['tables'][:5])}, ... and {len(result['tables']) - 5} more")
        
        if "sample_questions" in result:
            additional_info.append("\n**Sample Questions:**")
            for question in result["sample_questions"]:
                additional_info.append(f"- {question}")
        
        if additional_info:
            return f"{message}\n\n" + "\n".join(additional_info)
        else:
            return message
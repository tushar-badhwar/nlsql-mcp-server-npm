#!/usr/bin/env python3
"""
NLSQL Custom MCP Server
Direct JSON-RPC implementation without problematic MCP library validation
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Setup logging
mcp_mode = os.getenv('MCP_MODE', '0') == '1'
if mcp_mode:
    logging.basicConfig(level=logging.ERROR)
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        if not mcp_mode:
            logger.info(f"Loaded environment variables from {env_file}")
except ImportError:
    logger.warning("python-dotenv not available")

# NLSQL imports
from nlsql_mcp_server.nlsql_client import NLSQLClient
from nlsql_mcp_server.tools import NLSQLTools

class CustomMCPServer:
    """Custom MCP server with direct JSON-RPC handling"""
    
    def __init__(self):
        self.client = NLSQLClient()
        self.tools_manager = NLSQLTools(self.client)
        self.initialized = False
        
    async def handle_request(self, request):
        """Handle incoming JSON-RPC request"""
        try:
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})
            
            if not mcp_mode:
                logger.info(f"Handling request: {method}")
            
            if method == "initialize":
                return await self.handle_initialize(request_id, params)
            elif method == "initialized":
                return await self.handle_initialized()
            elif method == "tools/call":
                return await self.handle_tool_call(request_id, params)
            elif method == "prompts/list":
                return await self.handle_prompts_list(request_id)
            elif method == "prompts/get":
                return await self.handle_prompt_get(request_id, params)
            else:
                return self.error_response(request_id, -32601, f"Method not found: {method}")
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self.error_response(request.get("id"), -32603, f"Internal error: {str(e)}")
    
    async def handle_initialize(self, request_id, params):
        """Handle initialize request"""
        self.initialized = True
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "nlsql-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    
    async def handle_initialized(self):
        """Handle initialized notification"""
        # This is a notification, no response needed
        if not mcp_mode:
            logger.info("Client initialized")
        return None
    
    async def handle_tool_call(self, request_id, params):
        """Handle tool call request"""
        if not self.initialized:
            return self.error_response(request_id, -32002, "Server not initialized")
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return self.error_response(request_id, -32602, "Missing tool name")
        
        try:
            result = await self.tools_manager.call_tool(tool_name, arguments)
            
            # Convert result to JSON-compatible format
            content = []
            for item in result:
                if hasattr(item, 'text'):
                    content.append({
                        "type": "text",
                        "text": item.text
                    })
                else:
                    content.append({
                        "type": "text", 
                        "text": str(item)
                    })
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": content
                }
            }
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(error_msg)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": error_msg
                    }]
                }
            }
    
    async def handle_prompts_list(self, request_id):
        """Handle prompts list request"""
        prompts = [
            {
                "name": "analyze_database",
                "description": "Analyze database schema and provide insights",
                "arguments": [
                    {
                        "name": "database_type",
                        "description": "Type of database",
                        "required": False
                    }
                ]
            },
            {
                "name": "generate_sql",
                "description": "Generate SQL from natural language",
                "arguments": [
                    {
                        "name": "question", 
                        "description": "Natural language question",
                        "required": True
                    }
                ]
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "prompts": prompts
            }
        }
    
    async def handle_prompt_get(self, request_id, params):
        """Handle prompt get request"""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if name == "analyze_database":
            text = "Please analyze the database structure and provide insights using the NLSQL tools."
        elif name == "generate_sql":
            question = arguments.get("question", "")
            text = f"Convert this question to SQL using the natural_language_to_sql tool: {question}"
        else:
            return self.error_response(request_id, -32602, f"Unknown prompt: {name}")
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "description": f"Prompt for {name}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": text
                        }
                    }
                ]
            }
        }
    
    def error_response(self, request_id, code, message):
        """Create error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

async def main():
    """Run the custom MCP server"""
    if not os.getenv("OPENAI_API_KEY"):
        if not mcp_mode:
            logger.warning("OPENAI_API_KEY not set - some features may not work")
    
    if not mcp_mode:
        logger.info("Starting NLSQL Custom MCP Server...")
    
    server = CustomMCPServer()
    
    try:
        while True:
            # Read line from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = await server.handle_request(request)
                
                if response:  # Only send response for requests, not notifications
                    print(json.dumps(response), flush=True)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        if not mcp_mode:
            logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
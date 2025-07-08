"""
NLSQL Client Interface

This module provides a bridge between the MCP server and the original nlsql application.
It handles database connections, query processing, and result formatting.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
import json

# Add the nl2sql/nlsql directory to the Python path
# This MCP server requires the original nl2sql application to be installed
# Go up from src/nlsql_mcp_server/nlsql_client.py to parent directory, then look for nl2sql or nlsql

# Try different possible directory names and locations
possible_dirs = [
    Path(__file__).parent.parent.parent.parent / "nl2sql",  # Standard GitHub repo name
    Path(__file__).parent.parent.parent.parent / "nlsql",   # Alternative name
    Path("/home/tbadhwar/nlsql"),                           # Absolute path fallback
    Path("/home/tbadhwar/nl2sql")                           # Absolute path fallback
]

NLSQL_DIR = None
for dir_path in possible_dirs:
    if dir_path.exists() and (dir_path / "database_manager.py").exists():
        NLSQL_DIR = dir_path
        sys.path.insert(0, str(NLSQL_DIR))
        break

if not NLSQL_DIR:
    raise ImportError(
        "Could not find the nl2sql application. Please ensure it's installed in the parent directory.\n"
        "Install from: https://github.com/tushar-badhwar/nl2sql\n"
        "Expected structure:\n"
        "  parent_directory/\n"
        "  ├── nl2sql/          # Original application\n"
        "  └── nlsql-mcp-server/ # This MCP server"
    )

try:
    from database_manager import DatabaseManager
    from crew_setup import NL2SQLCrew
    from agents import NL2SQLAgents
    from tasks import NL2SQLTasks
except ImportError as e:
    logging.error(f"Failed to import nlsql modules: {e}")
    logging.error("Make sure the nlsql directory is in the correct location")
    raise

logger = logging.getLogger(__name__)


class NLSQLClient:
    """
    Client interface for NLSQL functionality in MCP server context
    """
    
    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.crew: Optional[NL2SQLCrew] = None
        self.connection_info: Dict[str, Any] = {}
        self.schema_cache: Optional[str] = None
        
    def connect_database(self, **connection_params) -> Dict[str, Any]:
        """
        Connect to a database with the given parameters
        
        Args:
            **connection_params: Database connection parameters
            
        Returns:
            Dict[str, Any]: Connection result
        """
        try:
            self.db_manager = DatabaseManager()
            success = self.db_manager.connect(**connection_params)
            
            if success:
                self.connection_info = connection_params
                self.crew = NL2SQLCrew(self.db_manager, model_name='gpt-4o')
                self.schema_cache = None  # Reset schema cache
                
                # Get basic database info
                tables = self.db_manager.get_table_names()
                
                return {
                    "success": True,
                    "message": "Database connected successfully",
                    "database_type": connection_params.get('db_type', 'unknown'),
                    "table_count": len(tables),
                    "tables": tables
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to connect to database"
                }
                
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def connect_sqlite_file(self, file_path: str) -> Dict[str, Any]:
        """
        Connect to a SQLite database file
        
        Args:
            file_path: Path to SQLite database file
            
        Returns:
            Dict[str, Any]: Connection result
        """
        return self.connect_database(db_type='sqlite', file_path=file_path)
    
    def connect_sample_database(self) -> Dict[str, Any]:
        """
        Connect to the sample NBA database
        
        Returns:
            Dict[str, Any]: Connection result
        """
        nba_db_path = NLSQL_DIR / "nba.sqlite"
        if not nba_db_path.exists():
            return {
                "success": False,
                "error": "Sample NBA database not found"
            }
        
        result = self.connect_sqlite_file(str(nba_db_path))
        if result["success"]:
            result["message"] = "Connected to sample NBA database"
            result["sample_questions"] = [
                "How many teams are in the NBA?",
                "List all teams from California",
                "Who are the players with 'James' in their name?",
                "Show me the Boston Celtics team details",
                "How many players are in the database?",
                "Which teams were founded before 1950?"
            ]
        return result
    
    def analyze_schema(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Analyze database schema
        
        Args:
            force_refresh: Force refresh of schema cache
            
        Returns:
            Dict[str, Any]: Schema analysis result
        """
        if not self.crew:
            return {
                "success": False,
                "error": "No database connection established"
            }
        
        try:
            if force_refresh or not self.schema_cache:
                db_type = self.connection_info.get('db_type', 'unknown')
                db_path = self.connection_info.get('file_path', 'connected_database')
                
                schema_analysis = self.crew.analyze_schema(db_type, db_path)
                self.schema_cache = schema_analysis
            
            return {
                "success": True,
                "schema_analysis": self.schema_cache,
                "cached": not force_refresh and self.schema_cache is not None
            }
            
        except Exception as e:
            logger.error(f"Schema analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get detailed database information
        
        Returns:
            Dict[str, Any]: Database information
        """
        if not self.db_manager:
            return {
                "success": False,
                "error": "No database connection established"
            }
        
        try:
            tables = self.db_manager.get_table_names()
            database_info = {
                "success": True,
                "database_type": self.db_manager.database_type,
                "table_count": len(tables),
                "tables": {}
            }
            
            for table in tables:
                try:
                    schema = self.db_manager.get_table_schema(table)
                    stats = self.db_manager.get_table_stats(table)
                    
                    database_info["tables"][table] = {
                        "columns": schema.get('columns', []),
                        "primary_keys": schema.get('primary_keys', []),
                        "foreign_keys": schema.get('foreign_keys', []),
                        "row_count": stats.get('row_count', 0)
                    }
                except Exception as e:
                    logger.warning(f"Error getting info for table {table}: {str(e)}")
                    database_info["tables"][table] = {
                        "error": str(e)
                    }
            
            return database_info
            
        except Exception as e:
            logger.error(f"Error getting database info: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def natural_language_to_sql(self, question: str, skip_schema: bool = False) -> Dict[str, Any]:
        """
        Convert natural language question to SQL query
        
        Args:
            question: Natural language question
            skip_schema: Skip schema analysis for faster processing
            
        Returns:
            Dict[str, Any]: Query processing result
        """
        if not self.crew:
            return {
                "success": False,
                "error": "No database connection established"
            }
        
        try:
            db_type = self.connection_info.get('db_type', 'unknown')
            db_path = self.connection_info.get('file_path', 'connected_database')
            
            result = self.crew.process_query(
                natural_language_question=question,
                use_full_workflow=True,
                db_type=db_type,
                db_path=db_path,
                skip_schema=skip_schema
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Natural language to SQL conversion failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }
    
    def execute_sql_query(self, sql_query: str, limit: int = 100) -> Dict[str, Any]:
        """
        Execute SQL query on connected database
        
        Args:
            sql_query: SQL query to execute
            limit: Maximum number of rows to return
            
        Returns:
            Dict[str, Any]: Query execution result
        """
        if not self.db_manager:
            return {
                "success": False,
                "error": "No database connection established"
            }
        
        try:
            # Add LIMIT clause if not present and limit is specified
            if limit > 0 and 'LIMIT' not in sql_query.upper():
                if sql_query.strip().endswith(';'):
                    sql_query = sql_query.strip()[:-1] + f' LIMIT {limit};'
                else:
                    sql_query = sql_query.strip() + f' LIMIT {limit}'
            
            result = self.db_manager.execute_query(sql_query)
            
            if result['success'] and result.get('data'):
                # Convert to list of dictionaries for JSON serialization
                data = []
                for row in result['data']:
                    if hasattr(row, '_asdict'):
                        data.append(row._asdict())
                    elif isinstance(row, dict):
                        data.append(row)
                    else:
                        data.append(dict(row))
                result['data'] = data
            
            return result
            
        except Exception as e:
            logger.error(f"SQL query execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sql_query": sql_query
            }
    
    def validate_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Validate SQL query syntax and structure
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Dict[str, Any]: Validation result
        """
        if not self.db_manager:
            return {
                "success": False,
                "error": "No database connection established"
            }
        
        try:
            # Basic syntax validation
            sql_upper = sql_query.upper().strip()
            
            # Check for basic SQL structure
            if not sql_upper.startswith('SELECT'):
                return {
                    "success": False,
                    "error": "Query must start with SELECT",
                    "valid": False
                }
            
            if 'FROM' not in sql_upper:
                return {
                    "success": False,
                    "error": "Query must contain FROM clause",
                    "valid": False
                }
            
            # Try to parse with database (dry run)
            try:
                # Create a version with LIMIT 0 to check syntax without executing
                test_query = sql_query.strip()
                if test_query.endswith(';'):
                    test_query = test_query[:-1]
                test_query += ' LIMIT 0'
                
                result = self.db_manager.execute_query(test_query)
                
                if result['success']:
                    return {
                        "success": True,
                        "valid": True,
                        "message": "SQL query syntax is valid"
                    }
                else:
                    return {
                        "success": True,
                        "valid": False,
                        "error": result.get('error', 'Unknown validation error')
                    }
                    
            except Exception as e:
                return {
                    "success": True,
                    "valid": False,
                    "error": str(e)
                }
            
        except Exception as e:
            logger.error(f"SQL validation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_table_sample(self, table_name: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get sample data from a specific table
        
        Args:
            table_name: Name of the table
            limit: Number of sample rows to return
            
        Returns:
            Dict[str, Any]: Sample data result
        """
        if not self.db_manager:
            return {
                "success": False,
                "error": "No database connection established"
            }
        
        try:
            sample_data = self.db_manager.get_sample_data(table_name, limit=limit)
            
            if sample_data['success'] and sample_data.get('data'):
                # Convert to list of dictionaries for JSON serialization
                data = []
                for row in sample_data['data']:
                    if hasattr(row, '_asdict'):
                        data.append(row._asdict())
                    elif isinstance(row, dict):
                        data.append(row)
                    else:
                        data.append(dict(row))
                sample_data['data'] = data
            
            return sample_data
            
        except Exception as e:
            logger.error(f"Error getting table sample: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "table_name": table_name
            }
    
    def disconnect(self) -> Dict[str, Any]:
        """
        Disconnect from database and cleanup
        
        Returns:
            Dict[str, Any]: Disconnect result
        """
        try:
            if self.db_manager:
                self.db_manager.disconnect()
            
            self.db_manager = None
            self.crew = None
            self.connection_info = {}
            self.schema_cache = None
            
            return {
                "success": True,
                "message": "Database disconnected successfully"
            }
            
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current client status
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "connected": self.db_manager is not None,
            "database_type": self.connection_info.get('db_type'),
            "schema_cached": self.schema_cache is not None,
            "crew_initialized": self.crew is not None
        }
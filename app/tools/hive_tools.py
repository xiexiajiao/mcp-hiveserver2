import asyncio
import json
from app.tools.registry import registry
from app.core.hive_client import execute_query
from app.config import config
import logging

logger = logging.getLogger(__name__)

@registry.register(
    name="query_hive",
    description="Executes a raw Hive SQL query. Use this for complex queries, Joins, Aggregations, or DDL operations that are not covered by other specialized tools. NOT recommended for simple table listings or schema checks.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The SQL query to execute"
            },
            "database": {
                "type": "string",
                "description": "Optional: specify database to use"
            },
            "max_rows": {
                "type": "integer",
                "description": "Optional: maximum number of rows returned (default 1000)"
            }
        },
        "required": ["query"]
    }
)
async def query_hive(query: str, database: str = None, max_rows: int = None):
    query = query.strip()
    if query.endswith(';'):
        query = query[:-1].strip()
    
    db = database or config.hive.database
    
    # Resolve max_rows
    server_max = config.server.max_rows
    if max_rows is None:
        limit = server_max
    else:
        try:
            limit = int(max_rows)
        except Exception:
            limit = server_max
        
        if limit <= 0:
            limit = server_max
        if limit > 10000: # Hard cap
            limit = 10000

    logger.info(f"Executing Hive query: {query} on db: {db}")
    
    try:
        # Run blocking hive query in thread pool
        result = await asyncio.to_thread(execute_query, query, db, limit)
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2, default=str)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"error": f"Query execution failed: {str(e)}"}, ensure_ascii=False)
            }]
        }

@registry.register(
    name="get_table_schema",
    description="Get detailed schema and metadata for a Hive table. Returns columns, data types, partitions, and storage information in a structured format. Prefer this over 'DESCRIBE' queries.",
    input_schema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "The name of the table to inspect (e.g. 'table_name' or 'db.table_name')"
            },
            "database": {
                "type": "string",
                "description": "Optional: database name if not included in table_name"
            }
        },
        "required": ["table_name"]
    }
)
async def get_table_schema(table_name: str, database: str = None):
    # Construct DESCRIBE FORMATTED query
    if database and '.' not in table_name:
        full_table_name = f"{database}.{table_name}"
    else:
        full_table_name = table_name
        
    query = f"DESCRIBE FORMATTED {full_table_name}"
    
    logger.info(f"Getting schema for table: {full_table_name}")
    
    try:
        # We use a larger limit for schema to ensure we get all fields
        result = await asyncio.to_thread(execute_query, query, None, 10000)
        
        # We could parse the 'result' here to make it even more structured JSON
        # For now, returning the formatted output is already a big improvement
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2, default=str)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"error": f"Failed to get table schema: {str(e)}"}, ensure_ascii=False)
            }]
        }

@registry.register(
    name="list_tables",
    description="List tables in a Hive database. Supports filtering by name pattern.",
    input_schema={
        "type": "object",
        "properties": {
            "database": {
                "type": "string",
                "description": "The database to list tables from (defaults to configured database)"
            },
            "search_pattern": {
                "type": "string",
                "description": "Optional: wildcard pattern to filter table names (e.g. 'ods_*', '*_log')"
            }
        },
        "required": []
    }
)
async def list_tables(database: str = None, search_pattern: str = None):
    db = database or config.hive.database
    
    if search_pattern:
        query = f"SHOW TABLES IN {db} LIKE '{search_pattern}'"
    else:
        query = f"SHOW TABLES IN {db}"
        
    logger.info(f"Listing tables in {db} with pattern {search_pattern}")
    
    try:
        result = await asyncio.to_thread(execute_query, query, db, 10000)
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2, default=str)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"error": f"Failed to list tables: {str(e)}"}, ensure_ascii=False)
            }]
        }

@registry.register(
    name="preview_table",
    description="Preview data from a Hive table safely. Always limits the number of rows returned.",
    input_schema={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "The name of the table to preview"
            },
            "limit": {
                "type": "integer",
                "description": "Number of rows to return (default 10, max 100)"
            },
            "database": {
                "type": "string",
                "description": "Optional: database name"
            }
        },
        "required": ["table_name"]
    }
)
async def preview_table(table_name: str, limit: int = 10, database: str = None):
    if limit > 100:
        limit = 100 # Strict limit for preview
    
    if database and '.' not in table_name:
        full_table_name = f"{database}.{table_name}"
    else:
        full_table_name = table_name
        
    query = f"SELECT * FROM {full_table_name} LIMIT {limit}"
    
    logger.info(f"Previewing table: {full_table_name} limit {limit}")
    
    try:
        result = await asyncio.to_thread(execute_query, query, None, limit)
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2, default=str)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"error": f"Failed to preview table: {str(e)}"}, ensure_ascii=False)
            }]
        }

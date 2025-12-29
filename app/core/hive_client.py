from pyhive import hive
from app.config import config
import logging

logger = logging.getLogger(__name__)

def get_hive_connection(database: str = None):
    """
    Creates and returns a new Hive connection.
    """
    db = database or config.hive.database
    
    conn_kwargs = {
        "host": config.hive.host,
        "port": config.hive.port,
        "username": config.hive.username,
        "password": config.hive.password,
        "database": db,
        "auth": config.hive.auth,
        "configuration": config.hive.configuration,
    }
    
    return hive.Connection(**conn_kwargs)

def execute_query(query: str, database: str = None, max_rows: int = 1000) -> dict:
    """
    Executes a Hive query and returns the results.
    """
    conn = None
    try:
        conn = get_hive_connection(database)
        cursor = conn.cursor()
        cursor.execute(query)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        truncated = False
        if max_rows is not None:
            rows = cursor.fetchmany(max_rows + 1)
            if len(rows) > max_rows:
                truncated = True
                rows = rows[:max_rows]
        else:
            rows = cursor.fetchall()

        return {
            "columns": columns,
            "data": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }
    except Exception as e:
        logger.error(f"Hive query failed: {e}")
        raise e
    finally:
        if conn:
            conn.close()

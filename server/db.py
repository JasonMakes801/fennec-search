import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import register_adapter, adapt, new_type, register_type
from contextlib import contextmanager
import numpy as np

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'dbname': os.environ.get('DB_NAME', 'fennec'),
    'user': os.environ.get('DB_USER', 'fennec'),
    'password': os.environ.get('DB_PASSWORD', 'fennec'),
}

# Register pgvector type adapter
def register_vector_type(conn):
    """Register the pgvector 'vector' type with psycopg2."""
    cur = conn.cursor()
    cur.execute("SELECT oid FROM pg_type WHERE typname = 'vector'")
    row = cur.fetchone()
    cur.close()
    
    if row:
        vector_oid = row[0]
        
        def vector_to_array(value, cur):
            if value is None:
                return None
            # pgvector format: [0.1,0.2,0.3,...]
            return np.array([float(x) for x in value.strip('[]').split(',')])
        
        VECTOR = new_type((vector_oid,), 'VECTOR', vector_to_array)
        register_type(VECTOR)

# Adapter for numpy arrays -> pgvector
def adapt_numpy_array(arr):
    return adapt('[' + ','.join(str(x) for x in arr) + ']')

register_adapter(np.ndarray, adapt_numpy_array)

# Register on first connection
_vector_registered = False

@contextmanager
def get_db():
    """Context manager for database connections."""
    global _vector_registered
    conn = psycopg2.connect(**DB_CONFIG)
    
    if not _vector_registered:
        register_vector_type(conn)
        _vector_registered = True
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def fetch_one(query, params=None):
    """Execute query and return single row as dict."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

def fetch_all(query, params=None):
    """Execute query and return all rows as list of dicts."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

def execute(query, params=None):
    """Execute a query without returning results."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)

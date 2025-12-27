"""
Database connection and operations for the ingest service.
"""

import os
import psycopg2

def get_connection():
    """Get a connection to the Postgres database."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "fennec"),
        user=os.environ.get("DB_USER", "fennec"),
        password=os.environ.get("DB_PASSWORD", "fennec"),
    )

def init_db():
    """Initialize database schema if needed."""
    # Schema is created by init.sql, this is for any runtime migrations
    pass

# import sqlite3
# import pysqlite3 as sqlite3
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from contextlib import contextmanager
from core.config import settings

def init_db():
    """Initialize SQLite database with required tables"""
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                collection_name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id)
            )
        """)
        db.commit()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
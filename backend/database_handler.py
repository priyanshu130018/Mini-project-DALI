"""Database handler for storing conversation records"""

import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import logging

logger = logging.getLogger(__name__)

class ConversationDB:
    def __init__(self, db_path="conversations.db"):
        """Initialize database connection and create tables if needed"""
        self.db_path = db_path
        self.create_tables()
        logger.info(f"Database initialized at {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise e
        finally:
            conn.close()
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Main conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_input TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    language TEXT DEFAULT 'english',
                    confidence_score REAL DEFAULT 0.0,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_time DATETIME,
                    total_interactions INTEGER DEFAULT 0
                )
            """)
            
            # Language switches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS language_switches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    from_language TEXT,
                    to_language TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)")
    
    def add_conversation(self, session_id, user_input, bot_response, language="english", confidence_score=0.0):
        """Add a conversation entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations 
                (session_id, user_input, bot_response, language, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, user_input, bot_response, language, confidence_score))
            
            # Update session interaction count
            cursor.execute("""
                UPDATE sessions 
                SET total_interactions = total_interactions + 1
                WHERE session_id = ?
            """, (session_id,))
    
    def start_session(self, session_id):
        """Start a new session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, start_time)
                VALUES (?, ?)
            """, (session_id, datetime.now()))
    
    def end_session(self, session_id):
        """End a session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions 
                SET end_time = ?
                WHERE session_id = ?
            """, (datetime.now(), session_id))
    
    def log_language_switch(self, session_id, from_lang, to_lang):
        """Log a language switch event"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO language_switches 
                (session_id, from_language, to_language)
                VALUES (?, ?, ?)
            """, (session_id, from_lang, to_lang))
    
    def get_session_history(self, session_id):
        """Get conversation history for a session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            return cursor.fetchall()
    
    def cleanup_old_sessions(self, days=30):
        """Delete sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM conversations 
                WHERE session_id IN (
                    SELECT session_id FROM sessions 
                    WHERE start_time < ?
                )
            """, (cutoff_date,))
            cursor.execute("DELETE FROM sessions WHERE start_time < ?", (cutoff_date,))
            logger.info(f"Cleaned up sessions older than {days} days")

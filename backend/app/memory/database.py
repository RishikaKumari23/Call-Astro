import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from backend.app.config.settings import settings
from backend.app.utils.logger import logger

class MemoryDatabase:
    def __init__(self, db_path: str = settings.DATABASE_PATH):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialise database tables for sessions and messages."""
        logger.info(f"Initialising database at {self.db_path}")
        
        # Ensure parent folder exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    dob TEXT,
                    birth_time TEXT,
                    birth_place TEXT,
                    gender TEXT,
                    name TEXT,
                    language TEXT DEFAULT 'Hinglish',
                    updated_at TEXT
                )
            """)
            
            # Create messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def get_or_create_session(self, session_id: str) -> Dict:
        """Fetch an existing session, or create it if not found."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            
            # Create new session record
            now_str = datetime.utcnow().isoformat()
            cursor.execute(
                """
                INSERT INTO sessions (session_id, dob, birth_time, birth_place, language, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, None, None, None, 'Hinglish', now_str)
            )
            conn.commit()
            
            return {
                "session_id": session_id,
                "dob": None,
                "birth_time": None,
                "birth_place": None,
                "gender": None,
                "name": None,
                "language": "Hinglish",
                "updated_at": now_str
            }

    def update_session(self, session_id: str, updates: Dict) -> Dict:
        """Update profile details for a session."""
        if not updates:
            return self.get_or_create_session(session_id)
            
        allowed_fields = {"dob", "birth_time", "birth_place", "gender", "name", "language"}
        fields_to_update = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
        
        if not fields_to_update:
            return self.get_or_create_session(session_id)
            
        fields_to_update["updated_at"] = datetime.utcnow().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
        params = list(fields_to_update.values()) + [session_id]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE sessions SET {set_clause} WHERE session_id = ?", params)
            conn.commit()
            
        return self.get_or_create_session(session_id)

    def add_message(self, session_id: str, role: str, content: str) -> Dict:
        """Append a message to the conversation history."""
        # Ensure session exists
        self.get_or_create_session(session_id)
        
        now_str = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, now_str)
            )
            conn.commit()
            
        return {"session_id": session_id, "role": role, "content": content, "timestamp": now_str}

    def get_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Fetch the list of latest messages for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content, timestamp FROM messages 
                WHERE session_id = ? 
                ORDER BY id ASC
                """,
                (session_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows][-limit:]

# Instantiate single global db reference
db = MemoryDatabase()

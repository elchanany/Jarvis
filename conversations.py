# conversations.py — Persistent chat history with SQLite
import sqlite3
import json
import uuid
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_chats.db")

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'שיחה חדשה',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            messages TEXT NOT NULL DEFAULT '[]'
        )
    """)
    conn.commit()
    conn.close()

def create_conversation(title="שיחה חדשה"):
    conn = _connect()
    cid = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at, messages) VALUES (?,?,?,?,?)",
        (cid, title, now, now, "[]")
    )
    conn.commit()
    conn.close()
    return {"id": cid, "title": title, "created_at": now, "updated_at": now, "messages": []}

def list_conversations():
    conn = _connect()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation(cid):
    conn = _connect()
    row = conn.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["messages"] = json.loads(d["messages"])
    return d

def save_messages(cid, messages):
    conn = _connect()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE conversations SET messages=?, updated_at=? WHERE id=?",
        (json.dumps(messages, ensure_ascii=False), now, cid)
    )
    conn.commit()
    conn.close()

def rename_conversation(cid, title):
    conn = _connect()
    conn.execute("UPDATE conversations SET title=? WHERE id=?", (title, cid))
    conn.commit()
    conn.close()

def delete_conversation(cid):
    conn = _connect()
    conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
    conn.commit()
    conn.close()

def auto_title(cid, first_message):
    """Generate a short title from the first message."""
    title = first_message.strip()[:40]
    if len(first_message.strip()) > 40:
        title += "..."
    rename_conversation(cid, title)
    return title

# Initialize DB on import
init_db()

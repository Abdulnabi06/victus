import sqlite3
import json
import uuid
import time
from typing import List, Dict, Any, Optional

DB_PATH = "zyricon.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Chats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                archived INTEGER DEFAULT 0
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                tool_calls TEXT,
                tool_output TEXT,
                image_url TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
            )
        """)
        
        # Settings / Config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                created_at REAL NOT NULL
            )
        """)
        
        # Set default config if empty
        cursor.execute("SELECT COUNT(*) FROM config")
        if cursor.fetchone()[0] == 0:
            default_config = {
                "model": "ChatGPT v4.0",
                "voice_enabled": "true",
                "voice_speed": "1.0",
                "search_provider": "duckduckgo",
                "automation_mode": "confirm"
            }
            for k, v in default_config.items():
                cursor.execute("INSERT INTO config (key, value) VALUES (?, ?)", (k, str(v)))
                
        conn.commit()

# Chat operations
def create_chat(title: str = "New Chat", model: str = "ChatGPT v4.0") -> Dict[str, Any]:
    chat_id = f"chat_{uuid.uuid4().hex[:8]}"
    now = time.time()
    with get_db() as conn:
        conn.cursor().execute(
            "INSERT INTO chats (id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (chat_id, title, model, now, now)
        )
        conn.commit()
    return {"id": chat_id, "title": title, "model": model, "created_at": now, "updated_at": now, "archived": False}

def get_all_chats() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chats ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        chats = []
        for r in rows:
            chats.append({
                "id": r["id"],
                "title": r["title"],
                "model": r["model"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "archived": bool(r["archived"])
            })
        return chats

def get_chat_with_messages(chat_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
        chat = cursor.fetchone()
        if not chat:
            return None
        
        cursor.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp ASC", (chat_id,))
        msg_rows = cursor.fetchall()
        messages = []
        for m in msg_rows:
            messages.append({
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "timestamp": m["timestamp"],
                "tool_calls": json.loads(m["tool_calls"]) if m["tool_calls"] else None,
                "tool_output": m["tool_output"],
                "image_url": m["image_url"]
            })
            
        return {
            "id": chat["id"],
            "title": chat["title"],
            "model": chat["model"],
            "created_at": chat["created_at"],
            "updated_at": chat["updated_at"],
            "messages": messages
        }

def add_message(chat_id: str, role: str, content: str, tool_calls: Any = None, tool_output: str = None, image_url: str = None) -> Dict[str, Any]:
    msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    now = time.time()
    tool_calls_json = json.dumps(tool_calls) if tool_calls else None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (id, chat_id, role, content, timestamp, tool_calls, tool_output, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (msg_id, chat_id, role, content, now, tool_calls_json, tool_output, image_url)
        )
        cursor.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
        conn.commit()
    return {
        "id": msg_id,
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "timestamp": now,
        "tool_calls": tool_calls,
        "tool_output": tool_output,
        "image_url": image_url
    }

# Config operations
def get_config() -> Dict[str, str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM config")
        return {r["key"]: r["value"] for r in cursor.fetchall()}

def update_config(config_dict: Dict[str, str]) -> Dict[str, str]:
    with get_db() as conn:
        cursor = conn.cursor()
        for k, v in config_dict.items():
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (k, str(v)))
        conn.commit()
    return get_config()

# Task operations
def save_task(task_id: str, name: str, status: str, result: str = None) -> Dict[str, Any]:
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO tasks (id, name, status, result, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, name, status, result, now)
        )
        conn.commit()
    return {"id": task_id, "name": name, "status": status, "result": result, "created_at": now}

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        r = cursor.fetchone()
        if not r:
            return None
        return {"id": r["id"], "name": r["name"], "status": r["status"], "result": r["result"], "created_at": r["created_at"]}

# Initialize DB on module import
init_db()

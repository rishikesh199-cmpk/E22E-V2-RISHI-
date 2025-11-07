# database.py
"""
SQLite database for user accounts and automation configs.
Passwords stored as SHA-256 hash.
"""

import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path("automation_users.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            user_id INTEGER UNIQUE,
            chat_id TEXT,
            name_prefix TEXT,
            delay INTEGER DEFAULT 5,
            cookies TEXT,
            messages TEXT,
            automation_running INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

_init_db()

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username: str, password: str):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        hashed_pw = _hash_password(password)
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        user_id = cur.lastrowid
        cur.execute("""
            INSERT INTO configs (user_id, chat_id, name_prefix, delay, cookies, messages)
            VALUES (?, '', '', 5, '', '')
        """, (user_id,))
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists!"
    except Exception as e:
        return False, f"Error creating user: {e}"
    finally:
        conn.close()

def verify_user(username: str, password: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    hashed_entered = _hash_password(password)
    if hashed_entered == row["password"]:
        return row["id"]
    return None

def get_username(user_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["username"] if row else None

def get_user_config(user_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM configs WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "chat_id": row["chat_id"],
        "name_prefix": row["name_prefix"],
        "delay": row["delay"],
        "cookies": row["cookies"],
        "messages": row["messages"]
    }

def update_user_config(user_id: int, chat_id, name_prefix, delay, cookies, messages):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO configs (user_id, chat_id, name_prefix, delay, cookies, messages)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            chat_id=excluded.chat_id,
            name_prefix=excluded.name_prefix,
            delay=excluded.delay,
            cookies=excluded.cookies,
            messages=excluded.messages
    """, (user_id, chat_id, name_prefix, delay, cookies, messages))
    conn.commit()
    conn.close()

def set_automation_running(user_id: int, running: bool):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE configs SET automation_running=? WHERE user_id=?", (1 if running else 0, user_id))
    conn.commit()
    conn.close()

def get_automation_running(user_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT automation_running FROM configs WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row["automation_running"]) if row else False

# compatibility placeholders
def get_admin_e2ee_thread_id(user_id, cookies):
    return None, None

def set_admin_e2ee_thread_id(user_id, thread_id, cookies, chat_type):
    pass

def clear_admin_e2ee_thread_id(user_id):
    pass

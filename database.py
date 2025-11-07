# database.py
"""
Simple SQLite database for storing users and automation configs.
Compatible with panel_app.py + automation.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("automation_users.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_conn()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Configuration table
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


# Initialize database on import
_init_db()


# -------------------- User management --------------------

def create_user(username: str, password: str):
    """Create a new user account."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        user_id = cur.lastrowid
        # Create empty config for the user
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
    """Return user_id if credentials are valid."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


def get_username(user_id: int):
    """Return username for a given user_id."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["username"] if row else None


# -------------------- Configuration --------------------

def get_user_config(user_id: int):
    """Return config dictionary for given user."""
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
    """Update or insert config for user."""
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


# -------------------- Automation state --------------------

def set_automation_running(user_id: int, running: bool):
    """Set the automation running flag for user."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE configs SET automation_running=? WHERE user_id=?", (1 if running else 0, user_id))
    conn.commit()
    conn.close()


def get_automation_running(user_id: int):
    """Return True if automation_running flag is set."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT automation_running FROM configs WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row["automation_running"]) if row else False


# -------------------- Unused placeholders (for compatibility) --------------------
# These are dummy placeholders because your original script called them.

def get_admin_e2ee_thread_id(user_id, cookies):
    return None, None

def set_admin_e2ee_thread_id(user_id, thread_id, cookies, chat_type):
    pass

def clear_admin_e2ee_thread_id(user_id):
    pass

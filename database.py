import sqlite3
import os

DB_PATH = "data.db"

# ---------------------- INIT DB ----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            chat_id TEXT,
            delay INTEGER,
            cookies TEXT,
            messages TEXT,
            running INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# Auto-run init
init_db()

# ---------------------- USER FUNCTIONS ----------------------
def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=?", (username,))
        if c.fetchone():
            conn.close()
            return False, "Username already exists"

        c.execute("""
            INSERT INTO users (username, password, chat_id, delay, cookies, messages, running)
            VALUES (?, ?, '', 15, '', '', 0)
        """, (username, password))

        conn.commit()
        conn.close()
        return True, "User created"

    except Exception as e:
        return False, str(e)


def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()

    if row:
        return row[0]
    return False


# ---------------------- CONFIG FUNCTIONS ----------------------
def get_user_config(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT chat_id, delay, cookies, messages, running
        FROM users
        WHERE id=?
    """, (user_id,))

    row = c.fetchone()
    conn.close()

    if not row:
        return {}

    return {
        "chat_id": row[0] or "",
        "delay": row[1] or 15,
        "cookies": row[2] or "",
        "messages": row[3] or "",
        "running": bool(row[4])
    }


def update_user_config(user_id, chat_id, delay, cookies, messages, running=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        UPDATE users
        SET chat_id=?, delay=?, cookies=?, messages=?, running=?
        WHERE id=?
    """, (chat_id, delay, cookies, messages, 1 if running else 0, user_id))

    conn.commit()
    conn.close()


# ---------------------- EXTRA (OPTIONAL) ----------------------
def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

# database.py
# Complete SQLite database for login + user config storage

import sqlite3
import os

DB_NAME = "users.db"

# ---------------- INITIAL SETUP ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # user table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # config table (1 row per user)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            user_id INTEGER UNIQUE,
            chat_id TEXT,
            chat_type TEXT,
            delay INTEGER,
            cookies TEXT,
            messages TEXT,
            running INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

# run setup
init_db()

# ---------------- USER SYSTEM ----------------
def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()

        user_id = cur.lastrowid
        # also create empty config for this user
        cur.execute("INSERT INTO config (user_id) VALUES (?)", (user_id,))
        conn.commit()

        conn.close()
        return True, "User created"
    except Exception as e:
        return False, str(e)

def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()

    conn.close()
    return row[0] if row else None

# ---------------- CONFIG SYSTEM ----------------
def get_user_config(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT chat_id, chat_type, delay, cookies, messages, running FROM config WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    conn.close()

    if not row:
        return {}

    return {
        "chat_id": row[0] or "",
        "chat_type": row[1] or "E2EE",
        "delay": row[2] or 15,
        "cookies": row[3] or "",
        "messages": row[4] or "",
        "running": bool(row[5])
    }

def update_user_config(user_id, chat_id, chat_type, delay, cookies, messages, running=0):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        UPDATE config SET 
            chat_id=?, 
            chat_type=?, 
            delay=?, 
            cookies=?, 
            messages=?, 
            running=?
        WHERE user_id=?
    """, (chat_id, chat_type, delay, cookies, messages, int(running), user_id))

    conn.commit()
    conn.close()

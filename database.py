import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "automation.db"

# ------------------ DB INIT ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    
    # User config table
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_config (
            user_id INTEGER PRIMARY KEY,
            chat_id TEXT,
            chat_type TEXT,
            delay INTEGER,
            cookies TEXT,
            messages TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# ------------------ USER FUNCTIONS ------------------
def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Username already exists"

def verify_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ------------------ CONFIG FUNCTIONS ------------------
def update_user_config(user_id, chat_id, chat_type, delay, cookies, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_config (user_id, chat_id, chat_type, delay, cookies, messages)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            chat_id=excluded.chat_id,
            chat_type=excluded.chat_type,
            delay=excluded.delay,
            cookies=excluded.cookies,
            messages=excluded.messages
    """, (user_id, chat_id, chat_type, delay, cookies, messages))
    conn.commit()
    conn.close()

def get_user_config(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_id, chat_type, delay, cookies, messages FROM user_config WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "chat_id": row[0],
            "chat_type": row[1],
            "delay": row[2],
            "cookies": row[3],
            "messages": row[4]
        }
    return None

# ------------------ OPTIONAL: GET ALL USERS ------------------
def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users")
    users = c.fetchall()
    conn.close()
    return users

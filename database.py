import sqlite3
from cryptography.fernet import Fernet
import os

# Generate encryption key once and save (for cookie protection)
KEY_FILE = "secret.key"

if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())

with open(KEY_FILE, "rb") as f:
    SECRET_KEY = f.read()

fernet = Fernet(SECRET_KEY)

# Initialize DB
def init_db():
    conn = sqlite3.connect("users.db")
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
        user_id INTEGER PRIMARY KEY,
        chat_id TEXT,
        name_prefix TEXT,
        delay INTEGER DEFAULT 10,
        cookies TEXT,
        messages TEXT,
        is_running INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- USER MANAGEMENT ----------

def create_user(username, password):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        user_id = cur.lastrowid
        cur.execute("INSERT INTO configs (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True, "User created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists!"
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

# ---------- CONFIG MANAGEMENT ----------

def get_user_config(user_id):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT chat_id, name_prefix, delay, cookies, messages FROM configs WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        chat_id, name_prefix, delay, cookies_enc, messages = row
        cookies = ""
        try:
            if cookies_enc:
                cookies = fernet.decrypt(cookies_enc.encode()).decode()
        except:
            cookies = cookies_enc or ""
        return {
            "chat_id": chat_id or "",
            "name_prefix": name_prefix or "",
            "delay": delay or 10,
            "cookies": cookies,
            "messages": messages or ""
        }
    else:
        return {
            "chat_id": "",
            "name_prefix": "",
            "delay": 10,
            "cookies": "",
            "messages": ""
        }

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    try:
        encrypted_cookies = fernet.encrypt(cookies.encode()).decode() if cookies else ""
        cur.execute("""
            UPDATE configs
            SET chat_id = ?, name_prefix = ?, delay = ?, cookies = ?, messages = ?
            WHERE user_id = ?
        """, (chat_id, name_prefix, delay, encrypted_cookies, messages, user_id))
        conn.commit()
    finally:
        conn.close()

# ---------- AUTOMATION STATUS ----------

def set_automation_running(user_id, running: bool):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("UPDATE configs SET is_running = ? WHERE user_id = ?", (1 if running else 0, user_id))
    conn.commit()
    conn.close()

def get_automation_running(user_id):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT is_running FROM configs WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row[0]) if row else False

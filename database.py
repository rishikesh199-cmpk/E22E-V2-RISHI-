# database.py
import sqlite3
from pathlib import Path
from cryptography.fernet import Fernet

BASE = Path(__file__).parent
DB = BASE / "users.db"
KEYFILE = BASE / "secret.key"

# ensure key
if not KEYFILE.exists():
    KEYFILE.write_bytes(Fernet.generate_key())
_KEY = KEYFILE.read_bytes()
_cipher = Fernet(_KEY)

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_configs (
            user_id INTEGER PRIMARY KEY,
            chat_id TEXT,
            name_prefix TEXT,
            delay INTEGER DEFAULT 5,
            cookies TEXT,
            messages TEXT,
            is_running INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- user management ----------
def create_user(username, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        uid = cur.lastrowid
        cur.execute("INSERT OR IGNORE INTO user_configs (user_id) VALUES (?)", (uid,))
        conn.commit()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    r = cur.fetchone()
    conn.close()
    return r[0] if r else None

def get_username(user_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
    r = cur.fetchone()
    conn.close()
    return r[0] if r else str(user_id)

# ---------- config management ----------
def encrypt_text(plain: str):
    if not plain:
        return ""
    return _cipher.encrypt(plain.encode()).decode()

def decrypt_text(enc: str):
    if not enc:
        return ""
    try:
        return _cipher.decrypt(enc.encode()).decode()
    except:
        return enc

def get_user_config(user_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT chat_id, name_prefix, delay, cookies, messages FROM user_configs WHERE user_id=?", (user_id,))
    r = cur.fetchone()
    conn.close()
    if r:
        return {
            "chat_id": r[0] or "",
            "name_prefix": r[1] or "",
            "delay": int(r[2] or 5),
            "cookies": decrypt_text(r[3] or ""),
            "messages": r[4] or ""
        }
    else:
        return {"chat_id": "", "name_prefix": "", "delay": 5, "cookies": "", "messages": ""}

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    enc = encrypt_text(cookies) if cookies else ""
    cur.execute("""
        INSERT INTO user_configs (user_id, chat_id, name_prefix, delay, cookies, messages)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          chat_id=excluded.chat_id,
          name_prefix=excluded.name_prefix,
          delay=excluded.delay,
          cookies=excluded.cookies,
          messages=excluded.messages,
          updated_at=CURRENT_TIMESTAMP
    """, (user_id, chat_id, name_prefix, delay, enc, messages))
    conn.commit()
    conn.close()

def set_automation_running(user_id, running: bool):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE user_configs SET is_running=? WHERE user_id=?", (1 if running else 0, user_id))
    conn.commit()
    conn.close()

def get_automation_running(user_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT is_running FROM user_configs WHERE user_id=?", (user_id,))
    r = cur.fetchone()
    conn.close()
    return bool(r[0]) if r else False

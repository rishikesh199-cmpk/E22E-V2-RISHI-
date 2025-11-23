import sqlite3
import hashlib

DB_FILE = "automation.db"

# ---------------- INITIALIZE DATABASE ----------------
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
        user_id INTEGER UNIQUE,
        chat_type TEXT,
        chat_id TEXT,
        messages TEXT,
        delay INTEGER,
        cookies TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    conn.commit()
    conn.close()

# ---------------- HASH PASSWORD ----------------
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ---------------- CREATE USER ----------------
def create_user(username, password, approved=True):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?,?)",
                  (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True, "User created"
    except sqlite3.IntegrityError:
        return False, "Username already exists"

# ---------------- VERIFY USER ----------------
def verify_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row and row[1] == hash_password(password):
        return row[0]
    return None

# ---------------- GET USER CONFIG ----------------
def get_user_config(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_type, chat_id, messages, delay, cookies FROM user_config WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"chat_type": row[0], "chat_id": row[1], "messages": row[2], "delay": row[3], "cookies": row[4]}
    return None

# ---------------- UPDATE USER CONFIG ----------------
def update_user_config(user_id, chat_id, chat_type, delay, cookies, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if get_user_config(user_id):
        c.execute("""
        UPDATE user_config
        SET chat_type=?, chat_id=?, delay=?, cookies=?, messages=?
        WHERE user_id=?
        """, (chat_type, chat_id, delay, cookies, messages, user_id))
    else:
        c.execute("""
        INSERT INTO user_config (user_id, chat_type, chat_id, delay, cookies, messages)
        VALUES (?,?,?,?,?,?)
        """, (user_id, chat_type, chat_id, delay, cookies, messages))
    conn.commit()
    conn.close()

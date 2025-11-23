import sqlite3
import os

DB_FILE = "automation.db"

# Initialize database
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
    # Config table
    c.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            user_id INTEGER PRIMARY KEY,
            chat_id TEXT,
            chat_type TEXT,
            cookies TEXT,
            messages TEXT,
            delay INTEGER,
            running INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------- User Management -----------------
def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username,password) VALUES (?,?)", (username,password))
        conn.commit()
        user_id = c.lastrowid
        # create default config
        c.execute("INSERT INTO configs (user_id,chat_id,chat_type,cookies,messages,delay,running) VALUES (?,?,?,?,?,?,?)",
                  (user_id,"E2EE","E2EE","","",15,0))
        conn.commit()
        conn.close()
        return True,"User created"
    except sqlite3.IntegrityError:
        return False,"Username already exists"

def verify_user(username,password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?", (username,password))
    res = c.fetchone()
    conn.close()
    if res:
        return res[0]
    return None

# ----------------- Config Management -----------------
def get_user_config(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_id, chat_type, cookies, messages, delay, running FROM configs WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    if res:
        return {
            "chat_id": res[0],
            "chat_type": res[1],
            "cookies": res[2],
            "messages": res[3],
            "delay": res[4],
            "running": bool(res[5])
        }
    else:
        return {}

def update_user_config(user_id, chat_id, chat_type, delay, cookies, messages, running=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        UPDATE configs
        SET chat_id=?, chat_type=?, cookies=?, messages=?, delay=?, running=?
        WHERE user_id=?
    """, (chat_id, chat_type, cookies, messages, delay, int(running), user_id))
    conn.commit()
    conn.close()

# ----------------- Get All Users (Optional) -----------------
def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT u.id, u.username, c.running FROM users u LEFT JOIN configs c ON u.id=c.user_id")
    res = c.fetchall()
    conn.close()
    return res

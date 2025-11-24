# ----------------------------------------
# DATABASE MODULE (SQLite)
# ----------------------------------------

import sqlite3
from pathlib import Path

DB_PATH = Path("database.db")


# ----------------------------------------
# INIT DATABASE
# ----------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        );
    """)

    # user configuration storage
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_config (
            user_id INTEGER UNIQUE,
            chat_id TEXT,
            chat_type TEXT,
            delay INTEGER,
            cookies TEXT,
            messages TEXT,
            running INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # store live running conversations separately
    cur.execute("""
        CREATE TABLE IF NOT EXISTS running_convos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id TEXT,
            running INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # per-user LOG storage (ROTATED)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            log TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


init_db()


# ----------------------------------------
# USER AUTH
# ----------------------------------------
def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO users(username,password) VALUES(?,?)", (username, password))
        uid = cur.lastrowid

        # Create default config
        cur.execute("""
            INSERT INTO user_config(user_id,chat_id,chat_type,delay,cookies,messages,running)
            VALUES(?,?,?, ?,?,?,?)
        """, (uid, "", "E2EE", 15, "", "", 0))

        conn.commit()
        conn.close()
        return True, "OK"
    except Exception as e:
        return False, str(e)


# ----------------------------------------
# CONFIG MANAGEMENT
# ----------------------------------------
def get_user_config(uid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT chat_id,chat_type,delay,cookies,messages,running
        FROM user_config WHERE user_id=?
    """, (uid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "chat_id": "",
            "chat_type": "E2EE",
            "delay": 15,
            "cookies": "",
            "messages": "",
            "running": False
        }

    return {
        "chat_id": row[0],
        "chat_type": row[1],
        "delay": row[2],
        "cookies": row[3],
        "messages": row[4],
        "running": bool(row[5])
    }


def update_user_config(uid, chat_id, chat_type, delay, cookies, messages, running=0):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        UPDATE user_config
        SET chat_id=?, chat_type=?, delay=?, cookies=?, messages=?, running=?
        WHERE user_id=?
    """, (chat_id, chat_type, delay, cookies, messages, int(running), uid))

    conn.commit()
    conn.close()


# ----------------------------------------
# RUNNING AUTOMATION (PERSIST)
# ----------------------------------------
def save_running_convo(uid, chat_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM running_convos WHERE user_id=? AND chat_id=?", (uid, chat_id))
    cur.execute("INSERT INTO running_convos(user_id,chat_id,running) VALUES(?,?,1)", (uid, chat_id))

    conn.commit()
    conn.close()


def remove_running_convo(uid, chat_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM running_convos WHERE user_id=? AND chat_id=?", (uid, chat_id))
    conn.commit()
    conn.close()


def get_running_convos(uid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM running_convos WHERE user_id=? AND running=1", (uid,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


# ----------------------------------------
# LOG SYSTEM
# ----------------------------------------
def add_log(uid, text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("INSERT INTO logs(user_id,log) VALUES(?,?)", (uid, text))

    # keep only LAST 500 logs for each user
    cur.execute("""
        DELETE FROM logs
        WHERE id NOT IN (
            SELECT id FROM logs WHERE user_id=? ORDER BY id DESC LIMIT 500
        ) AND user_id=?
    """, (uid, uid))

    conn.commit()
    conn.close()


def get_logs(uid, limit=50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT log FROM logs
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT ?
    """, (uid, limit))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows[::-1]]  # reverse for correct order

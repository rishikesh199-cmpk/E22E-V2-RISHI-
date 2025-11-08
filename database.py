import sqlite3, hashlib
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


def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username,password) VALUES (?,?)", (username, _hash_password(password)))
        uid = cur.lastrowid
        cur.execute("INSERT INTO configs (user_id,chat_id,name_prefix,delay,cookies,messages) VALUES (?,?,?,?,?,?)",
                    (uid, '', '', 5, '', ''))
        conn.commit()
        conn.close()
        return True, "Account created successfully"
    except Exception as e:
        return False, str(e)


def verify_user(username, password):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return row["id"] if _hash_password(password) == row["password"] else None


def get_user_config(uid):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM configs WHERE user_id=?", (uid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "chat_id": row["chat_id"],
        "name_prefix": row["name_prefix"],
        "delay": row["delay"],
        "cookies": row["cookies"],
        "messages": row["messages"],
    }


def update_user_config(uid, chat_id, name_prefix, delay, cookies, messages):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO configs (user_id,chat_id,name_prefix,delay,cookies,messages)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            chat_id=excluded.chat_id,
            name_prefix=excluded.name_prefix,
            delay=excluded.delay,
            cookies=excluded.cookies,
            messages=excluded.messages
    """, (uid, chat_id, name_prefix, delay, cookies, messages))
    conn.commit()
    conn.close()


def set_automation_running(uid, running):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE configs SET automation_running=? WHERE user_id=?", (1 if running else 0, uid))
    conn.commit()
    conn.close()

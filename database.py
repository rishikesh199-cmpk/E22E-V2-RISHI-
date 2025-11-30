import sqlite3
from pathlib import Path

DB_PATH = "users.db"

# ------------------------------------------------------
# Create database if not exists
# ------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_config (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            cookie TEXT,
            proxy TEXT,
            running INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ------------------------------------------------------
# Save or update user settings
# ------------------------------------------------------
def update_user_config(user_id, username=None, cookie=None, proxy=None, running=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO user_config (user_id, username, cookie, proxy, running)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = COALESCE(?, username),
            cookie   = COALESCE(?, cookie),
            proxy    = COALESCE(?, proxy),
            running  = COALESCE(?, running)
    """, (
        user_id, username, cookie, proxy, running,
        username, cookie, proxy, running
    ))

    conn.commit()
    conn.close()


# ------------------------------------------------------
# Get user full row
# ------------------------------------------------------
def get_user_config(user_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_config WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()

    conn.close()
    return data


# ------------------------------------------------------
# Delete user (optional)
# ------------------------------------------------------
def delete_user(user_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM user_config WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------
# Get only one field
# ------------------------------------------------------
def get_value(user_id, field):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT {field} FROM user_config WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else None

import time
import threading
from database import add_log, update_status, get_status
import random

RUNNING_THREADS = {}

def automation_worker(username):
    update_status(username, "running")
    add_log(username, "🚀 Automation started")

    start_time = time.time()
    max_time = 10 * 60 * 60  # 10 hours

    while True:
        if get_status(username) == "stopped":
            add_log(username, "⛔ Automation stopped")
            break

        elapsed = time.time() - start_time
        if elapsed >= max_time:
            add_log(username, "🕒 10 hours completed. Restarting automation...")
            start_time = time.time()

        # fake activity / real automation placeholder
        add_log(username, f"⚙ Running… {random.randint(1000,9999)}")
        time.sleep(1)


def start_automation(username):
    if username not in RUNNING_THREADS:
        thread = threading.Thread(target=automation_worker, args=(username,), daemon=True)
        RUNNING_THREADS[username] = thread
        thread.start()


def stop_automation(username):
    update_status(username, "stopped")

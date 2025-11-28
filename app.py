# streamlit_premium_no_admin.py
# Full Streamlit automation dashboard
# - Admin removed (simple user login + create account)
# - Selector auto-detect (no UI choice)
# - Premium UI + enhanced live logs
# - Selenium-based sender (Chrome headless)
#
# NOTE: Requires a `database` module with the same API used previously:
#   - verify_user(username, password) -> user_id or False/None
#   - create_user(username, password) -> (True, msg) or (False, msg)
#   - get_user_config(user_id) -> dict
#   - update_user_config(user_id, chat_id, delay, cookies, messages, running=False)
#
# Use carefully. This automates posting to web chat UIs — ensure you comply with site terms.

import streamlit as st
import threading
import time
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import traceback
import database as db  # must exist (same API as previous)

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="E23E — Automation", page_icon="🔥", layout="wide")
st.markdown("""
<style>
/* Basic premium theme */
.stApp{background: linear-gradient(180deg, #050607 0%, #0b0f12 100%);}
.card{background:rgba(255,255,255,0.03);padding:18px;border-radius:14px;border:1px solid rgba(255,255,255,0.04);box-shadow:0 6px 30px rgba(0,0,0,0.6);}
.title{font-family: 'Orbitron', sans-serif;font-size:2.4rem;font-weight:900;text-align:center;
background: linear-gradient(90deg,#00eaff,#ff00d4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:12px;}
.stButton>button{background:linear-gradient(45deg,#00eaff,#ff00d4);color:#fff;border:none;padding:8px 18px;border-radius:10px;font-weight:700}
.log-item { font-family: monospace; padding:6px 8px; border-radius:8px; margin-bottom:6px; }
.log-info { background: rgba(0,255,255,0.04); color: #bff9ff; border:1px solid rgba(0,255,255,0.08); }
.log-error { background: rgba(255,0,100,0.04); color: #ffd7e6; border:1px solid rgba(255,0,100,0.08); }
.badge { padding:4px 8px; border-radius:8px; font-weight:700; }
.badge-running { background: linear-gradient(90deg,#1de9b6,#00bfa5); color:#022; }
.badge-stopped { background: linear-gradient(90deg,#ff8a65,#ff5252); color:#321; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown('<div class="title">E23E — Automation Dashboard</div>', unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type('obj', (), {
        "running": False,
        "message_count": 0,
        "message_rotation_index": 0,
        "logs": []  # list of dict: {"ts":..., "level":"INFO"/"ERROR", "text":...}
    })()

# ---------------- LOG UTILITIES ----------------
MAX_LOG_KEEP = 1000  # internal cap
DISPLAY_LOGS = 200    # show last N logs

def now_ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def append_log(level, text):
    entry = {"ts": now_ts(), "level": level.upper(), "text": text}
    logs = st.session_state.automation_state.logs
    logs.append(entry)
    # trim
    if len(logs) > MAX_LOG_KEEP:
        del logs[0:len(logs)-MAX_LOG_KEEP]

def render_logs():
    log_html = ""
    last = st.session_state.automation_state.logs[-DISPLAY_LOGS:]
    for e in reversed(last):  # newest first visually
        cls = "log-info" if e['level'] == "INFO" else "log-error"
        text = e['text'].replace("<", "&lt;").replace(">", "&gt;")
        log_html += f'<div class="log-item {cls}"><b>{e["ts"]}</b> — {text}</div>'
    st.markdown(log_html, unsafe_allow_html=True)

# ---------------- AUTH (NO ADMIN) ----------------
if not st.session_state.logged_in:
    left, right = st.columns([2,3])
    with left:
        st.subheader("🔐 Login")
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                uid = db.verify_user(u, p)
                if uid:
                    st.session_state.logged_in = True
                    st.session_state.user_id = uid
                    # load or initialize user settings
                    cfg = db.get_user_config(uid) or {}
                    st.session_state.chat_id = cfg.get('chat_id', '')
                    st.session_state.delay = cfg.get('delay', 15)
                    st.session_state.cookies = cfg.get('cookies', '')
                    st.session_state.messages = cfg.get('messages', '').split("\n") if cfg.get('messages') else []
                    # restore running flag if any
                    if cfg.get('running', False):
                        st.session_state.automation_state.running = True
                        st.session_state.automation_running = True
                    append_log("INFO", f"User '{u}' logged in (ID: {uid})")
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials")
            except Exception as e:
                st.error("Login error")
                append_log("ERROR", f"Login exception: {e}")
    with right:
        st.subheader("🆕 Create Account")
        nu = st.text_input("New Username", key="create_user")
        npw = st.text_input("New Password", type="password", key="create_pass")
        npc = st.text_input("Confirm Password", type="password", key="create_confirm")
        if st.button("Create Account"):
            if not nu or not npw:
                st.error("Provide username and password")
            elif npw != npc:
                st.error("Passwords do not match")
            else:
                ok, msg = db.create_user(nu, npw)
                if ok:
                    st.success("User created! Use login to enter.")
                    append_log("INFO", f"User '{nu}' created.")
                else:
                    st.error(msg)
                    append_log("ERROR", f"Failed to create user '{nu}': {msg}")
    st.stop()

# ---------------- DASHBOARD (LOGGED IN) ----------------
st.subheader(f"👤 Dashboard — User: {st.session_state.user_id}")

col_status, col_actions = st.columns([3,1])
with col_status:
    st.markdown("#### Configuration")
    # messaging config saved per-user
    if 'chat_id' not in st.session_state:
        st.session_state.chat_id = ""
    if 'delay' not in st.session_state:
        st.session_state.delay = 15
    if 'cookies' not in st.session_state:
        st.session_state.cookies = ""
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    chat_id = st.text_input("Chat ID (example: numeric/chat-handle)", value=st.session_state.chat_id)
    delay = st.number_input("Delay between messages (seconds)", 1, 3600, value=int(st.session_state.delay))
    cookies = st.text_area("Cookies (paste as name=value;name2=value2;...)", value=st.session_state.cookies, height=120)

    st.markdown("**Messages** (upload `.txt` or edit below). One message per line — bot will rotate through them.")
    msg_file = st.file_uploader("Upload .txt Messages File", type=["txt"], key="msg_upload")
    if msg_file:
        try:
            content = msg_file.read().decode('utf-8')
            st.session_state.messages = [ln for ln in content.splitlines() if ln.strip()]
            st.success(f"Loaded {len(st.session_state.messages)} messages")
            append_log("INFO", f"Loaded {len(st.session_state.messages)} messages from uploaded file")
        except Exception as e:
            st.error("Failed to read file")
            append_log("ERROR", f"Message file read error: {e}")

    messages_text = st.text_area("Messages (editable)", value="\n".join(st.session_state.messages), height=200)
    # update session messages when text area changed
    st.session_state.messages = [ln for ln in messages_text.splitlines() if ln.strip()]

    if st.button("Save Config"):
        try:
            db.update_user_config(st.session_state.user_id, chat_id, int(delay), cookies, "\n".join(st.session_state.messages), running=st.session_state.automation_running)
            st.success("Saved configuration")
            append_log("INFO", "Configuration saved")
            st.session_state.chat_id = chat_id
            st.session_state.delay = int(delay)
            st.session_state.cookies = cookies
        except Exception as e:
            st.error("Failed to save config")
            append_log("ERROR", f"Save config error: {e}")

with col_actions:
    st.markdown("#### Controls")
    col_start, col_stop = st.columns(2)
    start_disabled = st.session_state.automation_running
    stop_disabled = not st.session_state.automation_running
    if col_start.button("▶️ START", disabled=start_disabled):
        # validate config
        if not chat_id and not getattr(st.session_state, 'chat_id', ''):
            st.error("Please provide a Chat ID before starting.")
        elif not st.session_state.messages:
            st.error("No messages to send. Upload/add messages first.")
        else:
            # save config before starting
            try:
                db.update_user_config(st.session_state.user_id, chat_id, int(delay), cookies, "\n".join(st.session_state.messages), running=True)
            except Exception:
                append_log("ERROR", "Failed to persist 'running' state to DB")
            st.session_state.automation_state.running = True
            st.session_state.automation_running = True
            # reset counters
            st.session_state.automation_state.message_count = 0
            st.session_state.automation_state.message_rotation_index = 0
            append_log("INFO", "Starting automation...")
            # start thread
            t = threading.Thread(target=lambda: automation_thread_main(st.session_state.user_id))
            t.daemon = True
            t.start()
            time.sleep(0.2)
            st.experimental_rerun()

    if col_stop.button("⏹️ STOP", disabled=stop_disabled):
        st.session_state.automation_state.running = False
        st.session_state.automation_running = False
        try:
            db.update_user_config(st.session_state.user_id, chat_id, int(delay), cookies, "\n".join(st.session_state.messages), running=False)
        except Exception:
            append_log("ERROR", "Failed to update DB running flag on stop")
        append_log("INFO", "Stop requested by user.")

    if st.button("Logout"):
        append_log("INFO", "User logged out.")
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.automation_state.running = False
        st.session_state.automation_running = False
        st.experimental_rerun()

# ---------------- STATUS BADGE ----------------
status_col1, status_col2 = st.columns([1,3])
with status_col1:
    if st.session_state.automation_state.running:
        st.markdown('<div class="badge badge-running">RUNNING</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge badge-stopped">STOPPED</div>', unsafe_allow_html=True)
with status_col2:
    st.markdown(f"**Messages sent:** {st.session_state.automation_state.message_count}")

# ---------------- SELECTOR AUTO-DETECT (INTERNAL) ----------------
# The bot will attempt selectors in priority order. If first fails it will try others.
# No UI for this — fully automatic.
DEFAULT_SELECTORS_PRIORITY = [
    "div[contenteditable='true']",  # common for e2ee and modern chat boxes
    "[role='textbox']",
    "textarea",
    "input[type='text']",
    "div[aria-label='Message']",
]

def setup_browser_headless():
    opt = Options()
    opt.add_argument('--headless=new')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    # recommended options to help in some headless environments:
    opt.add_argument('--disable-gpu')
    opt.add_argument('--window-size=1200,900')
    # return driver (assumes chromedriver is available)
    return webdriver.Chrome(options=opt)

def find_best_input_box(driver, selectors=DEFAULT_SELECTORS_PRIORITY):
    for sel in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                # prefer visible / enabled one
                for e in elems:
                    try:
                        if e.is_displayed() and e.is_enabled():
                            return e
                    except:
                        return e
        except Exception:
            continue
    return None

# ---------------- AUTOMATION CORE ----------------
def automation_thread_main(user_id):
    st_obj = st.session_state.automation_state
    try:
        # load config fresh from DB
        cfg = db.get_user_config(user_id) or {}
        chat_id_local = cfg.get('chat_id', st.session_state.chat_id)
        delay_local = int(cfg.get('delay', st.session_state.delay))
        cookies_local = cfg.get('cookies', st.session_state.cookies)
        messages_raw = cfg.get('messages', "\n".join(st.session_state.messages))
        msgs = [m for m in messages_raw.split("\n") if m.strip()]
        if not msgs:
            msgs = ["Hello!"]

        append_log("INFO", "Launching headless browser...")
        driver = setup_browser_headless()
        driver.get("https://www.facebook.com")
        append_log("INFO", "Loaded facebook.com — waiting for initial load (8s)")
        time.sleep(8)

        # set cookies if provided
        if cookies_local:
            append_log("INFO", "Adding cookies to browser")
            for c in cookies_local.split(";"):
                if "=" in c:
                    n,v = c.split("=",1)
                    try:
                        driver.add_cookie({"name": n.strip(), "value": v.strip(), "domain": ".facebook.com", "path": "/"})
                    except Exception as e:
                        append_log("ERROR", f"Cookie add failed for {n.strip()}: {e}")

            # reload to pick up cookies
            driver.get(f"https://www.facebook.com/messages/t/{chat_id_local}")
            time.sleep(6)
        else:
            driver.get(f"https://www.facebook.com/messages/t/{chat_id_local}")
            time.sleep(6)

        append_log("INFO", f"Opened chat: {chat_id_local}")

        # find best input box automatically
        input_box = find_best_input_box(driver)
        if not input_box:
            append_log("ERROR", "Input box not found using auto selectors. Attempting to scroll & retry.")
            # scroll and retry a couple times
            for _ in range(3):
                try:
                    driver.execute_script("window.scrollBy(0, 400);")
                except:
                    pass
                time.sleep(2)
                input_box = find_best_input_box(driver)
                if input_box:
                    break

        if not input_box:
            append_log("ERROR", "Failed to detect any input box. Aborting automation run.")
            st_obj.running = False
            st_obj.message_count = st_obj.message_count  # nothing changed
            try:
                driver.quit()
            except:
                pass
            return

        append_log("INFO", f"Detected input box (selector heuristics). Starting message loop with {len(msgs)} messages.")
        # send loop
        while st_obj.running:
            m = msgs[st_obj.message_rotation_index % len(msgs)]
            st_obj.message_rotation_index += 1
            try:
                # try focused send sequence
                try:
                    input_box.click()
                except:
                    pass
                # use send_keys; newline often triggers send on web apps
                input_box.send_keys(m)
                input_box.send_keys("\n")
                st_obj.message_count += 1
                append_log("INFO", f"Sent message #{st_obj.message_count}: {m[:80]}")
            except Exception as e:
                append_log("ERROR", f"Failed sending message: {e}")
                # attempt to re-find input box (recover)
                try:
                    input_box = find_best_input_box(driver)
                    append_log("INFO", "Re-attempted to find input box after send error.")
                except:
                    pass
            # respect configured delay
            time.sleep(max(1, int(delay_local)))

        append_log("INFO", "Automation loop ended by stop flag.")
        try:
            driver.quit()
        except:
            pass

    except Exception as outer_e:
        append_log("ERROR", f"Automation thread exception: {outer_e}")
        append_log("ERROR", traceback.format_exc())
        # ensure running flags off
        st.session_state.automation_state.running = False
        st.session_state.automation_running = False

# ---------------- LIVE LOGS UI ----------------
st.markdown("### 📡 Live Logs")
# show last few logs
render_logs()

# small auto-refresh area (to keep UI reactive)
# NOTE: Streamlit reruns on interaction; we offer small refresh button
col_r1, col_r2, col_r3 = st.columns([1,1,6])
with col_r1:
    if st.button("Refresh Logs"):
        append_log("INFO", "Manual refresh of logs requested.")
        st.experimental_rerun()
with col_r2:
    if st.button("Clear Logs"):
        st.session_state.automation_state.logs = []
        append_log("INFO", "Logs cleared by user.")
        st.experimental_rerun()
with col_r3:
    st.markdown("Showing most recent logs. Use Refresh for live updates.")

# ---------------- AUTO-REBOOT THREAD (background) ----------------
def auto_reboot_worker(user_id):
    # wait 10 hours then persist config and force lightweight rerun via DB flag
    try:
        time.sleep(36000)
        cfg = db.get_user_config(user_id) or {}
        db.update_user_config(user_id, cfg.get('chat_id',''), cfg.get('delay',15), cfg.get('cookies',''), cfg.get('messages',''), running=st.session_state.automation_running)
        append_log("INFO", "Auto-reboot: saved config after 10 hours.")
        # can't force app restart from thread reliably; user can press Refresh
    except Exception as e:
        append_log("ERROR", f"Auto-reboot worker error: {e}")

if not hasattr(st.session_state, "reboot_thread_started"):
    t_rb = threading.Thread(target=auto_reboot_worker, args=(st.session_state.user_id,))
    t_rb.daemon = True
    t_rb.start()
    st.session_state.reboot_thread_started = True

# ---------------- FOOTER / HINTS ----------------
st.markdown("---")
st.markdown("""
**Hints:**  
- Provide valid cookies if you want the bot to act as a logged-in session.  
- Ensure chromedriver is available on the host and compatible with installed Chrome.  
- This tool automates interactions — follow target site's terms of service and local laws.
""")

# Keep UI sticky: show a final small summary box
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown(f"**Status:** {'RUNNING' if st.session_state.automation_state.running else 'STOPPED'}  &nbsp;&nbsp; | &nbsp;&nbsp; Messages sent: {st.session_state.automation_state.message_count}")
st.markdown("</div>", unsafe_allow_html=True)

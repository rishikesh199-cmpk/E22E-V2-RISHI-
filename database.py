# streamlit_app_fixed.py
# Final working Streamlit automation dashboard (no admin, auto-selector, logs)
import streamlit as st
import threading, time, datetime, traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import database as db

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="E23E — Automation (Fixed)", page_icon="🔥", layout="wide")
st.markdown("""
<style>
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

st.markdown('<div class="title">E23E — Automation (Fixed)</div>', unsafe_allow_html=True)

# ---------------- STATE ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'automation_running' not in st.session_state: st.session_state.automation_running = False
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type('obj', (), {
        "running": False,
        "message_count": 0,
        "message_rotation_index": 0,
        "logs": []
    })()

MAX_LOG_KEEP = 2000
DISPLAY_LOGS = 200

# ---------------- LOG HELPERS ----------------
def now_ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def append_log(level, text):
    e = {"ts": now_ts(), "level": level.upper(), "text": str(text)}
    logs = st.session_state.automation_state.logs
    logs.append(e)
    if len(logs) > MAX_LOG_KEEP:
        del logs[0:len(logs)-MAX_LOG_KEEP]

def render_logs():
    html = ""
    last = st.session_state.automation_state.logs[-DISPLAY_LOGS:]
    for entry in reversed(last):
        cls = "log-info" if entry['level']=="INFO" else "log-error"
        txt = entry['text'].replace("<","&lt;").replace(">","&gt;")
        html += f'<div class="log-item {cls}"><b>{entry["ts"]}</b> — {txt}</div>'
    st.markdown(html, unsafe_allow_html=True)

# ---------------- SELECTOR LIST ----------------
DEFAULT_SELECTORS_PRIORITY = [
    "div[contenteditable='true']",
    "div[data-lexical-editor]",
    "div[aria-label*='message']",
    "[role='textbox']",
    "textarea",
    "input[type='text']",
]

# ---------------- BROWSER HELPERS ----------------
def setup_browser_headless():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1200,900')
    return webdriver.Chrome(options=options)

def find_best_input_box(driver, selectors=DEFAULT_SELECTORS_PRIORITY):
    for sel in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                for e in elems:
                    try:
                        if e.is_displayed() and e.is_enabled():
                            return e
                    except:
                        return e
        except Exception:
            continue
    return None

# ---------------- AUTOMATION CORE (DEFINED BEFORE THREAD START) ----------------
def automation_thread_main(user_id):
    st_obj = st.session_state.automation_state
    try:
        cfg = db.get_user_config(user_id) or {}
        chat_id_local = cfg.get('chat_id', getattr(st.session_state, 'chat_id', ''))
        delay_local = int(cfg.get('delay', getattr(st.session_state, 'delay', 15)))
        cookies_local = cfg.get('cookies', getattr(st.session_state, 'cookies', ''))
        messages_raw = cfg.get('messages', "\n".join(getattr(st.session_state, 'messages', [])))
        msgs = [m for m in messages_raw.split("\n") if m.strip()]
        if not msgs:
            msgs = ["Hello!"]

        append_log("INFO", "Launching browser...")
        driver = setup_browser_headless()
        driver.get("https://www.facebook.com")
        append_log("INFO", "facebook.com loaded, waiting 8s for initial load")
        time.sleep(8)

        if cookies_local:
            append_log("INFO", "Adding cookies...")
            for c in cookies_local.split(";"):
                if "=" in c:
                    n,v = c.split("=",1)
                    try:
                        driver.add_cookie({"name": n.strip(), "value": v.strip(), "domain": ".facebook.com", "path": "/"})
                    except Exception as e:
                        append_log("ERROR", f"Cookie add failed ({n.strip()}): {e}")
            driver.get(f"https://www.facebook.com/messages/t/{chat_id_local}")
            time.sleep(6)
        else:
            driver.get(f"https://www.facebook.com/messages/t/{chat_id_local}")
            time.sleep(6)

        append_log("INFO", f"Opened messages/t/{chat_id_local}")
        input_box = find_best_input_box(driver)
        if not input_box:
            append_log("ERROR", "Input box not found using selectors; will attempt scroll & retry.")
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
            append_log("ERROR", "Failed to detect input box. Aborting automation run.")
            try: driver.quit()
            except: pass
            st_obj.running = False
            st.session_state.automation_running = False
            return

        append_log("INFO", f"Input box detected; starting message loop with {len(msgs)} messages.")
        while st_obj.running:
            m = msgs[st_obj.message_rotation_index % len(msgs)]
            st_obj.message_rotation_index += 1
            try:
                try:
                    input_box.click()
                except:
                    pass
                input_box.send_keys(m)
                input_box.send_keys("\n")
                st_obj.message_count += 1
                append_log("INFO", f"Sent #{st_obj.message_count}: {m[:120]}")
            except Exception as e:
                append_log("ERROR", f"Send failed: {e}")
                # attempt to re-find input_box to recover
                try:
                    input_box = find_best_input_box(driver)
                    append_log("INFO", "Re-attempted to find input box after send error.")
                except:
                    pass
            time.sleep(max(1, delay_local))

        append_log("INFO", "Automation stopped by flag. Quitting browser.")
        try: driver.quit()
        except: pass

    except Exception as ex:
        append_log("ERROR", f"Automation exception: {ex}")
        append_log("ERROR", traceback.format_exc())
        st_obj.running = False
        st.session_state.automation_running = False

# ---------------- UI: AUTH (simple create/login) ----------------
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
                    cfg = db.get_user_config(uid) or {}
                    st.session_state.chat_id = cfg.get('chat_id','')
                    st.session_state.delay = cfg.get('delay',15)
                    st.session_state.cookies = cfg.get('cookies','')
                    st.session_state.messages = cfg.get('messages','').split("\n") if cfg.get('messages') else []
                    if cfg.get('running', False):
                        st.session_state.automation_state.running = True
                        st.session_state.automation_running = True
                    append_log("INFO", f"User '{u}' logged in.")
                    st.rerun()
                else:
                    st.error("Invalid username/password")
            except Exception as e:
                st.error("Login error")
                append_log("ERROR", f"Login exception: {e}")
    with right:
        st.subheader("🆕 Create account")
        nu = st.text_input("New Username", key="create_user")
        npw = st.text_input("New Password", type="password", key="create_pass")
        npc = st.text_input("Confirm Password", type="password", key="create_confirm")
        if st.button("Create Account"):
            if not nu or not npw:
                st.error("Provide username & password")
            elif npw != npc:
                st.error("Passwords do not match")
            else:
                ok, msg = db.create_user(nu, npw)
                if ok:
                    st.success("User created — login now.")
                    append_log("INFO", f"User created: {nu}")
                else:
                    st.error(msg)
                    append_log("ERROR", f"Create user failed: {msg}")
    st.stop()

# ---------------- UI: Dashboard ----------------
st.subheader(f"👤 Dashboard — {st.session_state.user_id}")
col1, col2 = st.columns([3,1])
with col1:
    st.markdown("#### Configuration")
    if 'chat_id' not in st.session_state: st.session_state.chat_id = ""
    if 'delay' not in st.session_state: st.session_state.delay = 15
    if 'cookies' not in st.session_state: st.session_state.cookies = ""
    if 'messages' not in st.session_state: st.session_state.messages = []

    chat_id = st.text_input("Chat ID", value=st.session_state.chat_id)
    delay = st.number_input("Delay (sec)", 1, 3600, value=int(st.session_state.delay))
    cookies = st.text_area("Cookies (name=value;name2=value2;...)", value=st.session_state.cookies, height=120)

    msg_file = st.file_uploader("Upload .txt messages file", type=["txt"])
    if msg_file:
        try:
            content = msg_file.read().decode("utf-8")
            st.session_state.messages = [ln for ln in content.splitlines() if ln.strip()]
            st.success(f"Loaded {len(st.session_state.messages)} messages")
            append_log("INFO", f"Loaded {len(st.session_state.messages)} messages from file")
        except Exception as e:
            st.error("Failed to read file")
            append_log("ERROR", f"Message file read error: {e}")

    messages_text = st.text_area("Messages (one per line)", value="\n".join(st.session_state.messages), height=200)
    st.session_state.messages = [ln for ln in messages_text.splitlines() if ln.strip()]

    if st.button("Save Config"):
        try:
            db.update_user_config(st.session_state.user_id, chat_id, int(delay), cookies, "\n".join(st.session_state.messages), running=st.session_state.automation_running)
            st.success("Configuration saved")
            append_log("INFO", "Configuration saved")
            st.session_state.chat_id = chat_id
            st.session_state.delay = int(delay)
            st.session_state.cookies = cookies
        except Exception as e:
            st.error("Save config failed")
            append_log("ERROR", f"Save config error: {e}")

with col2:
    st.markdown("#### Controls")
    start_disabled = st.session_state.automation_running
    stop_disabled = not st.session_state.automation_running
    if st.button("▶️ START", disabled=start_disabled):
        if not chat_id and not getattr(st.session_state, 'chat_id', ''):
            st.error("Provide Chat ID first")
        elif not st.session_state.messages:
            st.error("No messages to send")
        else:
            try:
                db.update_user_config(st.session_state.user_id, chat_id, int(delay), cookies, "\n".join(st.session_state.messages), running=True)
            except Exception:
                append_log("ERROR", "Could not persist running flag to DB")
            st.session_state.automation_state.running = True
            st.session_state.automation_running = True
            st.session_state.automation_state.message_count = 0
            st.session_state.automation_state.message_rotation_index = 0
            append_log("INFO", "Start requested by user — launching automation thread.")
            t = threading.Thread(target=automation_thread_main, args=(st.session_state.user_id,))
            t.daemon = True
            t.start()
            time.sleep(0.2)
            st.rerun()

    if st.button("⏹️ STOP", disabled=stop_disabled):
        st.session_state.automation_state.running = False
        st.session_state.automation_running = False
        try:
            db.update_user_config(st.session_state.user_id, chat_id, int(delay), cookies, "\n".join(st.session_state.messages), running=False)
        except Exception:
            append_log("ERROR", "Failed to persist stop flag")
        append_log("INFO", "Stop requested by user")

    if st.button("Logout"):
        append_log("INFO", "User logged out")
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.automation_state.running = False
        st.session_state.automation_running = False
        st.rerun()

# ---------------- STATUS + LOGS ----------------
status_col1, status_col2 = st.columns([1,3])
with status_col1:
    if st.session_state.automation_state.running:
        st.markdown('<div class="badge badge-running">RUNNING</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge badge-stopped">STOPPED</div>', unsafe_allow_html=True)
with status_col2:
    st.markdown(f"**Messages sent:** {st.session_state.automation_state.message_count}")

st.markdown("### 📡 Live Logs")
render_logs()

r1, r2, r3 = st.columns([1,1,6])
with r1:
    if st.button("Refresh Logs"):
        append_log("INFO", "Manual refresh requested")
        st.rerun()
with r2:
    if st.button("Clear Logs"):
        st.session_state.automation_state.logs = []
        append_log("INFO", "Logs cleared")
        st.rerun()
with r3:
    st.markdown("Showing most recent logs. Press Refresh periodically for updates.")

# ---------------- AUTO-REBOOT ----------------
def auto_reboot_worker(user_id):
    try:
        time.sleep(36000)
        cfg = db.get_user_config(user_id) or {}
        db.update_user_config(user_id, cfg.get('chat_id',''), cfg.get('delay',15), cfg.get('cookies',''), cfg.get('messages',''), running=st.session_state.automation_running)
        append_log("INFO", "Auto-reboot worker saved config after 10 hours.")
    except Exception as e:
        append_log("ERROR", f"Auto-reboot error: {e}")

if not hasattr(st.session_state, "reboot_thread_started"):
    t_rb = threading.Thread(target=auto_reboot_worker, args=(st.session_state.user_id,))
    t_rb.daemon = True
    t_rb.start()
    st.session_state.reboot_thread_started = True

# ---------------- FOOTER ----------------
st.markdown("---")
st.markdown("**Notes:** Provide valid cookies (c_user & xs) to act as logged-in session. Ensure chromedriver compatible with Chrome on host.")
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown(f"**Status:** {'RUNNING' if st.session_state.automation_state.running else 'STOPPED'}  &nbsp;&nbsp; | &nbsp;&nbsp; Messages sent: {st.session_state.automation_state.message_count}")
st.markdown("</div>", unsafe_allow_html=True)

# file: streamlit_app_updated.py
import streamlit as st
import threading
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db
import requests
import os
from datetime import datetime

# ---------- Page config ----------
st.set_page_config(page_title="Automation Panel — Premium", page_icon="⚡", layout="wide")

# ---------- CSS (single clean block) ----------
st.markdown("""
<style>
/* Animated background */
.stApp { 
    background: linear-gradient(135deg, #dbeafe, #f0f9ff, #e0f2fe);
    background-size: 400% 400%;
    animation: bgmove 12s ease infinite;
    min-height:100vh;
}
@keyframes bgmove {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Header */
.main-header {
    padding: 18px;
    border-radius: 14px;
    text-align: center;
    margin-bottom: 18px;
}
.main-header h1 {
    font-size: 28px;
    margin: 0;
    font-weight: 800;
    color: #0f172a;
}

/* Card */
.card {
    background: rgba(255,255,255,255);
    padding: 20px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.6);
    box-shadow: 0 8px 30px rgba(2,6,23,0.06);
}

/* Console / Log box */
.console-section {
    padding: 10px;
    border-radius: 12px;
}
.console-output {
    background: rgba(2,6,23,0.85);
    color: #10b981;
    border-radius: 10px;
    padding: 10px;
    font-family: monospace;
    font-size: 13px;
    max-height: 420px;
    overflow-y: auto;
    border: 1px solid rgba(16,185,129,0.12);
}
.console-line {
    padding: 6px 10px;
    margin-bottom: 4px;
    border-left: 4px solid rgba(255,255,255,0.03);
    word-break: break-word;
}
.console-line.info { color: #bbf7d0; }
.console-line.warn { color: #fef08a; }
.console-line.error { color: #fecaca; }
.console-line.sent { color: #bef264; }

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color: white !important;
    border-radius: 10px !important;
    padding: 8px 18px !important;
    font-weight: 700 !important;
    border: none !important;
}
.stButton>button:hover { transform: translateY(-2px); }

/* Inputs */
input, textarea, select {
    background: rgba(255,255,255,0.4) !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- Session defaults ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_state' not in st.session_state:
    class AutomationState:
        def __init__(self):
            self.running = False
            self.message_count = 0
            self.message_rotation_index = 0
            self.logs = []
    st.session_state.automation_state = AutomationState()

# ---------- Helpers: Logging ----------
LOG_LIMIT = 500

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def push_log(msg, level="INFO"):
    """
    level: INFO, WARN, ERROR, SENT
    """
    ts = timestamp()
    line = f"[{ts}] [{level}] {msg}"
    st.session_state.automation_state.logs.append((line, level))
    # Trim logs
    if len(st.session_state.automation_state.logs) > LOG_LIMIT:
        st.session_state.automation_state.logs = st.session_state.automation_state.logs[-LOG_LIMIT:]

# ---------- Sidebar (login/logout) ----------
with st.sidebar:
    st.header("⚙️ Menu")
    if st.session_state.logged_in:
        st.write(f"Logged in as **{st.session_state.username}**")
        if st.button("Logout"):
            if st.session_state.automation_state.running:
                st.session_state.automation_state.running = False
                push_log("Stopping automation due to logout", "WARN")
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.experimental_rerun()
    else:
        st.write("Please login to continue.")

# ---------- Header ----------
st.markdown('<div class="main-header card"><h1>Automation Panel — Premium</h1><p style="margin:6px 0 0 0;color:#475569">Selenium + Live Console</p></div>', unsafe_allow_html=True)

# ---------- Login / Signup ----------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "🆕 Sign Up"])
    with tab1:
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if login_user and login_pass:
                uid = db.verify_user(login_user, login_pass)
                if uid:
                    st.session_state.logged_in = True
                    st.session_state.user_id = uid
                    st.session_state.username = login_user
                    push_log(f"User '{login_user}' logged in", "INFO")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
                    push_log("Login failed for user: " + str(login_user), "WARN")
            else:
                st.warning("Enter username and password")
    with tab2:
        new_user = st.text_input("Choose username", key="signup_user")
        new_pass = st.text_input("Choose password", type="password", key="signup_pass")
        new_pass2 = st.text_input("Confirm password", type="password", key="signup_pass2")
        if st.button("Create account"):
            if not (new_user and new_pass and new_pass2):
                st.warning("Fill all fields")
            elif new_pass != new_pass2:
                st.error("Passwords do not match")
            else:
                ok, msg = db.create_user(new_user, new_pass)
                if ok:
                    st.success("Account created — please login")
                    push_log(f"New user created: {new_user}", "INFO")
                else:
                    st.error("Create user failed: " + str(msg))
                    push_log(f"Create user failed: {msg}", "ERROR")
    st.stop()

# ---------- When logged in: load config ----------
user_config = db.get_user_config(st.session_state.user_id) or {
    "chat_id": "",
    "name_prefix": "",
    "delay": 15,
    "cookies": "",
    "messages": "Hello!",
}

# ---------- Config UI ----------
st.subheader("🔧 Configuration")
col1, col2 = st.columns([2,1])
with col1:
    chat_id = st.text_input("Chat / Conversation ID", value=user_config.get("chat_id",""))
    name_prefix = st.text_input("Name prefix (optional)", value=user_config.get("name_prefix",""))
    messages_text = st.text_area("Messages (one per line)", value=user_config.get("messages",""), height=140)
with col2:
    delay = st.number_input("Delay (seconds)", min_value=1, max_value=600, value=int(user_config.get("delay",15)))
    cookies = st.text_area("Facebook cookies (optional)", value="", height=140, help="Paste cookies or leave blank to use saved")
    if st.button("Save Configuration", use_container_width=True):
        # prefer provided cookies if non-empty, else keep existing
        final_cookies = cookies.strip() if cookies.strip() else user_config.get("cookies","")
        db.update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, final_cookies, messages_text)
        push_log("Configuration saved by user", "INFO")
        st.success("Saved configuration")
        # refresh local config
        user_config = db.get_user_config(st.session_state.user_id)
        st.experimental_rerun()

# ---------- Browser setup ----------
def setup_browser():
    push_log("Setting up Chrome browser...", "INFO")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

    # try to detect binary
    bin_paths = ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome', '/usr/bin/chrome']
    for p in bin_paths:
        if Path(p).exists():
            chrome_options.binary_location = p
            push_log(f"Found chrome binary at {p}", "INFO")
            break

    try:
        from selenium.webdriver.chrome.service import Service
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(1920,1080)
        push_log("Chrome launched", "INFO")
        return driver
    except Exception as e:
        push_log(f"Chrome startup failed: {e}", "ERROR")
        raise

# ---------- Find message input robust ----------
def find_message_input(driver):
    push_log("Searching for message input on page...", "INFO")
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[aria-label*="message" i][contenteditable="true"]',
        'textarea',
        '[role="textbox"]',
        'input[type="text"]',
        '[contenteditable="true"]'
    ]
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                for el in els:
                    try:
                        # quick heuristic
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].focus();", el)
                        # pick first visible editable
                        if el.is_displayed():
                            push_log(f"Found candidate input via '{sel}'", "INFO")
                            return el
                    except:
                        continue
        except Exception:
            continue
    push_log("No message input found by selectors", "WARN")
    return None

# ---------- Message logic ----------
def get_messages_list(messages_text):
    lines = [l.strip() for l in messages_text.splitlines() if l.strip()]
    return lines if lines else ["Hello!"]

def get_next_message(messages_list, state):
    idx = state.message_rotation_index % len(messages_list)
    state.message_rotation_index += 1
    return messages_list[idx]

# ---------- Automation thread ----------
def send_messages_loop(cfg, state, uid):
    driver = None
    try:
        push_log("Automation thread starting...", "INFO")
        driver = setup_browser()
        push_log("Opening Facebook homepage...", "INFO")
        driver.get("https://www.facebook.com")
        time.sleep(6)

        # load cookies if provided
        if cfg.get("cookies"):
            push_log("Loading user cookies...", "INFO")
            for c in cfg.get("cookies").split(";"):
                if "=" in c:
                    name, val = c.split("=",1)
                    try:
                        driver.add_cookie({"name": name.strip(), "value": val.strip(), "domain": ".facebook.com", "path": "/"})
                    except Exception as e:
                        push_log(f"Cookie add failed: {name.strip()} -> {e}", "WARN")

        # open chat
        target = cfg.get("chat_id","").strip()
        if target:
            url = f"https://www.facebook.com/messages/t/{target}"
            push_log(f"Opening conversation: {url}", "INFO")
            driver.get(url)
        else:
            push_log("No chat_id configured — opening messages page", "WARN")
            driver.get("https://www.facebook.com/messages")

        time.sleep(8)
        input_el = find_message_input(driver)
        if not input_el:
            push_log("Input box not found — stopping automation", "ERROR")
            state.running = False
            db.set_automation_running(uid, False)
            return

        messages_list = get_messages_list(cfg.get("messages",""))
        delay_seconds = max(1, int(cfg.get("delay",15)))
        sent_count = 0

        push_log(f"Loaded {len(messages_list)} messages. Starting loop...", "INFO")

        while state.running:
            msg_base = get_next_message(messages_list, state)
            final_msg = f"{cfg.get('name_prefix','').strip()} {msg_base}".strip()

            try:
                # put message into input
                driver.execute_script("""
                    const el = arguments[0];
                    const txt = arguments[1];
                    el.focus();
                    if (el.tagName === 'DIV') {
                        el.innerText = txt;
                        el.textContent = txt;
                    } else {
                        el.value = txt;
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                """, input_el, final_msg)
                time.sleep(0.6)

                # try to click send buttons
                sent = driver.execute_script("""
                    const btns = document.querySelectorAll('[aria-label*="Send" i], [data-testid="send-button"], button[type="submit"]');
                    for (let b of btns) {
                        if (b.offsetParent !== null) {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                """)
                if not sent:
                    # fallback: Enter key
                    driver.execute_script("""
                        const el = arguments[0];
                        el.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}));
                        el.dispatchEvent(new KeyboardEvent('keyup', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}));
                    """, input_el)
                    push_log("Used Enter key to send", "INFO")
                else:
                    push_log("Clicked send button", "INFO")

                sent_count += 1
                state.message_count = sent_count
                push_log(f"[SENT #{sent_count}] {final_msg[:120]}", "SENT")

                # sleep breakable
                for i in range(delay_seconds):
                    if not state.running:
                        break
                    time.sleep(1)
            except Exception as e:
                push_log(f"Send error: {e}", "ERROR")
                # try to re-find input for next loop
                time.sleep(2)
                input_el = find_message_input(driver)
                if not input_el:
                    push_log("Could not re-find input after error, stopping", "ERROR")
                    break

        push_log(f"Automation loop ended. Sent {sent_count} messages.", "INFO")
        state.running = False
        db.set_automation_running(uid, False)
        return sent_count
    except Exception as e:
        push_log(f"Fatal automation error: {e}", "ERROR")
        state.running = False
        db.set_automation_running(uid, False)
        return 0
    finally:
        if driver:
            try:
                driver.quit()
                push_log("Browser closed", "INFO")
            except:
                pass

# ---------- Start/Stop helpers ----------
def start_automation_thread(cfg, uid):
    state = st.session_state.automation_state
    if state.running:
        push_log("Automation already running", "WARN")
        return
    state.running = True
    state.message_count = 0
    state.message_rotation_index = 0
    state.logs = []
    db.set_automation_running(uid, True)
    t = threading.Thread(target=send_messages_loop, args=(cfg, state, uid), daemon=True)
    t.start()
    push_log("Automation thread started", "INFO")

def stop_automation():
    state = st.session_state.automation_state
    if state.running:
        state.running = False
        db.set_automation_running(st.session_state.user_id, False)
        push_log("Stop signal sent to automation thread", "WARN")
    else:
        push_log("Stop requested but automation not running", "WARN")

# ---------- Automation controls UI ----------
st.subheader("🚀 Automation Control")
c1, c2, c3 = st.columns([1,1,1])
with c1:
    if st.button("▶️ Start", disabled=st.session_state.automation_state.running):
        cfg_payload = {
            "chat_id": chat_id,
            "name_prefix": name_prefix,
            "delay": delay,
            "cookies": cookies if cookies.strip() else user_config.get("cookies",""),
            "messages": messages_text
        }
        if not cfg_payload["chat_id"]:
            st.error("Please add Chat ID before starting")
        else:
            start_automation_thread(cfg_payload, st.session_state.user_id)
            time.sleep(0.3)
            st.experimental_rerun()
with c2:
    if st.button("⏹ Stop", disabled=not st.session_state.automation_state.running):
        stop_automation()
        time.sleep(0.3)
        st.experimental_rerun()
with c3:
    if st.button("Restart (quick)"):
        stop_automation()
        time.sleep(0.5)
        cfg_payload = {
            "chat_id": chat_id,
            "name_prefix": name_prefix,
            "delay": delay,
            "cookies": cookies if cookies.strip() else user_config.get("cookies",""),
            "messages": messages_text
        }
        start_automation_thread(cfg_payload, st.session_state.user_id)
        time.sleep(0.3)
        st.experimental_rerun()

# ---------- Live Console UI ----------
st.subheader("📡 Live Console Monitor")

# top controls for logs
fcol1, fcol2, fcol3, fcol4 = st.columns([1,1,1,1])
with fcol1:
    show_info = st.checkbox("INFO", value=True, key="show_info")
with fcol2:
    show_warn = st.checkbox("WARN", value=True, key="show_warn")
with fcol3:
    show_error = st.checkbox("ERROR", value=True, key="show_error")
with fcol4:
    show_sent = st.checkbox("SENT", value=True, key="show_sent")

# download / clear
dcol1, dcol2 = st.columns([1,1])
with dcol1:
    if st.button("📥 Download Logs"):
        # prepare text file
        text = "\n".join([l for (l, lvl) in st.session_state.automation_state.logs])
        st.download_button("Download .txt", data=text, file_name="automation_logs.txt")
with dcol2:
    if st.button("🗑 Clear Logs"):
        st.session_state.automation_state.logs = []
        push_log("User cleared logs", "INFO")
        st.experimental_rerun()

# show metrics
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Messages Sent", st.session_state.automation_state.message_count)
with m2:
    status_text = "Running" if st.session_state.automation_state.running else "Stopped"
    st.metric("Status", status_text)
with m3:
    st.metric("Total Logs", len(st.session_state.automation_state.logs))

# render logs
logs_to_show = []
for (line, lvl) in st.session_state.automation_state.logs:
    ok = False
    if lvl == "INFO" and show_info: ok = True
    if lvl == "WARN" and show_warn: ok = True
    if lvl == "ERROR" and show_error: ok = True
    if lvl == "SENT" and show_sent: ok = True
    if ok:
        logs_to_show.append((line, lvl))

# Build html
html = '<div class="card console-section">'
html += '<div class="console-output" id="console-output">'
for (ln, lv) in logs_to_show[-LOG_LIMIT:]:
    cls = "info"
    if lv == "WARN": cls = "warn"
    if lv == "ERROR": cls = "error"
    if lv == "SENT": cls = "sent"
    safe = ln.replace("<", "&lt;").replace(">", "&gt;")
    html += f'<div class="console-line {cls}">{safe}</div>'
html += "</div></div>"

st.markdown(html, unsafe_allow_html=True)

# auto-scroll to bottom
st.markdown("""
<script>
const el = document.getElementById('console-output');
if (el) { el.scrollTop = el.scrollHeight; }
</script>
""", unsafe_allow_html=True)

# if automation running, small rerun to refresh logs
if st.session_state.automation_state.running:
    time.sleep(1)
    st.rerun()

# ---------- Footer ----------
st.markdown('<div style="text-align:center;margin-top:18px;color:#475569">Built with ❤️ — Premium Console</div>', unsafe_allow_html=True)

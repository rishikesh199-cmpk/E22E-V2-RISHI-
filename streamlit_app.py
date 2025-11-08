# streamlit_app.py
"""
Streamlit control panel for Messenger automation (final).
- Login required (uses database.py)
- No notifications
- Messages only via file upload (preview shown)
- Works on Streamlit Cloud (uses webdriver-manager in automation.py)
"""

import streamlit as st
import time
from queue import Queue, Empty
from pathlib import Path

# Import your DB and automation modules (assumed present in same folder)
import database as db
from automation import AutomationController

# Page config
st.set_page_config(
    page_title="Messenger Automation Panel",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimal CSS (light styling) — you can paste your original CSS if you prefer
st.markdown(
    """
    <style>
    .main .block-container { padding: 1.5rem 2rem; }
    .header { display:flex; gap:12px; align-items:center; }
    .logo { width:60px; border-radius:8px; }
    .console-output { background:#0b1220; color:#00ff88; padding:12px; border-radius:8px; font-family:monospace; max-height:420px; overflow:auto; }
    .preview-box { background:rgba(255,255,255,0.04); padding:12px; border-radius:8px; color:white; }
    label { color: #e6eef8 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Session state initialization ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "log_queue" not in st.session_state:
    st.session_state.log_queue = Queue()
if "automation_controller" not in st.session_state:
    st.session_state.automation_controller = AutomationController(st.session_state.log_queue)
if "log_lines" not in st.session_state:
    st.session_state.log_lines = []
if "uploaded_messages" not in st.session_state:
    st.session_state.uploaded_messages = []  # list[str]
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

# ---------- Helper: collect logs from queue ----------
def fetch_logs(max_lines=500):
    q = st.session_state.log_queue
    new = []
    try:
        while True:
            line = q.get_nowait()
            new.append(line)
            if len(new) >= 200:
                break
    except Exception:
        pass
    if new:
        st.session_state.log_lines.extend(new)
        st.session_state.log_lines = st.session_state.log_lines[-max_lines:]
    return st.session_state.log_lines

# ---------- Header ----------
col_h1, col_h2 = st.columns([0.12, 0.88])
with col_h1:
    st.image("https://i.postimg.cc/VvB52mwW/In-Shot-20250608-213052061.jpg", width=64)
with col_h2:
    st.markdown("<div class='header'><h1 style='margin:0'>Messenger Automation</h1></div>", unsafe_allow_html=True)
st.markdown("---")

# ---------- Authentication ----------
if not st.session_state.logged_in:
    tabs = st.tabs(["🔐 Login", "✨ Sign Up"])
    with tabs[0]:
        st.subheader("Login")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", key="login_pass", type="password")
        if st.button("Login", key="btn_login", use_container_width=True):
            if not login_user or not login_pass:
                st.warning("Enter both username and password.")
            else:
                uid = db.verify_user(login_user, login_pass)
                if uid:
                    st.session_state.logged_in = True
                    st.session_state.user_id = uid
                    st.session_state.username = login_user
                    st.success(f"Welcome back, {login_user}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    with tabs[1]:
        st.subheader("Create account")
        new_user = st.text_input("Choose username", key="new_user")
        new_pass = st.text_input("Choose password", key="new_pass", type="password")
        new_pass2 = st.text_input("Confirm password", key="new_pass2", type="password")
        if st.button("Create account", key="btn_create", use_container_width=True):
            if not new_user or not new_pass:
                st.warning("Fill all fields.")
            elif new_pass != new_pass2:
                st.error("Passwords do not match.")
            else:
                ok, msg = db.create_user(new_user, new_pass)
                if ok:
                    st.success(msg + " You may now login.")
                else:
                    st.error(msg)

    st.stop()  # stop here until logged in

# ---------- Main Panel (logged in) ----------
st.sidebar.markdown(f"### 👤 {st.session_state.username}")
if st.sidebar.button("Logout", use_container_width=True):
    # stop automation if running
    if st.session_state.automation_controller.is_running():
        st.session_state.automation_controller.stop()
        db.set_automation_running(st.session_state.user_id, False)
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.rerun()

# fetch user config
user_cfg = db.get_user_config(st.session_state.user_id) or {
    "chat_id": "",
    "cookies": "",
    "name_prefix": "",
    "messages": "",
    "delay": 5,
}

# ---------- Layout: Configuration + Automation tabs ----------
tab_conf, tab_auto = st.tabs(["⚙️ Configuration", "🚀 Automation"])

with tab_conf:
    st.subheader("Configuration")
    chat_id = st.text_input("Chat / Conversation ID", value=user_cfg.get("chat_id", ""), help="Facebook conversation ID from the URL (messages/t/<ID>)")
    name_prefix = st.text_input("Name prefix (optional)", value=user_cfg.get("name_prefix", ""), help="Optional prefix to add before each message")
    delay = st.number_input("Delay between messages (seconds)", min_value=1, max_value=3600, value=int(user_cfg.get("delay", 5)))
    cookies = st.text_area("Facebook cookies (JSON string) — required for automation", value=user_cfg.get("cookies", ""), height=140, help="Paste your Facebook cookies as a JSON array/object. Keep private!")

    st.markdown("### Messages (upload only)")
    st.caption("Upload a plain .txt file where each line is one message. Preview will show loaded messages.")

    uploaded_file = st.file_uploader("Upload messages file (.txt or .csv)", type=["txt", "csv"], accept_multiple_files=False)

    if uploaded_file is not None:
        try:
            raw = uploaded_file.read()
            # try detect encoding as utf-8
            text = raw.decode("utf-8", errors="ignore")
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            st.session_state.uploaded_messages = lines
            st.session_state.uploaded_filename = uploaded_file.name
            st.success(f"Loaded {len(lines)} messages from {uploaded_file.name}")
        except Exception as e:
            st.error(f"Failed to read file: {e}")
            st.session_state.uploaded_messages = []
            st.session_state.uploaded_filename = None

    # preview box
    if st.session_state.uploaded_messages:
        st.markdown(f"**Preview — {st.session_state.uploaded_filename}**")
        preview_html = "<div class='preview-box'><ol>"
        for m in st.session_state.uploaded_messages[:500]:
            preview_html += f"<li>{st.html_escape(m)}</li>"
        preview_html += "</ol></div>"
        st.markdown(preview_html, unsafe_allow_html=True)
    else:
        st.info("No messages uploaded yet. Please upload a .txt file.")

    if st.button("💾 Save Configuration", use_container_width=True):
        # Save uploaded messages to DB as newline-joined string (so automation can read)
        messages_joined = "\n".join(st.session_state.uploaded_messages) if st.session_state.uploaded_messages else ""
        db.update_user_config(st.session_state.user_id, chat_id.strip(), name_prefix.strip(), int(delay), cookies.strip(), messages_joined)
        st.success("Configuration saved.")
        st.rerun()

with tab_auto:
    st.subheader("Automation Control")

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        st.metric("Messages sent", st.session_state.automation_controller.messages_sent)
    with col2:
        status_text = "🟢 Running" if st.session_state.automation_controller.is_running() else "🔴 Stopped"
        st.metric("Status", status_text)
    with col3:
        st.metric("Loaded messages", len(st.session_state.uploaded_messages))

    st.markdown("---")
    st.markdown("**Run options**")
    headless = st.checkbox("Run browser headless (required on Streamlit Cloud)", value=True, help="On Cloud: headless must be checked. Locally you can uncheck to see browser window.")

    start_col, stop_col = st.columns(2)
    with start_col:
        if st.button("▶️ Start Automation", disabled=st.session_state.automation_controller.is_running(), use_container_width=True):
            # validate config & uploaded messages
            cfg = db.get_user_config(st.session_state.user_id) or {}
            # prefer latest UI fields (not only DB)
            cfg_chat = chat_id.strip()
            cfg_cookies = cookies.strip()
            cfg_prefix = name_prefix.strip()
            cfg_delay = int(delay)
            cfg_messages = "\n".join(st.session_state.uploaded_messages)

            if not cfg_chat:
                st.error("Please set Chat/Conversation ID.")
            elif not cfg_cookies:
                st.error("Please paste Facebook cookies (required).")
            elif not st.session_state.uploaded_messages:
                st.error("Please upload a messages file first.")
            else:
                # start automation
                start_config = {
                    "chat_id": cfg_chat,
                    "cookies": cfg_cookies,
                    "name_prefix": cfg_prefix,
                    "messages": cfg_messages,
                    "delay": cfg_delay,
                    "headless": bool(headless)
                }
                started = st.session_state.automation_controller.start(start_config)
                if started:
                    db.set_automation_running(st.session_state.user_id, True)
                    st.success("Automation started.")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.warning("Automation already running or failed to start.")
    with stop_col:
        if st.button("⏹️ Stop Automation", disabled=not st.session_state.automation_controller.is_running(), use_container_width=True):
            stopped = st.session_state.automation_controller.stop()
            db.set_automation_running(st.session_state.user_id, False)
            if stopped:
                st.success("Automation stopped.")
            else:
                st.warning("Automation was not running.")
            time.sleep(0.6)
            st.rerun()

    # Live logs / console
    st.markdown("### Live Console")
    logs = fetch_logs()
    if logs:
        # display last 300 logs
        display = logs[-300:]
        console_html = "<div class='console-output'>"
        for ln in display:
            console_html += f"{ln}<br />"
        console_html += "</div>"
        st.markdown(console_html, unsafe_allow_html=True)
    else:
        st.markdown("<div class='console-output'>No logs yet — start the automation to see live logs.</div>", unsafe_allow_html=True)

    # auto-refresh while running (light)
    if st.session_state.automation_controller.is_running():
        time.sleep(1)
        st.rerun()

# Footer
st.markdown("---")
st.markdown("Built for you — no notifications, upload-only messages. Keep cookies private.")

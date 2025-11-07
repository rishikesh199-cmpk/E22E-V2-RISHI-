# panel_app.py
"""
Streamlit control panel for running the automation (uses automation.py).
- UI elements and CSS preserved from original.
- Starts/stops AutomationController and shows live logs from a Queue.
- Assumes database.py exists with the same API used previously.
"""

import streamlit as st
import time
from queue import Queue, Empty
import database as db  # your existing DB module
from automation import AutomationController

# ------------------ Page config & CSS (kept same as in your original) ------------------
st.set_page_config(
    page_title="OFFLINE💋PY",
    page_icon="🏴‍☠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

custom_css = """
<style>
/* (Use the exact CSS you used before; shortened here for readability in this message) */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
* { font-family: 'Poppins', sans-serif; }
/* Paste the full CSS from your original streamlit_app.py here
   (I omitted it in this message for brevity — be sure to paste your full CSS block) */
</style>
"""
# If you want the original CSS exactly, copy the custom_css content from your existing file.
st.markdown(custom_css, unsafe_allow_html=True)

# ------------------ Session state initialization ------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'log_queue' not in st.session_state:
    st.session_state.log_queue = Queue()
if 'automation_controller' not in st.session_state:
    st.session_state.automation_controller = AutomationController(st.session_state.log_queue)
if 'auto_start_checked' not in st.session_state:
    st.session_state.auto_start_checked = False
if 'css_injected' not in st.session_state:
    st.session_state.css_injected = True  # we've already injected css above

# ------------------ Utility to fetch recent logs ------------------
def fetch_logs(max_lines=200):
    q = st.session_state.log_queue
    lines = []
    try:
        while True:
            line = q.get_nowait()
            lines.append(line)
            if len(lines) >= max_lines:
                break
    except Exception:
        pass
    # keep lines in session for display continuity
    if 'log_lines' not in st.session_state:
        st.session_state.log_lines = []
    st.session_state.log_lines.extend(lines)
    # keep only last N
    st.session_state.log_lines = st.session_state.log_lines[-500:]
    return st.session_state.log_lines

# ------------------ Header ------------------
st.markdown('<div class="main-header"><img src="https://i.postimg.cc/VvB52mwW/In-Shot-20250608-213052061.jpg" class="prince-logo"><h1> E2EE OFFLINE</h1><p>𝘾𝙃𝙊𝙊𝙏 𝙆𝙊 𝙇𝘼𝙉𝘿 𝙎𝙀 𝘾𝙃𝙀𝙀𝙍𝙉𝙀𝙔 𝙒𝘼𝙇𝘼 𝘿𝘼𝙉𝘼𝙑 𝙆𝙄𝙉𝙂</p></div>', unsafe_allow_html=True)

# ------------------ Authentication ------------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    with tab1:
        st.markdown("### Welcome Back!")
        username = st.text_input("Username", key="login_username", placeholder="Enter your username")
        password = st.text_input("Password", key="login_password", type="password", placeholder="Enter your password")
        if st.button("Login", key="login_btn", use_container_width=True):
            if username and password:
                user_id = db.verify_user(username, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username

                    # auto-start automation if it was running before
                    should_auto_start = db.get_automation_running(user_id)
                    if should_auto_start:
                        user_config = db.get_user_config(user_id)
                        if user_config and user_config.get('chat_id'):
                            # ensure automation controller uses current queue
                            if not st.session_state.automation_controller.is_running():
                                st.session_state.automation_controller.start({
                                    "chat_id": user_config.get('chat_id', ''),
                                    "cookies": user_config.get('cookies', ''),
                                    "name_prefix": user_config.get('name_prefix', ''),
                                    "messages": user_config.get('messages', ''),
                                    "delay": user_config.get('delay', 5),
                                    "headless": True
                                })
                                db.set_automation_running(user_id, True)

                    st.success(f"✅ Welcome back, {username}!")
                    st.experimental_rerun()
                else:
                    st.error("❌ Invalid username or password!")
            else:
                st.warning("⚠️ Please enter both username and password")

    with tab2:
        st.markdown("### Create New Account")
        new_username = st.text_input("Choose Username", key="signup_username", placeholder="Choose a unique username")
        new_password = st.text_input("Choose Password", key="signup_password", type="password", placeholder="Create a strong password")
        confirm_password = st.text_input("Confirm Password", key="confirm_password", type="password", placeholder="Re-enter your password")
        if st.button("Create Account", key="signup_btn", use_container_width=True):
            if new_username and new_password and confirm_password:
                if new_password == confirm_password:
                    success, message = db.create_user(new_username, new_password)
                    if success:
                        st.success(f"✅ {message} Please login now!")
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ Passwords do not match!")
            else:
                st.warning("⚠️ Please fill all fields")

# ------------------ Main panel for logged in users ------------------
else:
    # Sidebar
    st.sidebar.markdown(f"### 👤 {st.session_state.username}")
    st.sidebar.markdown(f"**User ID:** {st.session_state.user_id}")

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if st.session_state.automation_controller.is_running():
            st.session_state.automation_controller.stop()
            db.set_automation_running(st.session_state.user_id, False)
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.experimental_rerun()

    # fetch user config from DB
    user_config = db.get_user_config(st.session_state.user_id) or {
        "chat_id": "",
        "cookies": "",
        "name_prefix": "",
        "messages": "",
        "delay": 5
    }

    tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Automation"])

    with tab1:
        st.markdown("### Your Configuration")

        chat_id = st.text_input("Chat/Conversation ID", value=user_config.get('chat_id', ''), placeholder="e.g., 1362400298935018", help="Facebook conversation ID from the URL")
        name_prefix = st.text_input("Hatersname", value=user_config.get('name_prefix', ''), placeholder="e.g., [END TO END]", help="Prefix to add before each message")
        delay = st.number_input("Delay (seconds)", min_value=1, max_value=300, value=int(user_config.get('delay', 5)), help="Wait time between messages")
        cookies = st.text_area("Facebook Cookies (optional - kept private)", value=user_config.get('cookies', ''), placeholder="Paste your Facebook cookies here (will be encrypted)", height=120)
        messages = st.text_area("Messages (one per line)", value=user_config.get('messages', ''), placeholder="Each line is one message; messages will rotate.", height=180)

        if st.button("💾 Save Configuration", use_container_width=True):
            db.update_user_config(st.session_state.user_id, chat_id, name_prefix, int(delay), cookies, messages)
            st.success("✅ Configuration saved successfully!")
            st.experimental_rerun()

    with tab2:
        st.markdown("### Automation Control")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Messages Sent", st.session_state.automation_controller.messages_sent)
        with col2:
            status = "🟢 Running" if st.session_state.automation_controller.is_running() else "🔴 Stopped"
            st.metric("Status", status)
        with col3:
            total_logs = len(st.session_state.get('log_lines', []))
            st.metric("Total Logs", total_logs)

        st.markdown("#### Run Options")
        headless_toggle = st.checkbox("Run browser headless (recommended)", value=True)
        debug_visible = not headless_toggle

        col_start, col_stop = st.columns(2)
        with col_start:
            if st.button("▶️ Start E2EE", disabled=st.session_state.automation_controller.is_running(), use_container_width=True):
                # read latest config from UI (so user can update before starting)
                latest_config = {
                    "chat_id": chat_id.strip(),
                    "cookies": cookies.strip(),
                    "name_prefix": name_prefix.strip(),
                    "messages": messages,
                    "delay": int(delay),
                    "headless": headless_toggle
                }
                if not latest_config['chat_id']:
                    st.error("❌ Please configure Chat ID first!")
                else:
                    started = st.session_state.automation_controller.start(latest_config)
                    if started:
                        db.set_automation_running(st.session_state.user_id, True)
                        st.success("✅ Automation started.")
                        # give it a moment and refresh UI to show live logs
                        time.sleep(1)
                        st.experimental_rerun()
                    else:
                        st.warning("⚠️ Automation could not be started (already running?).")

        with col_stop:
            if st.button("⏹️ Stop E2EE", disabled=not st.session_state.automation_controller.is_running(), use_container_width=True):
                stopped = st.session_state.automation_controller.stop()
                db.set_automation_running(st.session_state.user_id, False)
                if stopped:
                    st.success("⏹️ Automation stopped.")
                else:
                    st.warning("⚠️ Automation was not running.")
                time.sleep(1)
                st.experimental_rerun()

        # Console / logs
        st.markdown('<div class="console-section"><h4 class="console-header"><i class="fas fa-terminal"></i> Live Console Monitor</h4></div>', unsafe_allow_html=True)

        # Pull logs from the queue and display them
        logs = fetch_logs()
        if logs:
            logs_html = '<div class="console-output">'
            for log in logs[-200:]:
                logs_html += f'<div class="console-line">{log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="console-output"><div class="console-line">🚀 Console ready... Start automation to see logs here.</div></div>', unsafe_allow_html=True)

        # auto-refresh when running to show live logs
        if st.session_state.automation_controller.is_running():
            time.sleep(1)
            st.experimental_rerun()

# Footer
st.markdown('<div class="footer">𝙃𝘼𝙏𝙀𝙍𝙎 𝙆𝙄 𝙈𝙒 𝙆𝘼 𝘽𝙃9𝙎𝘿𝘼  𝙊𝙉𝙁𝙄𝙍𝙀𝙀𝙀 <br>All Rights Reserved</div>', unsafe_allow_html=True)

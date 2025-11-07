# panel_app.py
"""
Streamlit control panel for Facebook Messenger automation.
✅ Works with Streamlit Cloud
✅ Compatible with database.py & automation.py
✅ Uses st.rerun() (no deprecated functions)
✅ Added file upload option for messages
"""

import streamlit as st
import time
from queue import Queue
import database as db
from automation import AutomationController

# ------------------ Page Config ------------------
st.set_page_config(
    page_title="OFFLINE💋PY",
    page_icon="🏴‍☠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ Custom CSS ------------------
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    * { font-family: 'Poppins', sans-serif; }
    .stApp {
        background-image: url('https://i.postimg.cc/L51fQrQH/681be2a77443fb2f2f74fd42da1bc40f.jpg');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    .main .block-container {
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        border: 1px solid rgba(255,255,255,0.12);
    }
    .main-header {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.15);
    }
    .main-header h1 {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    .main-header p { color: rgba(255,255,255,0.9); font-size: 1.1rem; margin-top: .5rem; }
    .prince-logo {
        width: 70px; height: 70px; border-radius: 50%; margin-bottom: 15px; border: 2px solid #4ecdc4;
    }
    .stButton>button {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        color: white; border: none; border-radius: 10px;
        padding: .75rem 2rem; font-weight: 600; font-size: 1rem;
        transition: all .3s ease; box-shadow: 0 4px 15px rgba(102,126,234,0.4); width: 100%;
    }
    .stButton>button:hover { opacity: .9; transform: translateY(-2px); }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25);
        border-radius: 8px; color: white; padding: .75rem;
    }
    label { color: white !important; font-weight: 500 !important; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background: rgba(255,255,255,0.06);
        padding: 10px; border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] { background: rgba(255,255,255,0.1); border-radius: 8px; color: white; }
    .stTabs [aria-selected="true"] { background: linear-gradient(45deg,#ff6b6b,#4ecdc4); }
    .console-section { margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.06);
        border-radius: 10px; border: 1px solid rgba(78,205,196,0.3);}
    .console-header { color:#4ecdc4; text-shadow:0 0 10px rgba(78,205,196,.5); margin-bottom:20px; font-weight:600; }
    .console-output {
        background: rgba(0,0,0,0.5); border: 1px solid rgba(78,205,196,0.4);
        border-radius: 10px; padding: 12px; font-family: monospace;
        font-size: 12px; color: #00ff88; max-height: 400px; overflow-y: auto;
    }
    .console-line { margin-bottom: 3px; word-wrap: break-word; padding: 6px 10px; color: #00ff88; }
    .footer { text-align: center; padding: 2rem; color: rgba(255,255,255,0.7);
        font-weight: 600; margin-top: 3rem; background: rgba(255,255,255,0.05);
        border-radius: 10px; border-top: 1px solid rgba(255,255,255,0.15);
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ------------------ Session State ------------------
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
if 'log_lines' not in st.session_state:
    st.session_state.log_lines = []

# ------------------ Helper for logs ------------------
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
    st.session_state.log_lines.extend(lines)
    st.session_state.log_lines = st.session_state.log_lines[-500:]
    return st.session_state.log_lines

# ------------------ Header ------------------
st.markdown('<div class="main-header"><img src="https://i.postimg.cc/VvB52mwW/In-Shot-20250608-213052061.jpg" class="prince-logo"><h1> E2EE OFFLINE</h1><p>𝘾𝙃𝙊𝙊𝙏 𝙆𝙊 𝙇𝘼𝙉𝘿 𝙎𝙀 𝘾𝙃𝙀𝙀𝙍𝙉𝙀𝙔 𝙒𝘼𝙇𝘼 𝘿𝘼𝙉𝘼𝙑 𝙆𝙄𝙉𝙂</p></div>', unsafe_allow_html=True)

# ------------------ LOGIN / SIGNUP ------------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", key="login_password", type="password")
        if st.button("Login", key="login_btn", use_container_width=True):
            user_id = db.verify_user(username, password)
            if user_id:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.success(f"✅ Welcome back, {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password!")

    with tab2:
        new_username = st.text_input("Choose Username", key="signup_username")
        new_password = st.text_input("Choose Password", key="signup_password", type="password")
        confirm_password = st.text_input("Confirm Password", key="confirm_password", type="password")
        if st.button("Create Account", key="signup_btn", use_container_width=True):
            if new_password == confirm_password:
                success, msg = db.create_user(new_username, new_password)
                st.success(msg) if success else st.error(msg)
            else:
                st.error("Passwords do not match!")

# ------------------ MAIN PANEL ------------------
else:
    st.sidebar.markdown(f"### 👤 {st.session_state.username}")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if st.session_state.automation_controller.is_running():
            st.session_state.automation_controller.stop()
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()

    user_config = db.get_user_config(st.session_state.user_id) or {
        "chat_id": "", "cookies": "", "name_prefix": "", "messages": "", "delay": 5
    }

    tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Automation"])

    with tab1:
        chat_id = st.text_input("Chat/Conversation ID", value=user_config.get('chat_id', ''), placeholder="e.g., 1362400298935018")
        name_prefix = st.text_input("Hatersname", value=user_config.get('name_prefix', ''), placeholder="[END TO END]")
        delay = st.number_input("Delay (seconds)", min_value=1, max_value=300, value=int(user_config.get('delay', 5)))
        cookies = st.text_area("Facebook Cookies", value=user_config.get('cookies', ''), height=100)

        # 📂 File upload + manual input for messages
        st.markdown("#### Messages")
        uploaded_file = st.file_uploader("📂 Upload Messages File (.txt or .csv)", type=["txt", "csv"])
        messages_text = user_config.get('messages', '')

        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode("utf-8", errors="ignore")
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                messages_text = "\n".join(lines)
                st.success(f"✅ Loaded {len(lines)} messages from file.")
                st.text_area("Preview Loaded Messages", value=messages_text, height=180)
            except Exception as e:
                st.error(f"Error reading file: {e}")
        else:
            messages_text = st.text_area("Messages (one per line)",
                                         value=messages_text,
                                         placeholder="Each line is one message; messages will rotate.",
                                         height=180)

        if st.button("💾 Save Configuration", use_container_width=True):
            db.update_user_config(st.session_state.user_id, chat_id, name_prefix, int(delay), cookies, messages_text)
            st.success("✅ Configuration saved successfully!")
            st.rerun()

    with tab2:
        st.markdown("### Automation Control")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages Sent", st.session_state.automation_controller.messages_sent)
        with col2:
            status = "🟢 Running" if st.session_state.automation_controller.is_running() else "🔴 Stopped"
            st.metric("Status", status)

        headless_toggle = st.checkbox("Run browser headless (Streamlit Cloud compatible)", value=True)

        start, stop = st.columns(2)
        with start:
            if st.button("▶️ Start E2EE", disabled=st.session_state.automation_controller.is_running(), use_container_width=True):
                config = {
                    "chat_id": chat_id.strip(),
                    "cookies": cookies.strip(),
                    "name_prefix": name_prefix.strip(),
                    "messages": messages_text,
                    "delay": int(delay),
                    "headless": headless_toggle
                }
                if not config['chat_id']:
                    st.error("❌ Please enter Chat ID first!")
                else:
                    started = st.session_state.automation_controller.start(config)
                    if started:
                        db.set_automation_running(st.session_state.user_id, True)
                        st.success("✅ Automation started.")
                        time.sleep(1)
                        st.rerun()
        with stop:
            if st.button("⏹️ Stop E2EE", disabled=not st.session_state.automation_controller.is_running(), use_container_width=True):
                stopped = st.session_state.automation_controller.stop()
                db.set_automation_running(st.session_state.user_id, False)
                if stopped:
                    st.success("⏹️ Automation stopped.")
                else:
                    st.warning("⚠️ Automation not running.")
                time.sleep(1)
                st.rerun()

        # 🖥️ Live console monitor
        st.markdown('<div class="console-section"><h4 class="console-header">💻 Live Console Monitor</h4></div>', unsafe_allow_html=True)
        logs = fetch_logs()
        if logs:
            html = '<div class="console-output">' + "".join(f"<div class='console-line'>{l}</div>" for l in logs[-200:]) + "</div>"
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="console-output"><div class="console-line">🚀 Console ready... Start automation to see logs here.</div></div>', unsafe_allow_html=True)

        if st.session_state.automation_controller.is_running():
            time.sleep(1)
            st.rerun()

st.markdown('<div class="footer">💋 All Rights Reserved | E2EE OFFLINE</div>', unsafe_allow_html=True)

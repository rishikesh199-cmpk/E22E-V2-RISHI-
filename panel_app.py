# panel_app.py
"""
Streamlit control panel for running the automation (uses automation.py).
- Keeps your UI/CSS/look.
- Works with the database.py provided.
"""

import streamlit as st
import time
from queue import Queue
import database as db
from automation import AutomationController

st.set_page_config(
    page_title="OFFLINE BABY",
    page_icon="🩵",
    layout="wide",
    initial_sidebar_state="expanded"
)

custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Noto+Sans+Devanagari:wght@400;600&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Background Image */
    .stApp {
        background-image: url('https://i.postimg.cc/L51fQrQH/681be2a77443fb2f2f74fd42da1bc40f.jpg');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    /* Main Container */
    .main .block-container {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    
    .main-header {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    .main-header h1 {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    .prince-logo {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        margin-bottom: 15px;
        border: 2px solid #4ecdc4;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        width: 100%;
    }
    
    .stButton>button:hover {
        opacity: 0.9;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input, 
    .stTextArea>div>div>textarea, 
    .stNumberInput>div>div>input {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 8px;
        color: white;
        padding: 0.75rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input::placeholder,
    .stTextArea>div>div>textarea::placeholder {
        color: rgba(255, 255, 255, 0.6);
    }
    
    .stTextInput>div>div>input:focus, 
    .stTextArea>div>div>textarea:focus {
        background: rgba(255, 255, 255, 0.2);
        border-color: #4ecdc4;
        box-shadow: 0 0 0 2px rgba(78, 205, 196, 0.2);
        color: white;
    }
    
    /* Labels */
    label {
        color: white !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.06);
        padding: 10px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: white;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #4ecdc4;
        font-weight: 700;
        font-size: 1.8rem;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.9);
        font-weight: 500;
    }
    
    /* Console Section */
    .console-section {
        margin-top: 20px;
        padding: 15px;
        background: rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        border: 1px solid rgba(78, 205, 196, 0.3);
    }
    
    .console-header {
        color: #4ecdc4;
        text-shadow: 0 0 10px rgba(78, 205, 196, 0.5);
        margin-bottom: 20px;
        font-weight: 600;
    }
    
    .console-output {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(78, 205, 196, 0.4);
        border-radius: 10px;
        padding: 12px;
        font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
        font-size: 12px;
        color: #00ff88;
        line-height: 1.6;
        max-height: 400px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(78, 205, 196, 0.5) rgba(0, 0, 0, 0.2);
    }
    
    .console-output::-webkit-scrollbar {
        width: 8px;
    }
    
    .console-output::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
    }
    
    .console-output::-webkit-scrollbar-thumb {
        background: rgba(78, 205, 196, 0.5);
        border-radius: 4px;
    }
    
    .console-output::-webkit-scrollbar-thumb:hover {
        background: rgba(78, 205, 196, 0.7);
    }
    
    .console-line {
        margin-bottom: 3px;
        word-wrap: break-word;
        padding: 6px 10px;
        padding-left: 28px;
        color: #00ff88;
        background: rgba(78, 205, 196, 0.08);
        border-left: 2px solid rgba(78, 205, 196, 0.4);
        position: relative;
    }
    
    .console-line::before {
        content: '►';
        position: absolute;
        left: 10px;
        opacity: 0.6;
        color: #4ecdc4;
    }
    
    /* Success/Error Boxes */
    .success-box {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    .error-box {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* Info Card */
    .info-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: rgba(255, 255, 255, 0.7);
        font-weight: 600;
        margin-top: 3rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    [data-testid="stSidebar"] .element-container {
        color: white;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Session state init
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
if 'log_lines' not in st.session_state:
    st.session_state.log_lines = []

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

st.markdown('<div class="main-header"><img src="https://i.postimg.cc/VvB52mwW/In-Shot-20250608-213052061.jpg" class="prince-logo"><h1> E2EE OFFLINE</h1><p>𝘾𝙃𝙊𝙊𝙏 𝙆𝙊 𝙇𝘼𝙉𝘿 𝙎𝙀 𝘾𝙃𝙀𝙀𝙍𝙉𝙀𝙔 𝙒𝘼𝙇𝘼 𝘿𝘼𝙉𝘼𝙑 𝙆𝙄𝙉𝙂</p></div>', unsafe_allow_html=True)

# Authentication UI
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

                    should_auto_start = db.get_automation_running(user_id)
                    if should_auto_start:
                        user_config = db.get_user_config(user_id)
                        if user_config and user_config.get('chat_id'):
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

# Main panel
else:
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
        headless_toggle = st.checkbox("Run browser headless (required on Streamlit Cloud)", value=True)

        col_start, col_stop = st.columns(2)
        with col_start:
            if st.button("▶️ Start E2EE", disabled=st.session_state.automation_controller.is_running(), use_container_width=True):
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
                        time.sleep(1)
                        st.experimental_rerun()
                    else:
                        st.warning("⚠️ Automation could not be started (already running?).")

        with col_stop:
            if st.button("⏹️ Stop E2ee", disabled=not st.session_state.automation_controller.is_running(), use_container_width=True):
                stopped = st.session_state.automation_controller.stop()
                db.set_automation_running(st.session_state.user_id, False)
                if stopped:
                    st.success("⏹️ Automation stopped.")
                else:
                    st.warning("⚠️ Automation was not running.")
                time.sleep(1)
                st.experimental_rerun()

        st.markdown('<div class="console-section"><h4 class="console-header"><i class="fas fa-terminal"></i> Live Console Monitor</h4></div>', unsafe_allow_html=True)

        logs = fetch_logs()
        if logs:
            logs_html = '<div class="console-output">'
            for log in logs[-200:]:
                logs_html += f'<div class="console-line">{log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="console-output"><div class="console-line">🚀 Console ready... Start automation to see logs here.</div></div>', unsafe_allow_html=True)

        if st.session_state.automation_controller.is_running():
            time.sleep(1)
            st.experimental_rerun()

st.markdown('<div class="footer">THE OG ON FIRE<br>All Rights Reserved</div>', unsafe_allow_html=True)

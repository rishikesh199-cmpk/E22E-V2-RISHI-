# ================= CLEAN STREAMLIT AUTOMATION =================
import streamlit as st
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import database as db  # your database module

st.set_page_config(page_title="E2EE Automation", page_icon="🔥", layout="wide")

# ---------------- CSS ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #fff;
}

/* Glowing card */
.glow-card {
    background: rgba(0,0,0,0.4);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 15px;
    border: 2px solid;
    border-image-slice: 1;
    border-width: 3px;
    border-image-source: linear-gradient(45deg, #ff00d4, #00eaff, #fffb00, #ff00d4);
    box-shadow: 0 0 20px rgba(0,255,255,0.4), 0 0 30px rgba(255,0,212,0.4);
    animation: glowing 3s linear infinite;
}

/* Glowing animation */
@keyframes glowing {
    0% { box-shadow: 0 0 5px #ff00d4, 0 0 10px #00eaff, 0 0 15px #fffb00; }
    50% { box-shadow: 0 0 20px #ff00d4, 0 0 30px #00eaff, 0 0 40px #fffb00; }
    100% { box-shadow: 0 0 5px #ff00d4, 0 0 10px #00eaff, 0 0 15px #fffb00; }
}

/* Logo */
.dashboard-logo {
    width: 80px;
    border-radius: 50%;
    margin-bottom: 15px;
}

/* Live logs box */
.live-log {
    background: rgba(0,0,0,0.3);
    border-radius: 15px;
    padding: 10px;
    height: 300px;
    overflow-y: auto;
    font-family: monospace;
    font-size: 14px;
    border: 2px solid #00eaff;
    box-shadow: 0 0 10px #00eaff;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="glow-card"><h2 style="text-align:center;">⚡ E2EE AUTOMATION</h2></div>', unsafe_allow_html=True)

# ---------------- SESSION VARS ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'automation_running' not in st.session_state: st.session_state.automation_running = False
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type('obj',(object,),{"running":False,"message_count":0,"message_rotation_index":0})()
if 'logs' not in st.session_state: st.session_state.logs = []

# ---------------- LOGIN & CREATE USER ----------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["User Login", "Create Account"])

    # USER LOGIN
    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            uid = db.verify_user(u, p)
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                st.rerun()
            else:
                st.error("Invalid username/password")

    # CREATE ACCOUNT
    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        npc = st.text_input("Confirm Password", type="password")
        if st.button("Create User"):
            if np != npc:
                st.error("Passwords do not match!")
            else:
                ok, msg = db.create_user(nu, np)
                if ok: st.success("User Created! You can now login.")
                else: st.error(msg)

    st.stop()

# ---------------- DASHBOARD ----------------
st.subheader("👤 User Dashboard")

# Logo
st.image("https://i.imgur.com/YourLogo.png", width=80, use_column_width=False, caption="E2EE Automation")  # replace with your logo URL

# ---------------- MESSAGE FILE UPLOAD ----------------
st.markdown("### 📂 Upload .txt Messages File")
msg_file = st.file_uploader("Upload messages", type=["txt"])
msgs = []
if msg_file:
    msgs = msg_file.read().decode("utf-8").split("\n")
    st.success("Messages loaded!")

# ---------------- CONFIG ----------------
chat_id = st.text_input("Chat ID")
chat_type = st.radio("Chat Type", ["E2EE", "Regular"])  # New option
delay = st.number_input("Delay (sec)", 1, 300, 15)
cookies = st.text_area("Cookies")

if st.button("Save Config"):
    db.update_user_config(
        st.session_state.user_id,
        chat_id,
        chat_type,
        delay,
        cookies,
        "\n".join(msgs)
    )
    st.success("Saved!")

# ---------------- AUTOMATION ENGINE ----------------
from selenium.webdriver.chrome.service import Service

def setup_browser():
    opt = Options()
    opt.add_argument('--headless=new')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=opt)

def find_input(driver, chat_type="E2EE"):
    if chat_type == "E2EE":
        selectors = [
            "div[contenteditable='true'][aria-label='Send a message']",
            "div[contenteditable='true']"
        ]
    else:
        selectors = [
            "div[contenteditable='true']",
            "textarea",
            "[role='textbox']"
        ]
    for sel in selectors:
        try:
            return driver.find_element(By.CSS_SELECTOR, sel)
        except:
            pass
    return None

def update_log(message):
    st.session_state.logs.append(message)
    log_box.markdown('<div class="live-log">' + "<br>".join(st.session_state.logs[-50:]) + '</div>', unsafe_allow_html=True)

def send_messages(cfg, stt):
    d = setup_browser()
    d.get("https://www.facebook.com")
    time.sleep(8)

    # Add cookies
    for c in (cfg.get('cookies') or "").split(';'):
        if '=' in c:
            n,v=c.split('=',1)
            try: d.add_cookie({"name":n.strip(),"value":v.strip(),"domain":".facebook.com","path":"/"})
            except: pass

    d.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
    time.sleep(10)

    box = find_input(d, chat_type=cfg.get('chat_type','E2EE'))
    if not box:
        stt.running = False
        update_log("❌ Chat box not found!")
        return

    msgs = [m for m in (cfg.get('messages') or "").split("\n") if m.strip()]
    if not msgs:
        msgs = ["Hello!"]

    while stt.running:
        m = msgs[stt.message_rotation_index % len(msgs)]
        stt.message_rotation_index += 1
        try:
            box.send_keys(m)
            box.send_keys("\n")
            stt.message_count += 1
            update_log(f"✅ Sent: {m}")
        except Exception as e:
            update_log(f"❌ Error sending message: {e}")
        time.sleep(int(cfg.get('delay',15)))

    d.quit()

# ---------------- AUTOMATION UI ----------------
st.markdown('<div class="glow-card">🚀 Automation Controls</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

if col1.button("▶️ START", disabled=st.session_state.automation_running):
    cfg = db.get_user_config(st.session_state.user_id)
    if not cfg or not cfg.get('chat_id'):
        st.error("Please save a Chat ID in config first.")
    else:
        st.session_state.automation_state.running = True
        st.session_state.automation_running = True
        t = threading.Thread(target=send_messages, args=(cfg, st.session_state.automation_state))
        t.daemon = True
        t.start()
        st.rerun()

if col2.button("⏹️ STOP", disabled=not st.session_state.automation_running):
    st.session_state.automation_state.running = False
    st.session_state.automation_running = False
    st.rerun()

# ---------------- LIVE LOGS ----------------
st.markdown('<div class="glow-card">📡 Live Logs</div>', unsafe_allow_html=True)
log_box = st.empty()

# Initial empty log display
log_box.markdown('<div class="live-log"></div>', unsafe_allow_html=True)

# ---------------- MESSAGES SENT COUNT ----------------
st.write(f"📤 Total Messages Sent: {st.session_state.automation_state.message_count}")

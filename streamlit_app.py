# ---------------- CLEAN STREAMLIT SCRIPT ----------------
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
.stApp{background:#0d0d0d;} 
.title{font-size:2.5rem;font-weight:900;text-align:center;background:linear-gradient(90deg,#00eaff,#ff00d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.card{background:rgba(255,255,255,0.06);padding:20px;border-radius:12px;border:1px solid rgba(255,255,255,0.2);} 
.stButton>button{background:linear-gradient(45deg,#00eaff,#ff00d4);color:#fff;border:none;border-radius:10px;padding:10px 25px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">⚡ E2EE AUTOMATION</div>', unsafe_allow_html=True)

# ---------------- SESSION VARS ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'automation_running' not in st.session_state: st.session_state.automation_running = False
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type('obj',(object,),{"running":False,"message_count":0,"message_rotation_index":0})()

# ---------------- LOGIN SYSTEM ----------------
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
                ok, msg = db.create_user(nu, np, approved=True)  # approved by default
                if ok: st.success("User Created! You can now login.")
                else: st.error(msg)

    st.stop()

# ---------------- USER DASHBOARD ----------------
st.subheader("👤 User Dashboard")

# ---------------- CHAT TYPE SELECTOR ----------------
if 'chat_type' not in st.session_state:
    st.session_state.chat_type = "E2EE Chat ID"

chat_type = st.selectbox(
    "Select Chat Type",
    ["E2EE Chat ID", "Normal Thread ID"],
    index=0 if st.session_state.chat_type=="E2EE Chat ID" else 1,
    key="chat_type"
)

# ---------------- CHAT ID / THREAD ----------------
if chat_type == "Normal Thread ID":
    # Example threads - replace with DB fetch if needed
    normal_threads = {
        "Friend 1": "123456789",
        "Friend 2": "987654321",
        "Group Chat": "555666777"
    }
    selected_thread = st.selectbox(
        "Select Thread",
        options=list(normal_threads.keys()),
        key="normal_thread_selector"
    )
    chat_id = normal_threads[selected_thread]
else:
    chat_id = st.text_input("Chat ID", value=st.session_state.get('chat_id_input',''), key="chat_id_input")

# ---------------- FILE UPLOAD ----------------
st.markdown("### 📂 Upload .txt Messages File")
msg_file = st.file_uploader("Upload messages", type=["txt"])
msgs = []
if msg_file:
    msgs = [m.strip() for m in msg_file.read().decode("utf-8").split("\n") if m.strip()]
    st.success(f"{len(msgs)} messages loaded!")

# ---------------- CONFIG ----------------
delay = st.number_input("Delay (sec)", 1, 300, value=st.session_state.get('delay',15), key="delay")
cookies = st.text_area("Cookies", value=st.session_state.get('cookies',''), key="cookies")

if st.button("Save Config"):
    db.update_user_config(st.session_state.user_id, chat_id, "", delay, cookies, "\n".join(msgs))
    st.success("Saved!")

# ---------------- AUTOMATION ENGINE ----------------
from selenium.webdriver.chrome.service import Service

def setup_browser():
    opt = Options()
    opt.add_argument('--headless=new')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=opt)

def find_input(driver):
    sels=["div[contenteditable='true']","textarea","[role='textbox']"]
    for s in sels:
        try: return driver.find_element(By.CSS_SELECTOR,s)
        except: pass
    return None

def send_messages(cfg, stt):
    d = setup_browser()
    d.get("https://www.facebook.com")
    time.sleep(8)

    for c in (cfg.get('cookies') or "").split(';'):
        if '=' in c:
            n,v=c.split('=',1)
            try: d.add_cookie({"name":n.strip(),"value":v.strip(),"domain":".facebook.com","path":"/"})
            except: pass

    d.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
    time.sleep(10)

    box=find_input(d)
    if not box:
        st.warning("Unable to find message input box.")
        stt.running=False
        return

    msgs=[m for m in (cfg.get('messages') or "").split("\n") if m.strip()]
    if not msgs:
        msgs = ["Hello!"]

    while stt.running:
        m=msgs[stt.message_rotation_index % len(msgs)]
        stt.message_rotation_index+=1
        try:
            box.send_keys(m)
            box.send_keys("\n")
            stt.message_count+=1
        except Exception:
            pass
        time.sleep(int(cfg.get('delay',15)))

    d.quit()

# ---------------- AUTOMATION CONTROL ----------------
st.subheader("🚀 Automation Control")
col1, col2 = st.columns(2)

if col1.button("▶️ START", disabled=st.session_state.automation_running):
    if not chat_id:
        st.error("Please enter/select a Chat ID.")
    elif not msgs:
        st.error("Please upload a messages file first.")
    else:
        cfg = {
            "chat_type": chat_type,
            "chat_id": chat_id,
            "messages": "\n".join(msgs),
            "delay": delay,
            "cookies": cookies
        }
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

# ---------------- LIVE STATUS ----------------
st.write(f"📡 Messages Sent: {st.session_state.automation_state.message_count}")

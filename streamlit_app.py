import streamlit as st
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import database as db

st.set_page_config(page_title="Automation Dashboard", page_icon="🔥", layout="wide")

# ---------------- CSS / STYLING ----------------
st.markdown("""
<style>
/* Full HD background */
.stApp {
    background: url('https://i.ibb.co/9k1k2c6f/bg.png') no-repeat center center fixed;
    background-size: cover;  /* keeps full image visible */
}

/* Overlay for readability */
.stApp::before {
    content: "";
    position: fixed;
    top:0; left:0; width:100%; height:100%;
    background: rgba(0,0,0,0.2);
    pointer-events:none;
    z-index:0;
}

/* Cards */
.stCard {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 20px !important;
    padding: 25px !important;
    border: 2px solid rgba(255,255,255,0.25) !important;
    box-shadow: 0 0 25px rgba(0,255,255,0.4), 0 0 60px rgba(255,0,255,0.3);
    transition: all 0.3s ease-in-out;
}
.stCard:hover {
    box-shadow: 0 0 35px rgba(0,255,255,0.6), 0 0 70px rgba(255,0,255,0.5);
}

/* Inputs glowing */
input, textarea {
    background: rgba(0,0,0,0.5) !important;
    border: 2px solid #0ff !important;
    border-radius: 10px !important;
    color: #0ff !important;
    padding: 5px 10px !important;
}
input:focus, textarea:focus {
    outline: none;
    border: 2px solid #ff00ff !important;
    box-shadow: 0 0 15px #ff00ff;
}

/* Buttons glowing */
.stButton>button {
    background: linear-gradient(45deg,#00eaff,#ff00d4) !important;
    color:#fff !important;
    border:none !important;
    border-radius:10px !important;
    padding:10px 25px !important;
    font-weight:700 !important;
}

/* Logo */
.logo {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    animation: pulse 2s infinite;
    display:block;
    margin:auto;
}
@keyframes pulse {
    0% { transform: scale(1); box-shadow: 0 0 15px rgba(0,255,255,0.6); }
    50% { transform: scale(1.12); box-shadow: 0 0 40px rgba(0,255,255,0.8); }
    100% { transform: scale(1); box-shadow: 0 0 15px rgba(0,255,255,0.6); }
}

/* Title: watercolor text */
.title {
    font-family: 'Orbitron', sans-serif;
    font-size: 3.2rem;
    font-weight: 900;
    text-align:center;
    background: url('https://i.ibb.co/0G6Kj8V/watercolor-texture.jpg') repeat;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-size: cover;
    animation: waterFlow 6s ease-in-out infinite;
    margin-bottom: 25px;
}
@keyframes waterFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Live logs */
.logbox {
    background: rgba(0,0,0,0.55);
    color: #0ff;
    padding: 15px;
    height: 300px;
    overflow:auto;
    border-radius: 20px;
    box-shadow: 0 0 20px rgba(0,255,255,0.35);
}

/* Sparkles */
@keyframes sparkle {
    0% { transform: translate(0,0) rotate(0deg); opacity:1; }
    100% { transform: translate(100px,-100px) rotate(360deg); opacity:0; }
}
.sparkle {
    position: absolute;
    width: 6px;
    height: 6px;
    background: linear-gradient(45deg, #0ff, #f0f, #ff0);
    border-radius: 50%;
    animation: sparkle 2s linear infinite;
}
</style>

<img class="logo" src="https://i.ibb.co/m5G9GdXx/logo.png" alt="Logo">
<div class="sparkle" style="top:5%; left:5%;"></div>
<div class="sparkle" style="top:10%; right:10%;"></div>
<div class="sparkle" style="bottom:10%; left:15%;"></div>
<div class="sparkle" style="bottom:5%; right:5%;"></div>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown('<div class="title">⚡ E2EE / Non-E2EE AUTOMATION DASHBOARD</div>', unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in=False
if 'user_id' not in st.session_state: st.session_state.user_id=None
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type('obj', (object,), {
        "running": False,
        "message_count": 0,
        "message_rotation_index": 0,
        "logs": []
    })()
if 'messages' not in st.session_state: st.session_state.messages = []

# ---------------- LOGIN / CREATE ----------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login","Create Account"])
    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            uid = db.verify_user(u,p)
            if uid:
                st.session_state.logged_in=True
                st.session_state.user_id=uid
                cfg = db.get_user_config(uid)
                st.session_state.chat_id = cfg.get('chat_id','')
                st.session_state.chat_type = cfg.get('chat_type','E2EE')
                st.session_state.delay = cfg.get('delay',15)
                st.session_state.cookies = cfg.get('cookies','')
                st.session_state.messages = cfg.get('messages','').split("\n") if cfg.get('messages') else []
                if cfg.get('running',False):
                    st.session_state.automation_state.running=True
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        npc = st.text_input("Confirm Password", type="password")
        if st.button("Create User"):
            if np != npc:
                st.error("Passwords do not match")
            else:
                ok,msg = db.create_user(nu,np)
                if ok:
                    st.success("User created!")
                else:
                    st.error(msg)
    st.stop()

# ---------------- DASHBOARD ----------------
st.subheader(f"👤 Dashboard ({st.session_state.user_id})")
if st.button("Logout"):
    st.session_state.logged_in=False
    st.session_state.user_id=None
    st.session_state.automation_state.running=False
    st.rerun()

# ---------------- MESSAGE UPLOAD ----------------
msg_file = st.file_uploader("Upload .txt Messages File", type=["txt"])
if msg_file:
    st.session_state.messages = msg_file.read().decode("utf-8").split("\n")
    st.success("Messages loaded!")

# ---------------- CONFIG ----------------
chat_id = st.text_input("Chat ID", value=st.session_state.get('chat_id',''))
chat_type = st.selectbox("Chat Type", ["E2EE","Non-E2EE"], index=0 if st.session_state.get('chat_type','E2EE')=='E2EE' else 1)
delay = st.number_input("Delay (sec)", 1, 300, value=st.session_state.get('delay',15))
cookies = st.text_area("Cookies", value=st.session_state.get('cookies',''))

if st.button("Save Config"):
    db.update_user_config(st.session_state.user_id, chat_id, chat_type, delay, cookies, "\n".join(st.session_state.messages), running=st.session_state.automation_state.running)
    st.success("Saved!")

# ---------------- AUTOMATION PLACEHOLDERS ----------------
log_placeholder = st.empty()
msg_count_placeholder = st.empty()

# ---------------- AUTOMATION FUNCTIONS ----------------
def setup_browser():
    opt = Options()
    # Remove headless if messages blocked
    # opt.add_argument('--headless=new')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=opt)

def find_input(driver, chat_type):
    if chat_type=="E2EE":
        try: return driver.find_element(By.CSS_SELECTOR,"div[contenteditable='true']")
        except: return None
    else:
        for s in ["div[contenteditable='true']","textarea","[role='textbox']"]:
            elems = driver.find_elements(By.CSS_SELECTOR,s)
            if elems: return elems[0]
        return None

def send_messages(cfg, stt):
    stt.logs.append("🚀 Automation started")
    try:
        driver = setup_browser()
        driver.get("https://www.facebook.com")
        time.sleep(8)
        for c in (cfg.get('cookies') or "").split(";"):
            if "=" in c:
                n,v = c.split("=",1)
                try: driver.add_cookie({"name":n.strip(),"value":v.strip(),"domain":".facebook.com","path":"/"})
                except: stt.logs.append(f"❌ Cookie failed: {c}")
        driver.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
        time.sleep(10)
        stt.logs.append(f"Opened chat: {cfg.get('chat_id','')}")
        box = find_input(driver, cfg.get('chat_type','E2EE'))
        if not box:
            stt.logs.append("❌ Input box not found!")
            stt.running=False
            return
        msgs = [m for m in (cfg.get('messages') or "").split("\n") if m.strip()]
        if not msgs: msgs=["Hello!"]
        while stt.running:
            m = msgs[stt.message_rotation_index % len(msgs)]
            stt.message_rotation_index +=1
            try:
                box.send_keys(m)
                box.send_keys("\n")
                stt.message_count +=1
                stt.logs.append(f"✅ Sent: {m}")
            except Exception as e:
                stt.logs.append(f"❌ Error: {e}")
            time.sleep(int(cfg.get('delay',15)))
        driver.quit()
        stt.logs.append("⏹️ Automation stopped")
    except Exception as e:
        stt.logs.append(f"❌ Browser error: {e}")
        stt.running=False

# ---------------- AUTOMATION CONTROLS ----------------
col1, col2 = st.columns(2)
if col1.button("▶️ START"):
    if not st.session_state.automation_state.running:
        cfg = {
            "chat_id": chat_id,
            "chat_type": chat_type,
            "cookies": cookies,
            "messages": st.session_state.messages,
            "delay": delay
        }
        st.session_state.automation_state.running=True
        t = threading.Thread(target=send_messages, args=(cfg, st.session_state.automation_state))
        t.daemon=True
        t.start()
    else:
        st.warning("⚠️ Automation is already running!")

if col2.button("⏹️ STOP"):
    st.session_state.automation_state.running=False
    st.session_state.automation_state.logs.append("⏹️ Automation stopped manually")

# ---------------- LIVE LOGS ----------------
while st.session_state.automation_state.running:
    msg_count_placeholder.write(f"📡 Messages Sent: {st.session_state.automation_state.message_count}")
    logs_to_show = "\n".join(st.session_state.automation_state.logs[-50:])
    log_placeholder.code(logs_to_show)
    time.sleep(1)

msg_count_placeholder.write(f"📡 Messages Sent: {st.session_state.automation_state.message_count}")
log_placeholder.code("\n".join(st.session_state.automation_state.logs[-50:]))

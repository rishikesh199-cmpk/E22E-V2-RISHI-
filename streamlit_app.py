import streamlit as st
import threading, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import database as db

st.set_page_config(page_title="E23E FB Multi-Convo", page_icon="🔥", layout="wide")

# ---------------- CSS & GLASS STYLING ----------------
st.markdown("""
<style>
.stApp { background: url('https://i.ibb.co/9k1k2c6f/bg.png') no-repeat center center fixed; background-size: cover; color:#0ff; }
.stCard { background: rgba(0,0,0,0.25) !important; border-radius: 25px; padding: 25px; border:2px solid rgba(255,255,255,0.2); backdrop-filter: blur(12px); box-shadow:0 0 25px rgba(0,255,255,0.4),0 0 60px rgba(255,0,255,0.3); transition:0.3s; margin-bottom:15px; }
.stCard:hover { box-shadow:0 0 35px rgba(0,255,255,0.6),0 0 70px rgba(255,0,255,0.5); }
input, textarea { background: rgba(0,0,0,0.5); border: 2px solid #0ff; border-radius:12px; color:#0ff; padding:5px 12px; }
input:focus, textarea:focus { outline:none; border:2px solid #ff00ff; box-shadow:0 0 15px #ff00ff; }
.stButton>button { background: linear-gradient(45deg,#00eaff,#ff00d4); color:#fff; border:none; border-radius:12px; padding:12px 28px; font-weight:700; }
.logo { width:120px; height:120px; border-radius:50%; animation:pulse 2s infinite; display:block; margin:auto;}
@keyframes pulse {0% {transform: scale(1); box-shadow:0 0 15px rgba(0,255,255,0.6);}50%{transform: scale(1.12); box-shadow:0 0 40px rgba(0,255,255,0.8);}100%{transform: scale(1); box-shadow:0 0 15px rgba(0,255,255,0.6);}}
.title {font-family: 'Orbitron', sans-serif; font-size:3rem; font-weight:900; text-align:center; background:url('https://i.ibb.co/0G6Kj8V/watercolor-texture.jpg') repeat; -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-size:cover; animation:waterFlow 6s ease-in-out infinite; margin-bottom:20px;}
@keyframes waterFlow {0%{background-position:0% 50%;}50%{background-position:100% 50%;}100%{background-position:0% 50%;}}
.logbox {background: rgba(0,0,0,0.5); color:#0ff; padding:15px; height:250px; overflow:auto; border-radius:20px; box-shadow:0 0 20px rgba(0,255,255,0.35);}
</style>
<img class="logo" src="https://i.ibb.co/m5G9GdXx/logo.png">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown('<div class="title"><h1>E23E FB Multi-Convo Dashboard</h1></div>', unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in=False
if 'user_id' not in st.session_state: st.session_state.user_id=None
if 'conversations' not in st.session_state:
    st.session_state.conversations = {}  # {chat_id: {"running":bool,"logs":[],"rotation_index":int,"last_reboot":float,"thread":threading.Thread}}

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    tab1,tab2 = st.tabs(["Login","Create Account"])
    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            uid = db.verify_user(u,p)
            if uid:
                st.session_state.logged_in=True
                st.session_state.user_id=uid
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        npc = st.text_input("Confirm Password", type="password")
        if st.button("Create User"):
            if np!=npc: st.error("Passwords do not match")
            else:
                ok,msg = db.create_user(nu,np)
                if ok: st.success("User created!")
                else: st.error(msg)
    st.stop()

# ---------------- DASHBOARD ----------------
st.subheader(f"👤 Dashboard ({st.session_state.user_id})")
if st.button("Logout"):
    st.session_state.logged_in=False
    st.session_state.user_id=None
    for conv in st.session_state.conversations.values(): conv['running']=False
    st.rerun()

# ---------------- CONVERSATION MANAGEMENT ----------------
st.markdown("---")
st.subheader("📩 Manage Conversations")

with st.expander("Add / Load Conversation"):
    chat_id = st.text_input("Chat ID")
    chat_type = st.selectbox("Chat Type", ["E2EE","Non-E2EE"], index=0)
    delay = st.number_input("Delay (sec)",1,300,15)
    cookies = st.text_area("Cookies")
    msg_file = st.file_uploader("Upload .txt Messages File", type=["txt"])
    messages = []
    if msg_file: messages = msg_file.read().decode("utf-8").split("\n")
    if st.button("Add Conversation"):
        if not chat_id or not messages: st.error("Chat ID and messages required")
        else:
            st.session_state.conversations[chat_id] = {
                "running": False,
                "logs": [],
                "rotation_index": 0,
                "last_reboot": time.time(),
                "thread": None,
                "chat_type": chat_type,
                "delay": delay,
                "cookies": cookies,
                "messages": messages
            }
            st.success(f"Conversation {chat_id} added!")

# ---------------- AUTOMATION ENGINE ----------------
def setup_browser(cfg):
    opt=Options()
    opt.add_argument('--headless=new')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    driver=webdriver.Chrome(options=opt)
    driver.get("https://www.facebook.com")
    time.sleep(5)
    # Add cookies
    for c in (cfg.get('cookies') or "").split(";"):
        if "=" in c:
            n,v=c.split("=",1)
            try: driver.add_cookie({"name":n.strip(),"value":v.strip(),"domain":".facebook.com","path":"/"})
            except: pass
    return driver

def find_input(driver,chat_type):
    selectors=["div[contenteditable='true']"] if chat_type=="E2EE" else ["div[contenteditable='true']","textarea","[role='textbox']"]
    for s in selectors:
        try: return driver.find_element(By.CSS_SELECTOR,s)
        except: pass
    return None

def send_messages(cfg, conv_state, log_container):
    conv_state['running']=True
    conv_state['logs'].append(f"Starting browser for {cfg['chat_id']}...")
    d = setup_browser(cfg)
    d.get(f"https://www.facebook.com/messages/t/{cfg['chat_id']}")
    time.sleep(8)
    conv_state['logs'].append(f"Opened chat {cfg['chat_id']}")
    box = find_input(d, cfg['chat_type'])
    if not box:
        conv_state['logs'].append("Input box not found!")
        conv_state['running']=False
        return
    msgs = cfg['messages'] or ["Hello!"]
    while conv_state['running']:
        m = msgs[conv_state['rotation_index'] % len(msgs)]
        conv_state['rotation_index'] +=1
        try:
            box.send_keys(m + Keys.ENTER)
            conv_state['logs'].append(f"Sent: {m}")
        except Exception as e:
            conv_state['logs'].append(f"Error: {e}")
        log_container.markdown("<br>".join(conv_state['logs'][-50:]), unsafe_allow_html=True)
        time.sleep(cfg.get('delay',15))
        if time.time() - conv_state['last_reboot'] > 36000:
            conv_state['logs'].append("Auto-rebooting automation...")
            conv_state['last_reboot']=time.time()
            conv_state['rotation_index']=0
            conv_state['logs'].append("Automation restarted after reboot.")

# ---------------- DISPLAY & CONTROL ----------------
for cid, conv in st.session_state.conversations.items():
    with st.container():
        st.markdown(f'<div class="stCard"><h3>Chat: {cid}</h3>', unsafe_allow_html=True)
        st.write(f"Messages Sent: {conv['rotation_index']}")
        log_placeholder = st.empty()
        log_placeholder.markdown("<br>".join(conv['logs'][-50:]), unsafe_allow_html=True)
        col1,col2=st.columns(2)
        if col1.button(f"▶️ START {cid}", key=f"start_{cid}", disabled=conv['running']):
            cfg = conv.copy()
            cfg['chat_id'] = cid
            t=threading.Thread(target=send_messages, args=(cfg, conv, log_placeholder))
            t.daemon=True
            conv['thread'] = t
            t.start()
        if col2.button(f"⏹️ STOP {cid}", key=f"stop_{cid}", disabled=not conv['running']):
            conv['running']=False
        st.markdown('</div>', unsafe_allow_html=True)

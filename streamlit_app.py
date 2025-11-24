import streamlit as st
import threading, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import database as db  # Your database module
import datetime

st.set_page_config(page_title="E23E FB Automation", page_icon="🔥", layout="wide")

# ---------------- CSS & GLASS STYLING ----------------
st.markdown("""
<style>
.stApp {
    background: url('https://i.ibb.co/9k1k2c6f/bg.png') no-repeat center center fixed;
    background-size: cover;
    color:#0ff;
}
.stCard {
    background: rgba(0,0,0,0.25) !important;
    border-radius: 25px !important;
    padding: 25px !important;
    border: 2px solid rgba(255,255,255,0.2) !important;
    backdrop-filter: blur(12px);
    box-shadow: 0 0 25px rgba(0,255,255,0.4), 0 0 60px rgba(255,0,255,0.3);
    transition: all 0.3s ease-in-out;
}
.stCard:hover {
    box-shadow: 0 0 35px rgba(0,255,255,0.6), 0 0 70px rgba(255,0,255,0.5);
}
input, textarea {
    background: rgba(0,0,0,0.5) !important;
    border: 2px solid #0ff !important;
    border-radius: 12px !important;
    color: #0ff !important;
    padding: 5px 12px !important;
}
input:focus, textarea:focus { outline:none; border:2px solid #ff00ff !important; box-shadow:0 0 15px #ff00ff; }
.stButton>button {
    background: linear-gradient(45deg,#00eaff,#ff00d4) !important;
    color:#fff !important;
    border:none !important;
    border-radius:12px !important;
    padding:12px 28px !important;
    font-weight:700 !important;
}
.logo { width:120px; height:120px; border-radius:50%; animation:pulse 2s infinite; display:block; margin:auto;}
@keyframes pulse {0% {transform: scale(1); box-shadow:0 0 15px rgba(0,255,255,0.6);}50% {transform: scale(1.12); box-shadow:0 0 40px rgba(0,255,255,0.8);}100% {transform: scale(1); box-shadow:0 0 15px rgba(0,255,255,0.6);}}
.title {font-family: 'Orbitron', sans-serif; font-size:3rem; font-weight:900; text-align:center; background:url('https://i.ibb.co/0G6Kj8V/watercolor-texture.jpg') repeat; -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-size:cover; animation:waterFlow 6s ease-in-out infinite; margin-bottom:20px;}
@keyframes waterFlow {0%{background-position:0% 50%;}50%{background-position:100% 50%;}100%{background-position:0% 50%;}}
.logbox {background: rgba(0,0,0,0.5); color:#0ff; padding:15px; height:350px; overflow:auto; border-radius:20px; box-shadow:0 0 20px rgba(0,255,255,0.35);}
</style>
<img class="logo" src="https://i.ibb.co/m5G9GdXx/logo.png">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown('<div class="title"><h1>E23E FB Automation</h1></div>', unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in=False
if 'user_id' not in st.session_state: st.session_state.user_id=None
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = {
        "running": False,
        "logs": [],
        "message_count": 0,
        "rotation_index": 0,
        "last_reboot": time.time()
    }

# ---------------- LOGIN / CREATE ----------------
if not st.session_state.logged_in:
    tab1,tab2=st.tabs(["Login","Create Account"])
    with tab1:
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Login"):
            uid=db.verify_user(u,p)
            if uid:
                st.session_state.logged_in=True
                st.session_state.user_id=uid
                cfg=db.get_user_config(uid)
                # Load previous settings
                st.session_state.chat_id=cfg.get('chat_id','')
                st.session_state.chat_type=cfg.get('chat_type','E2EE')
                st.session_state.delay=cfg.get('delay',15)
                st.session_state.cookies=cfg.get('cookies','')
                st.session_state.messages=cfg.get('messages','').split("\n") if cfg.get('messages') else []
                st.session_state.automation_state['running'] = cfg.get('running', False)
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        nu=st.text_input("New Username")
        np=st.text_input("New Password",type="password")
        npc=st.text_input("Confirm Password",type="password")
        if st.button("Create User"):
            if np!=npc: st.error("Passwords do not match")
            else:
                ok,msg=db.create_user(nu,np)
                if ok: st.success("User created!")
                else: st.error(msg)
    st.stop()

# ---------------- DASHBOARD ----------------
st.subheader(f"👤 Dashboard ({st.session_state.user_id})")
if st.button("Logout"):
    st.session_state.logged_in=False
    st.session_state.user_id=None
    st.session_state.automation_state['running']=False
    st.rerun()

# ---------------- CONFIG ----------------
msg_file=st.file_uploader("Upload .txt Messages File",type=["txt"])
if msg_file:
    st.session_state.messages=msg_file.read().decode("utf-8").split("\n")
    st.success("Messages loaded!")

chat_id=st.text_input("Chat ID", value=getattr(st.session_state,'chat_id',''))
chat_type=st.selectbox("Chat Type", ["E2EE","Non-E2EE"], index=0 if getattr(st.session_state,'chat_type','E2EE')=='E2EE' else 1)
delay=st.number_input("Delay (sec)",1,300,value=getattr(st.session_state,'delay',15))
cookies=st.text_area("Cookies",value=getattr(st.session_state,'cookies',''))

if st.button("Save Config"):
    db.update_user_config(st.session_state.user_id,chat_id,chat_type,delay,cookies,"\n".join(st.session_state.messages),running=st.session_state.automation_state['running'])
    st.success("Saved!")

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

def send_messages(cfg, stt, log_container):
    stt['running'] = True
    stt['logs'].append("Starting browser...")
    d=setup_browser(cfg)
    d.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
    time.sleep(8)
    stt['logs'].append(f"Opened chat {cfg.get('chat_id','')}")
    box=find_input(d,cfg.get('chat_type','E2EE'))
    if not box:
        stt['logs'].append("Input box not found!")
        stt['running']=False
        return
    msgs=cfg.get('messages') or ["Hello!"]
    while stt['running']:
        m=msgs[stt['rotation_index'] % len(msgs)]
        stt['rotation_index'] +=1
        try:
            box.send_keys(m + Keys.ENTER)
            stt['message_count'] +=1
            stt['logs'].append(f"Sent: {m}")
        except Exception as e:
            stt['logs'].append(f"Error: {e}")
        # Update live logs
        log_container.markdown("<br>".join(stt['logs'][-50:]), unsafe_allow_html=True)
        time.sleep(cfg.get('delay',15))
        # Auto-reboot check
        if time.time() - stt.get('last_reboot',0) > 36000:  # 10 hours
            stt['logs'].append("Auto-rebooting automation...")
            db.update_user_config(st.session_state.user_id, chat_id, chat_type, delay, cookies, "\n".join(st.session_state.messages), running=True)
            stt['last_reboot'] = time.time()
            stt['rotation_index'] = 0
            stt['message_count'] = 0
            stt['logs'].append("Automation restarted after reboot.")

# ---------------- AUTOMATION CONTROLS ----------------
st.subheader("🚀 Automation")
col1,col2=st.columns(2)
log_container = st.empty()

if col1.button("▶️ START",disabled=st.session_state.automation_state['running']):
    cfg = {
        "chat_id": chat_id,
        "chat_type": chat_type,
        "delay": delay,
        "cookies": cookies,
        "messages": st.session_state.messages
    }
    st.session_state.automation_state['running'] = True
    t=threading.Thread(target=send_messages, args=(cfg, st.session_state.automation_state, log_container))
    t.daemon=True
    t.start()

if col2.button("⏹️ STOP",disabled=not st.session_state.automation_state['running']):
    st.session_state.automation_state['running'] = False

# ---------------- LIVE LOGS ----------------
st.subheader("📡 Live Logs & Messages Sent")
st.markdown(f"Messages Sent: {st.session_state.automation_state['message_count']}")
log_container.markdown("<br>".join(st.session_state.automation_state['logs'][-50:]), unsafe_allow_html=True)

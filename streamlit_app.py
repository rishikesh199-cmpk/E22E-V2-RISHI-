import streamlit as st
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import database as db
import os, shutil, subprocess

st.set_page_config(page_title="OFFLINE💋PY", page_icon="🏴‍☠️", layout="wide")

# ======= Transparent Blue Theme =======
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
.stApp {
  background-image: url('https://i.postimg.cc/L51fQrQH/681be2a77443fb2f2f74fd42da1bc40f.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
.main .block-container {
  background: rgba(18,24,32,0.45);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 14px;
  box-shadow: 0 6px 30px rgba(14,165,233,0.08);
}
.stButton>button {
  background: linear-gradient(90deg, rgba(14,165,233,1), rgba(56,189,248,1));
  border:none;
  color:white;
  border-radius:10px;
  padding:0.6rem 1.2rem;
  font-weight:700;
  transition: all .2s;
}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 12px 24px rgba(14,165,233,0.15);}
.console-output{background:rgba(0,0,0,0.5);border-radius:10px;padding:10px;color:#9ef;font-family:monospace;font-size:13px;max-height:400px;overflow-y:auto;}
</style>
""", unsafe_allow_html=True)

# ======= Session defaults =======
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'automation_state' not in st.session_state:
    class Auto: 
        running=False; message_count=0; logs=[]; message_rotation_index=0
    st.session_state.automation_state = Auto()

def log(msg):
    t = time.strftime("%H:%M:%S")
    st.session_state.automation_state.logs.append(f"[{t}] {msg}")

# ======= Browser setup fix =======
def setup_browser():
    log("Setting up Chrome browser...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--remote-debugging-port=9222")

    chrome_path = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    driver_path = shutil.which("chromedriver")

    if not chrome_path or not driver_path:
        log("Installing Chromium & Chromedriver...")
        try:
            subprocess.run(["apt-get","update"],check=True)
            subprocess.run(["apt-get","install","-y","chromium-browser","chromium-chromedriver"],check=True)
        except Exception as e:
            log(f"Install failed: {e}")

    chrome_path = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    driver_path = shutil.which("chromedriver")
    if not chrome_path: raise Exception("❌ Chrome binary not found.")
    if not driver_path: raise Exception("❌ Chromedriver not found.")

    chrome_options.binary_location = chrome_path
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(1920,1080)
    log("✅ Chrome started successfully.")
    return driver

# ======= Automation =======
def send_messages(cfg,user_id):
    state = st.session_state.automation_state
    try:
        driver = setup_browser()
        log("Opening Facebook...")
        driver.get("https://www.facebook.com/")
        time.sleep(8)
        if cfg['cookies']:
            for c in cfg['cookies'].split(";"):
                parts=c.strip().split("=",1)
                if len(parts)==2:
                    try: driver.add_cookie({'name':parts[0],'value':parts[1],'domain':'.facebook.com'})
                    except: pass
        url = f"https://www.facebook.com/messages/t/{cfg['chat_id']}" if cfg['chat_id'] else "https://www.facebook.com/messages"
        driver.get(url)
        time.sleep(10)
        msgs = [m.strip() for m in cfg['messages'].splitlines() if m.strip()]
        if not msgs: msgs=["Hello!"]
        delay=int(cfg['delay'])
        while state.running:
            msg = msgs[state.message_rotation_index % len(msgs)]
            state.message_rotation_index+=1
            try:
                el = driver.find_element(By.CSS_SELECTOR,'div[contenteditable="true"][role="textbox"]')
                el.send_keys(f"{cfg['name_prefix']} {msg}" if cfg['name_prefix'] else msg)
                el.send_keys(u'\ue007') # Enter
                state.message_count+=1
                log(f"Sent {state.message_count}: {msg[:40]}...")
                time.sleep(delay)
            except Exception as e:
                log(f"Send error: {e}")
                break
    except Exception as e:
        log(f"Fatal error: {e}")
    finally:
        try: driver.quit()
        except: pass
        state.running=False
        db.set_automation_running(user_id,False)

def start(cfg,uid):
    s=st.session_state.automation_state
    if s.running: return
    s.running=True; s.logs.clear(); s.message_count=0
    db.set_automation_running(uid,True)
    threading.Thread(target=send_messages,args=(cfg,uid),daemon=True).start()

def stop(uid):
    st.session_state.automation_state.running=False
    db.set_automation_running(uid,False)

# ======= UI =======
st.markdown('<div style="text-align:center;"><img src="https://i.postimg.cc/VvB52mwW/In-Shot-20250608-213052061.jpg" width="70"/><h2 style="color:white;">E2EE OFFLINE — Professional Transparent Panel</h2></div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    tab1,tab2=st.tabs(["🔐 Login","✨ Sign Up"])
    with tab1:
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Login",use_container_width=True):
            uid=db.verify_user(u,p)
            if uid:
                st.session_state.logged_in=True
                st.session_state.user_id=uid
                st.success("✅ Logged in!"); st.rerun()
            else: st.error("❌ Invalid credentials")
    with tab2:
        u=st.text_input("New Username")
        p=st.text_input("New Password",type="password")
        c=st.text_input("Confirm Password",type="password")
        if st.button("Create Account",use_container_width=True):
            if p==c and u and p:
                ok,msg=db.create_user(u,p)
                st.success(msg if ok else f"❌ {msg}")
            else: st.error("⚠️ Password mismatch or empty fields.")
else:
    st.sidebar.write(f"👤 **{st.session_state.user_id}**")
    if st.sidebar.button("🚪 Logout",use_container_width=True):
        if st.session_state.automation_state.running: stop(st.session_state.user_id)
        st.session_state.logged_in=False; st.rerun()

    cfg=db.get_user_config(st.session_state.user_id)
    tab1,tab2=st.tabs(["⚙️ Configuration","🚀 Automation"])
    with tab1:
        chat=st.text_input("Chat ID",value=cfg['chat_id'])
        name=st.text_input("Prefix",value=cfg['name_prefix'])
        delay=st.number_input("Delay (sec)",min_value=1,max_value=300,value=cfg['delay'])
        cookies=st.text_area("Facebook Cookies",value="")
        st.write("Upload messages file (.txt or .csv)")
        up=st.file_uploader("Messages file",type=["txt","csv"])
        msgs=cfg['messages']
        if up:
            txt=up.read().decode(errors="ignore")
            msgs="\n".join([x.strip() for x in txt.splitlines() if x.strip()])
            st.text_area("Preview",msgs,height=180)
        if st.button("💾 Save Config",use_container_width=True):
            db.update_user_config(st.session_state.user_id,chat,name,delay,cookies or cfg['cookies'],msgs)
            st.success("✅ Saved!"); st.rerun()
    with tab2:
        st.metric("Messages Sent",st.session_state.automation_state.message_count)
        st.metric("Status","🟢 Running" if st.session_state.automation_state.running else "🔴 Stopped")
        c1,c2=st.columns(2)
        with c1:
            if st.button("▶️ Start",disabled=st.session_state.automation_state.running,use_container_width=True):
                start(db.get_user_config(st.session_state.user_id),st.session_state.user_id); st.rerun()
        with c2:
            if st.button("⏹ Stop",disabled=not st.session_state.automation_state.running,use_container_width=True):
                stop(st.session_state.user_id); st.rerun()
        st.markdown("### Console")
        logs=st.session_state.automation_state.logs
        if logs:
            st.markdown("<div class='console-output'>"+"<br>".join(logs[-50:])+"</div>",unsafe_allow_html=True)
        else:
            st.markdown("<div class='console-output'>Ready...</div>",unsafe_allow_html=True)
        if st.session_state.automation_state.running:
            time.sleep(1); st.rerun()

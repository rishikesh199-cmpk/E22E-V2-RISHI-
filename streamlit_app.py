# ================= STREAMLIT AUTOMATION =================
import streamlit as st
import time
import threading
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
import database as db  # your database module
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

st.set_page_config(page_title="E2EE Automation", page_icon="🔥", layout="wide")

# ---------------- SESSION VARS ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'automation_running' not in st.session_state: st.session_state.automation_running = False
if 'automation_logs' not in st.session_state: st.session_state.automation_logs = []
if 'automation_state_dict' not in st.session_state:
    st.session_state.automation_state_dict = {"running": False, "message_index":0, "count":0}

# ---------------- CSS ----------------
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: #fff;}
.glow-card {
    background: rgba(0,0,0,0.4); border-radius: 20px; padding: 20px; margin-bottom: 15px;
    border: 3px solid; border-image-slice: 1;
    border-image-source: linear-gradient(45deg, #ff00d4, #00eaff, #fffb00, #ff00d4);
    box-shadow: 0 0 20px rgba(0,255,255,0.4), 0 0 30px rgba(255,0,212,0.4);
    animation: glowing 3s linear infinite;
}
@keyframes glowing {
    0% { box-shadow: 0 0 5px #ff00d4, 0 0 10px #00eaff, 0 0 15px #fffb00; }
    50% { box-shadow: 0 0 20px #ff00d4, 0 0 30px #00eaff, 0 0 40px #fffb00; }
    100% { box-shadow: 0 0 5px #ff00d4, 0 0 10px #00eaff, 0 0 15px #fffb00; }
}
.dashboard-logo { width: 80px; border-radius: 50%; margin-bottom: 15px; }
.live-log {
    background: rgba(0,0,0,0.3); border-radius: 15px; padding: 10px; height: 300px;
    overflow-y: auto; font-family: monospace; font-size: 14px; border: 2px solid #00eaff;
    box-shadow: 0 0 10px #00eaff;
}
.stButton>button { background: linear-gradient(45deg,#00eaff,#ff00d4); color:#fff; border:none; border-radius:10px; padding:10px 25px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="glow-card"><h2 style="text-align:center;">⚡ E2EE AUTOMATION</h2></div>', unsafe_allow_html=True)

# ---------------- LOGIN & CREATE USER ----------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["User Login", "Create Account"])

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
st.image("https://i.imgur.com/YourLogo.png", width=80, caption="E2EE Automation")  # replace with your logo

# ---------------- MESSAGE FILE UPLOAD ----------------
st.markdown("### 📂 Upload .txt Messages File")
msg_file = st.file_uploader("Upload messages", type=["txt"])
msgs = []
if msg_file:
    msgs = msg_file.read().decode("utf-8").split("\n")
    st.success("Messages loaded!")

# ---------------- CONFIG ----------------
chat_id = st.text_input("Chat ID")
chat_type = st.radio("Chat Type", ["E2EE", "Regular"])
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

# ---------------- SELENIUM SETUP ----------------
def setup_browser(headless=True):
    chromedriver_path = shutil.which("chromedriver")
    if not chromedriver_path:
        raise Exception("Chromedriver not found in PATH")

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")

    chrome_bin = shutil.which("google-chrome") or shutil.which("chrome")
    if chrome_bin:
        options.binary_location = chrome_bin
    else:
        raise Exception("Google Chrome not found")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver

def find_input(driver, chat_type="E2EE", retries=5, wait=2):
    selectors = ["div[contenteditable='true']","textarea","[role='textbox']"]
    for _ in range(retries):
        for sel in selectors:
            try:
                box = driver.find_element(By.CSS_SELECTOR, sel)
                if box.is_displayed():
                    return box
            except:
                pass
        time.sleep(wait)
    return None

# ---------------- AUTOMATION THREAD ----------------
def send_messages_thread(cfg, stt, logs_ref):
    try:
        driver = setup_browser(headless=True)
    except Exception as e:
        logs_ref.append(f"❌ Browser setup failed: {e}")
        return

    logs_ref.append("🌐 Browser launched")
    driver.get("https://www.facebook.com")
    logs_ref.append("🌐 Navigating to Facebook...")
    time.sleep(8)

    # Load cookies
    for c in (cfg.get('cookies') or "").split(';'):
        if '=' in c:
            n,v = c.split('=',1)
            try: driver.add_cookie({"name": n.strip(), "value": v.strip(), "domain": ".facebook.com", "path": "/"})
            except: pass
    logs_ref.append(f"🌐 Cookies loaded: {len((cfg.get('cookies') or '').split(';'))}")

    chat_url = f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}"
    driver.get(chat_url)
    logs_ref.append(f"🌐 Navigated to chat: {chat_url}")
    time.sleep(8)

    msgs_list = [m for m in (cfg.get('messages') or "").split("\n") if m.strip()]
    if not msgs_list: msgs_list = ["Hello!"]
    logs_ref.append(f"💬 Total messages loaded: {len(msgs_list)}")

    while stt['running']:
        try:
            box = find_input(driver, chat_type=cfg.get('chat_type','E2EE'))
            if not box:
                logs_ref.append("❌ Chat box not found, retrying...")
                time.sleep(5)
                continue

            m = msgs_list[stt['message_index'] % len(msgs_list)]
            stt['message_index'] += 1

            try:
                box.send_keys(m)
                box.send_keys("\n")
                stt['count'] += 1
                logs_ref.append(f"✅ Sent: {m}")
            except StaleElementReferenceException:
                logs_ref.append("⚠️ Stale element, retrying...")
                continue
            except Exception as e:
                logs_ref.append(f"❌ Error sending message: {e}")
                time.sleep(3)
                continue

            time.sleep(int(cfg.get('delay',15)))
        except Exception as e:
            logs_ref.append(f"❌ Unexpected error: {e}")
            time.sleep(5)

    driver.quit()
    logs_ref.append("🛑 Automation stopped")

# ---------------- AUTOMATION CONTROLS ----------------
st.markdown('<div class="glow-card">🚀 Automation Controls</div>', unsafe_allow_html=True)
log_box = st.empty()
col1, col2 = st.columns(2)

if col1.button("▶️ START", disabled=st.session_state.automation_state_dict['running']):
    cfg = db.get_user_config(st.session_state.user_id)
    if not cfg or not cfg.get('chat_id'):
        st.error("Please save Chat ID first.")
    else:
        st.session_state.automation_state_dict['running'] = True
        t = threading.Thread(target=send_messages_thread, args=(cfg, st.session_state.automation_state_dict, st.session_state.automation_logs))
        t.daemon = True
        t.start()

if col2.button("⏹️ STOP", disabled=not st.session_state.automation_state_dict['running']):
    st.session_state.automation_state_dict['running'] = False

# ---------------- LIVE LOGS ----------------
log_box.markdown('<div class="live-log">' + "<br>".join(st.session_state.automation_logs[-50:]) + '</div>', unsafe_allow_html=True)

# ---------------- MESSAGE COUNT ----------------
st.write(f"📤 Total Messages Sent: {st.session_state.automation_state_dict['count']}")

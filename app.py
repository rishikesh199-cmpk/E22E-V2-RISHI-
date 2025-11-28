import streamlit as st
import threading
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db

# ------------------------------------------------------
# PAGE SETTINGS
# ------------------------------------------------------
st.set_page_config(page_title="Automation Panel", page_icon="⚡", layout="wide")

# ------------------------------------------------------
# PREMIUM UI CSS
# ------------------------------------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #dbeafe, #e0f2fe, #f0f9ff);
}
.title {
    font-size:2.4rem;
    font-weight:800;
    text-align:center;
    margin-bottom:20px;
    background: linear-gradient(120deg, #1e3a8a, #0284c7);
    -webkit-background-clip:text;
    color:transparent;
}
.card {
    background: rgba(255,255,255,0.65);
    padding:22px;
    border-radius:16px;
    border:1px solid rgba(255,255,255,0.4);
    box-shadow:0 6px 16px rgba(0,0,0,0.12);
    backdrop-filter: blur(14px);
}
.logbox {
    height:330px;
    background: rgba(15,23,42,0.75);
    border-radius:12px;
    padding:12px;
    overflow:auto;
    font-family: monospace;
    font-size:13px;
    border:1px solid rgba(255,255,255,0.2);
}
.stButton>button {
    background:linear-gradient(135deg,#2563eb,#3b82f6)!important;
    color:#fff!important;
    border-radius:8px!important;
    padding:8px 20px!important;
    font-weight:700!important;
    border:none!important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------
# SESSION STATE INITIALIZATION
# ------------------------------------------------------
# User login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

# Automation state
if "automation_state" not in st.session_state:
    st.session_state.automation_state = type("obj", (), {
        "running": False,
        "message_count": 0,
        "message_rotation_index": 0,
        "logs": []
    })()

# User configuration defaults
if "chat_id" not in st.session_state:
    st.session_state.chat_id = ""
if "delay" not in st.session_state:
    st.session_state.delay = 15
if "cookies" not in st.session_state:
    st.session_state.cookies = ""
if "messages" not in st.session_state:
    st.session_state.messages = ["Hello!"]

# ------------------------------------------------------
# LIVE LOG ENGINE
# ------------------------------------------------------
def log(msg, level="info"):
    color = {
        "info": "#38bdf8",
        "success": "#22c55e",
        "error": "#ef4444",
        "warn": "#eab308",
    }.get(level, "#38bdf8")

    ts = datetime.datetime.now().strftime("%H:%M:%S")
    formatted = f"<span style='color:{color}'>[{ts}] {msg}</span>"

    st.session_state.automation_state.logs.append(formatted)
    if len(st.session_state.automation_state.logs) > 300:
        st.session_state.automation_state.logs = st.session_state.automation_state.logs[-200:]

# ------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Menu")
    if st.session_state.logged_in:
        st.write("Logged in as: **" + str(st.session_state.user_id) + "**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.automation_state.running = False
            st.rerun()
    else:
        st.write("Please Login")

# ------------------------------------------------------
# LOGIN PAGE
# ------------------------------------------------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            uid = db.verify_user(u, p)
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid

                cfg = db.get_user_config(uid)
                st.session_state.chat_id = cfg.get("chat_id", "")
                st.session_state.delay = cfg.get("delay", 15)
                st.session_state.cookies = cfg.get("cookies", "")
                st.session_state.messages = cfg.get("messages", "").split("\n") or ["Hello!"]

                st.rerun()
            else:
                st.error("Wrong credentials")

    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        npc = st.text_input("Confirm Password", type="password")

        if st.button("Create User"):
            if np != npc:
                st.error("Passwords do not match")
            else:
                ok, msg = db.create_user(nu, np)
                if ok:
                    st.success("Account Created!")
                else:
                    st.error(msg)
    st.stop()

# ------------------------------------------------------
# CONFIGURATION UI
# ------------------------------------------------------
st.markdown("<div class='title'>Automation Panel</div>", unsafe_allow_html=True)

st.subheader("🔧 Configuration")

chat_id = st.text_input("Chat ID", value=st.session_state.chat_id)
delay = st.number_input("Delay (seconds)", min_value=1, max_value=999, value=st.session_state.delay)
cookies = st.text_area("Cookies", value=st.session_state.cookies)

msg_file = st.file_uploader("Upload messages (.txt)", type=["txt"])
if msg_file:
    st.session_state.messages = msg_file.read().decode().split("\n") or ["Hello!"]
    st.success("Messages Updated!")

if st.button("Save Config"):
    db.update_user_config(
        st.session_state.user_id,
        chat_id,
        "",
        delay,
        cookies,
        "\n".join(st.session_state.messages),
    )
    st.success("Saved!")

# ------------------------------------------------------
# SELENIUM SETUP
# ------------------------------------------------------
def setup_browser():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opt)

def find_input(driver):
    candidates = [
        "div[contenteditable='true']",
        "textarea",
        "[role='textbox']"
    ]
    for c in candidates:
        try:
            return driver.find_element(By.CSS_SELECTOR, c)
        except:
            pass
    return None

# ------------------------------------------------------
# AUTOMATION THREAD
# ------------------------------------------------------
def automation_thread(cfg):
    stt = st.session_state.automation_state

    try:
        log("Starting Browser...", "info")
        d = setup_browser()
        d.get("https://www.facebook.com")
        time.sleep(5)
        log("Facebook Loaded", "success")

        for c in cfg["cookies"].split(";"):
            if "=" in c:
                n, v = c.split("=", 1)
                try:
                    d.add_cookie({"name": n.strip(), "value": v.strip(), "domain": ".facebook.com"})
                except:
                    log(f"Failed to add cookie: {n}", "warn")

        d.get(f"https://www.facebook.com/messages/t/{cfg['chat_id']}")
        time.sleep(5)
        log("Chat Opened", "success")

        box = find_input(d)
        if not box:
            log("Input box not found", "error")
            stt.running = False
            return

        msgs = [m for m in cfg["messages"].split("\n") if m.strip()] or ["Hello!"]

        log(f"Loaded {len(msgs)} messages", "info")

        while stt.running:
            msg = msgs[stt.message_rotation_index % len(msgs)]
            stt.message_rotation_index += 1

            try:
                box.send_keys(msg)
                box.send_keys("\n")
                stt.message_count += 1
                log(f"Sent: {msg}", "success")
            except Exception as e:
                log(f"Send failed: {e}", "error")

            for _ in range(cfg["delay"]):
                if not stt.running:
                    break
                time.sleep(1)

    except Exception as e:
        log(f"Fatal Error: {e}", "error")

    finally:
        try:
            d.quit()
        except:
            pass
        log("Browser Closed", "info")

# ------------------------------------------------------
# CONTROLS
# ------------------------------------------------------
st.subheader("🚀 Automation Controls")

c1, c2 = st.columns(2)

with c1:
    if st.button("▶ START", disabled=st.session_state.automation_state.running):
        cfg = {
            "chat_id": chat_id,
            "delay": delay,
            "cookies": cookies,
            "messages": "\n".join(st.session_state.messages)
        }
        st.session_state.automation_state.running = True

        t = threading.Thread(target=automation_thread, args=(cfg,), daemon=True)
        t.start()
        log("Automation Started", "success")
        st.success("Running...")

with c2:
    if st.button("⏹ STOP", disabled=not st.session_state.automation_state.running):
        st.session_state.automation_state.running = False
        log("Stopping Automation...", "warn")
        st.success("Stopping...")

# ------------------------------------------------------
# LIVE LOGS
# ------------------------------------------------------
st.subheader("📡 LIVE CONSOLE LOGS")
st.write("Messages Sent:", st.session_state.automation_state.message_count)

html = "<div class='logbox'>"
for entry in st.session_state.automation_state.logs[-150:]:
    html += entry + "<br>"
html += "</div>"

st.markdown(html, unsafe_allow_html=True)

st.markdown("""
<script>
var box = window.parent.document.querySelector('.logbox');
if(box){ box.scrollTop = box.scrollHeight; }
</script>
""", unsafe_allow_html=True)

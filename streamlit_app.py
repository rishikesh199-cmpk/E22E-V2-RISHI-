import streamlit as st
import time
import threading
from datetime import datetime
from database import users_col, logs_col, state_col, convos_col
from selenium_helpers import create_chrome_driver, load_cookies, open_chat, send_text

# ---------------------- STREAMLIT CONFIG -----------------------
st.set_page_config(
    page_title="DEVIL AUTOMATION PANEL",
    page_icon="⚡",
    layout="wide"
)

# ---------------------- CSS UI (AURA NEON) ----------------------
st.markdown("""
<style>
html, body {
    background: radial-gradient(circle at center, #071018, #000000);
}
.title {
    font-size: 40px;
    text-align:center;
    color: #86f5ff;
    text-shadow: 0 0 20px #00eaff, 0 0 40px #00eaff;
    font-weight: 700;
}
.card {
    padding: 20px;
    background: rgba(0,0,0,0.45);
    border-radius: 20px;
    border: 1px solid #0d4f55;
    box-shadow: 0 0 25px rgba(0,255,255,0.25);
}
.loader {
  display:inline-block;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
 100% { transform: rotate(360deg); }
}
</style>
""", unsafe_allow_html=True)

# ---------------------- SESSION AUTH STATE ----------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login_user(name, pwd):
    u = users_col.find_one({"username": name, "password": pwd})
    if u:
        st.session_state.user = name
        return True
    return False

def logout_user():
    st.session_state.user = None


# ---------------------- LOGIN SCREEN ----------------------
if not st.session_state.user:
    st.markdown("<h1 class='title'>🔐 LOGIN</h1>", unsafe_allow_html=True)

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if login_user(u, p):
            st.rerun()
        else:
            st.error("Wrong credentials")
    st.stop()


# ---------------------- SIDEBAR ----------------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user}")
    st.markdown("### ⏳ Timer: **10 Hours**")

    if st.button("Logout"):
        logout_user()
        st.rerun()


# ---------------------- LOAD OR RESTORE AUTOMATION STATE ----------------------
if "running" not in st.session_state:
    rec = state_col.find_one({"user": st.session_state.user})
    st.session_state.running = rec["running"] if rec else False


def save_state():
    state_col.update_one(
        {"user": st.session_state.user},
        {"$set": {"running": st.session_state.running}},
        upsert=True
    )


# ---------------------- LOGGING ----------------------
def push_log(msg):
    logs_col.insert_one({
        "user": st.session_state.user,
        "time": datetime.now(),
        "msg": msg
    })


def fetch_logs(limit=60):
    return list(logs_col.find({"user": st.session_state.user}).sort("time", -1).limit(limit))[::-1]


# ---------------------- AUTOMATION SEND THREAD ----------------------
def automation_thread():
    push_log("Automation started")

    # GET CONVERSATIONS FOR USER
    convos = list(convos_col.find({"user": st.session_state.user}))

    drivers = {}

    # Setup each convo driver
    for c in convos:
        chat_id = c["chat_id"]
        cookies = c.get("cookies", "")
        messages = c.get("messages", "").split("\n")

        d = create_chrome_driver(headless=True)
        drivers[chat_id] = (d, messages)

        d.get("https://www.facebook.com")
        time.sleep(3)
        load_cookies(d, cookies)
        d.get("https://www.facebook.com")
        time.sleep(2)

    # MAIN LOOP
    while st.session_state.running:
        for c in convos:
            chat_id = c["chat_id"]
            d, msgs = drivers[chat_id]

            elem = open_chat(d, chat_id)
            if not elem:
                push_log(f"❌ Input not found for {chat_id}")
                continue

            for m in msgs:
                if not st.session_state.running:
                    break
                if send_text(elem, m):
                    push_log(f"📨 Sent → {m}")
                time.sleep(1.5)

        time.sleep(3)

    for d, _ in drivers.values():
        try: d.quit()
        except: pass

    push_log("Automation stopped")


# ---------------------- HEADER ----------------------
st.markdown("<h1 class='title'>⚡ DEVIL AUTOMATION DASHBOARD ⚡</h1>", unsafe_allow_html=True)


# ---------------------- CONTROL SECTION ----------------------
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        if st.button("▶️ START AUTOMATION"):
            st.session_state.running = True
            save_state()
            threading.Thread(target=automation_thread, daemon=True).start()
            st.rerun()

    with c2:
        if st.button("⛔ STOP AUTOMATION"):
            st.session_state.running = False
            save_state()
            st.rerun()

    # RUNNING ICON
    if st.session_state.running:
        st.markdown("### 🟢 Running <span class='loader'>⚙️</span>", unsafe_allow_html=True)
    else:
        st.markdown("### 🔴 Stopped")

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------- LIVE LOGS ----------------------
st.markdown("<h2 class='title' style='font-size:28px;'>📡 LIVE LOGS</h2>", unsafe_allow_html=True)

logs_box = st.empty()

while True:
    data = fetch_logs()
    formatted = "\n".join([f"[{str(x['time'])[11:19]}] {x['msg']}" for x in data])
    logs_box.text(formatted)

    if not st.session_state.running:
        break

    time.sleep(1)

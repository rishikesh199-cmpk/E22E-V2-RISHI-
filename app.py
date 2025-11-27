import streamlit as st
import time, threading, os, sys, json, sqlite3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# =========================================================
#  TRANSPARENT GLASS UI + STYLES
# =========================================================

st.set_page_config(
    page_title="⚡ E2EE Auto Messenger",
    page_icon="💎",
    layout="wide"
)

GLASS_UI = """
<style>
body {
    background: url('https://images.unsplash.com/photo-1527192491265-7e15c55b1ed2?auto=format&fit=crop&w=1350&q=80') no-repeat center center fixed;
    background-size: cover;
    font-family: 'Poppins', sans-serif;
}
.block-container {
    background: rgba(255,255,255,0.10) !important;
    backdrop-filter: blur(22px);
    border-radius: 20px;
    padding: 25px 40px;
    border: 1px solid rgba(255,255,255,0.25);
    box-shadow: 0 0 25px rgba(0,0,0,0.4);
}
.card {
    background: rgba(255,255,255,0.08);
    padding: 20px;
    border-radius: 16px;
    backdrop-filter: blur(18px);
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 0 18px rgba(0,0,0,0.25);
}
h1, h2, h3, h4, h5 {
    color: white !important;
    text-shadow: 0 0 10px black;
}
label, span {
    color: white !important;
}
.stTextInput>div>div>input,
.stTextArea textarea,
.stNumberInput input {
    background: rgba(255,255,255,0.15) !important;
    color: white !important;
}
.stButton>button {
    background: linear-gradient(135deg, #7f00ff, #e100ff);
    border-radius: 10px;
    padding: 10px 20px;
    border: none;
    color: white;
    box-shadow: 0 0 12px rgba(255,0,255,0.4);
}
.stButton>button:hover {
    transform: scale(1.03);
}
.console {
    background: black;
    padding: 15px;
    border-radius: 10px;
    color: #00ff88;
    font-family: monospace;
    height: 300px;
    overflow-y: scroll;
}
</style>
"""

st.markdown(GLASS_UI, unsafe_allow_html=True)

# =========================================================
#  DATABASE (auto resume + running state)
# =========================================================

DB = "automation.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS automation_state (
            user_id INTEGER PRIMARY KEY,
            is_running INTEGER DEFAULT 0,
            last_config TEXT,
            updated_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_state(user_id, config):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO automation_state (user_id, is_running, last_config, updated_at)
        VALUES (?, 1, ?, datetime('now'))
    """, (user_id, json.dumps(config)))
    conn.commit()
    conn.close()

def stop_state(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE automation_state SET is_running=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def load_running():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT user_id, last_config FROM automation_state WHERE is_running=1")
    rows = c.fetchall()
    conn.close()
    return rows

init_db()

# =========================================================
#  AUTO REBOOT SYSTEM (Every 6 hours)
# =========================================================

def auto_reboot_loop():
    while True:
        time.sleep(21600)  # 6 hours
        os.execv(sys.executable, ['python'] + sys.argv)

threading.Thread(target=auto_reboot_loop, daemon=True).start()

# =========================================================
# SESSION STATES
# =========================================================

if "automation" not in st.session_state:
    class AutoState:
        running = False
        logs = []
        msg_index = 0
        msg_count = 0
    st.session_state.automation = AutoState()

if "uploaded_messages" not in st.session_state:
    st.session_state.uploaded_messages = []

# =========================================================
# LOG HELPER
# =========================================================

def log(msg):
    ts = time.strftime("%H:%M:%S")
    st.session_state.automation.logs.append(f"[{ts}] {msg}")

# =========================================================
# HEADER
# =========================================================

st.markdown("<h1 align='center'>💎 E2EE Auto Messenger Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<h3 align='center'>Transparent Glass Premium UI</h3>", unsafe_allow_html=True)
# =========================================================
# BROWSER SETUP
# =========================================================

def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(options=chrome_options)

# =========================================================
# FIND MESSAGE BOX
# =========================================================

def find_box(driver):
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"]',
        'textarea',
        'input[type="text"]'
    ]
    for s in selectors:
        try:
            el = driver.find_elements(By.CSS_SELECTOR, s)
            if el:
                return el[0]
        except:
            pass
    return None

# =========================================================
# MAIN AUTOMATION ENGINE
# =========================================================

def next_msg(msgs):
    ai = st.session_state.automation
    val = msgs[ai.msg_index % len(msgs)]
    ai.msg_index += 1
    return val

def automation_thread(config, mode):
    ai = st.session_state.automation
    ai.running = True
    ai.logs = []
    ai.msg_count = 0

    save_state(config["user_id"], config)

    driver = setup_browser()
    log("Browser launched")

    driver.get("https://facebook.com")
    time.sleep(5)

    # COOKIES
    if config["cookies"].strip():
        for ck in config["cookies"].split(";"):
            if "=" in ck:
                n, v = ck.split("=",1)
                try:
                    driver.add_cookie({"name":n.strip(),"value":v.strip(),"domain":".facebook.com"})
                except:
                    pass

    # URL decide
    chat = config["chat_id"]

    if mode == "Auto":
        if "e2ee" in chat:
            url = f"https://www.facebook.com/messages/e2ee/t/{chat.replace('e2ee/','')}"
        else:
            url = f"https://www.facebook.com/messages/t/{chat}"
    elif mode == "E2EE":
        url = f"https://www.facebook.com/messages/e2ee/t/{chat}"
    else:
        url = f"https://www.facebook.com/messages/t/{chat}?normal=true"

    log("Opening chat: " + url)
    driver.get(url)
    time.sleep(8)

    box = find_box(driver)
    if not box:
        log("❌ Message box not found!")
        ai.running = False
        stop_state(config["user_id"])
        return

    # MESSAGE SOURCE
    msgs = st.session_state.uploaded_messages if st.session_state.use_uploaded else \
           [m for m in config["messages"].split("\n") if m.strip()]

    if not msgs:
        msgs = ["Hello!"]

    delay = int(config["delay"])

    # LOOP
    while ai.running:
        msg = next_msg(msgs)

        if config["prefix"]:
            msg = config["prefix"] + " " + msg

        try:
            driver.execute_script("""
                arguments[0].focus();
                arguments[0].innerText = arguments[1];
                arguments[0].dispatchEvent(new Event('input',{bubbles:true}));
            """, box, msg)

            time.sleep(1)

            driver.execute_script("""
                document.dispatchEvent(new KeyboardEvent('keydown',{
                    key:'Enter', keyCode:13, which:13, bubbles:true
                }));
            """)

            ai.msg_count += 1
            log(f"Sent #{ai.msg_count}: {msg[:40]}")

        except Exception as e:
            log("Error: " + str(e))
            break

        time.sleep(delay)

    driver.quit()
    log("Browser closed")
    stop_state(config["user_id"])
    ai.running = False

# =========================================================
# AUTO-RESUME AFTER REBOOT
# =========================================================

def auto_resume():
    rows = load_running()
    for user_id, cfg_json in rows:
        cfg = json.loads(cfg_json)
        cfg["user_id"] = user_id
        threading.Thread(target=automation_thread, args=(cfg,"Auto"), daemon=True).start()

auto_resume()

# =========================================================
# UI PANELS
# =========================================================

tab1, tab2 = st.tabs(["⚙️ Settings", "🚀 Automation"])

# ========== SETTINGS PANEL ==========

with tab1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Configuration")

    user_id = st.number_input("User ID", min_value=1, value=1)
    chat_id = st.text_input("Chat ID")
    prefix = st.text_input("Prefix (optional)")
    delay = st.number_input("Delay (seconds)", min_value=1, value=5)
    cookies = st.text_area("Facebook Cookies (optional)")
    messages = st.text_area("Messages (one per line)")

    mode = st.selectbox("Send Mode", ["Auto", "E2EE", "Normal"])

    st.write("### Upload Messages File")
    up = st.file_uploader("Upload .txt or .csv", type=["txt","csv"])

    if up:
        text = up.getvalue().decode("utf-8")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        st.session_state.uploaded_messages = lines
        st.success(f"Loaded {len(lines)} messages")

    st.checkbox("Use Uploaded Messages", key="use_uploaded")

    manual = st.text_input("Add manual message")
    if manual:
        st.session_state.uploaded_messages.append(manual)
        st.success("Added!")

    st.markdown("</div>", unsafe_allow_html=True)

# ========== AUTOMATION PANEL ==========

with tab2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    ai = st.session_state.automation

    st.metric("Messages Sent", ai.msg_count)
    st.metric("Status", "Running" if ai.running else "Stopped")

    cfg = {
        "user_id": user_id,
        "chat_id": chat_id,
        "prefix": prefix,
        "delay": delay,
        "cookies": cookies,
        "messages": messages
    }

    c1, c2 = st.columns(2)

    if c1.button("START", disabled=ai.running):
        threading.Thread(target=automation_thread, args=(cfg, mode), daemon=True).start()
        time.sleep(0.5)
        st.experimental_rerun()

    if c2.button("STOP", disabled=not ai.running):
        ai.running = False
        stop_state(user_id)

    st.write("### Console Log")
    st.markdown("<div class='console'>", unsafe_allow_html=True)
    for line in ai.logs[-80:]:
        st.write(line)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

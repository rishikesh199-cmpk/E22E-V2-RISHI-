import streamlit as st
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import database as db

st.set_page_config(page_title="Automation Panel", page_icon="⚡", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
.stApp { background:#f5f7fa; }

.title { 
    font-size:2.2rem; 
    font-weight:700; 
    text-align:center; 
    margin-bottom:15px; 
    color:#222; 
}

.card { 
    background:#fff; 
    padding:20px; 
    border:1px solid #e5e7eb; 
    border-radius:12px;
    box-shadow:0px 6px 18px rgba(0,0,0,0.15); 
}

.logbox { 
    background:#0d1117; 
    color:#10b981; 
    height:320px; 
    padding:12px; 
    border-radius:10px; 
    overflow:auto; 
    font-size:13px; 
    font-family:monospace; 
}

.stButton>button { 
    background:#2563eb !important; 
    color:#fff !important; 
    border-radius:6px; 
    padding:8px 18px; 
    font-weight:600; 
}

input, textarea { 
    border-radius:8px !important; 
}
</style>
""", unsafe_allow_html=True)
# ---------- Session ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type("obj", (), {
        "running": False,
        "message_count": 0,
        "message_rotation_index": 0,
        "logs": []
    })()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Menu")
    if st.session_state.logged_in:
        st.write("Logged in as: **" + str(st.session_state.user_id) + "**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.automation_state.running = False
            st.session_state.automation_running = False
            st.rerun()
    else:
        st.write("Please login.")

# ---------- Login Page ----------
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
                st.session_state.chat_type = cfg.get("chat_type", "E2EE")
                st.session_state.delay = cfg.get("delay", 15)
                st.session_state.cookies = cfg.get("cookies", "")
                st.session_state.messages = cfg.get("messages", "").split("\n")

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
                ok, msg = db.create_user(nu, np)
                if ok:
                    st.success("Account created!")
                else:
                    st.error(msg)
    st.stop()

# ---------- MAIN DASHBOARD ----------
st.subheader("🔧 Configuration")

chat_id = st.text_input("Chat ID", value=getattr(st.session_state, "chat_id", ""))
chat_type = st.selectbox("Chat Type", ["E2EE", "Non-E2EE"], index=0 if st.session_state.chat_type == "E2EE" else 1)
delay = st.number_input("Delay (seconds)", min_value=1, max_value=600, value=st.session_state.delay)
cookies = st.text_area("Cookies", value=st.session_state.cookies)

msg_file = st.file_uploader("Upload .txt messages", type=["txt"])
if msg_file:
    st.session_state.messages = msg_file.read().decode().split("\n")
    st.success("Messages loaded!")

if st.button("Save Config"):
    db.update_user_config(
        st.session_state.user_id,
        chat_id,
        chat_type,
        delay,
        cookies,
        "\n".join(st.session_state.messages),
        running=st.session_state.automation_running
    )
    st.success("Saved!")

# ---------- Browser Setup ----------
def setup_browser():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opt)

def find_input(driver, chat_type):
    selectors = ["div[contenteditable='true']"] if chat_type == "E2EE" else [
        "div[contenteditable='true']",
        "textarea",
        "[role='textbox']"
    ]
    for s in selectors:
        try:
            return driver.find_element(By.CSS_SELECTOR, s)
        except:
            pass
    return None

# ---------- FULLY FIXED AUTOMATION THREAD ----------
def send_messages(cfg, stt):
    try:
        stt.logs.append("[INFO] Starting browser...")

        d = setup_browser()
        d.get("https://www.facebook.com")
        time.sleep(6)

        stt.logs.append("[INFO] Facebook opened")

        # Load cookies
        for c in (cfg.get("cookies") or "").split(";"):
            if "=" in c:
                n, v = c.split("=", 1)
                try:
                    d.add_cookie({"name": n.strip(), "value": v.strip(),
                                  "domain": ".facebook.com", "path": "/"})
                except Exception as e:
                    stt.logs.append(f"[WARN] Cookie failed: {n} -> {e}")

        # Open chat
        chat_url = f"https://www.facebook.com/messages/t/{cfg.get('chat_id', '')}"
        d.get(chat_url)
        time.sleep(6)

        stt.logs.append(f"[INFO] Chat opened: {chat_url}")

        box = find_input(d, cfg.get("chat_type", "E2EE"))
        if not box:
            stt.logs.append("[ERROR] Input box not found")
            stt.running = False
            return

        # Messages list
        msgs = [m.strip() for m in (cfg.get("messages") or "").split("\n") if m.strip()]
        if not msgs:
            msgs = ["Hello!"]

        stt.logs.append(f"[INFO] Loaded {len(msgs)} messages")

        while stt.running:
            msg = msgs[stt.message_rotation_index % len(msgs)]
            stt.message_rotation_index += 1

            try:
                box.send_keys(msg)
                box.send_keys("\n")
                stt.message_count += 1
                stt.logs.append(f"[SENT #{stt.message_count}] {msg}")
            except Exception as e:
                stt.logs.append(f"[ERROR] Send failed: {e}")

            # breakable delay
            for _ in range(int(cfg.get("delay", 15))):
                if not stt.running:
                    break
                time.sleep(1)

    except Exception as e:
        stt.logs.append(f"[FATAL] Automation crashed: {e}")

    finally:
        try:
            d.quit()
        except:
            pass
        stt.logs.append("[INFO] Browser closed")

# ---------- Automation Controls ----------
st.subheader("🚀 Automation Control")

c1, c2 = st.columns(2)

with c1:
    if st.button("▶️ Start", disabled=st.session_state.automation_running):
        cfg = {
            "chat_id": chat_id,
            "chat_type": chat_type,
            "delay": delay,
            "cookies": cookies,
            "messages": "\n".join(st.session_state.messages)
        }
        st.session_state.automation_running = True
        st.session_state.automation_state.running = True

        t = threading.Thread(
            target=send_messages,
            args=(cfg, st.session_state.automation_state),
            daemon=True
        )
        t.start()
        st.success("Automation Started")

with c2:
    if st.button("⏹ Stop", disabled=not st.session_state.automation_running):
        st.session_state.automation_state.running = False
        st.session_state.automation_running = False
        st.success("Stopping...")

# ---------- Live Logs ----------
st.subheader("📡 Live Logs")
st.write("Messages Sent:", st.session_state.automation_state.message_count)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="logbox">', unsafe_allow_html=True)

for log in st.session_state.automation_state.logs[-200:]:
    safe = str(log).replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(safe)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

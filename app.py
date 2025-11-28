# streamlit_app.py
# Clean Professional Dashboard (background removed, sidebar logout, nonstop live logs, start/stop controls)
import streamlit as st
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import database as db  # Ensure your database module provides required functions

st.set_page_config(page_title="Automation", page_icon="🔥", layout="wide")

# ---------------- CSS (clean professional) ----------------
st.markdown("""
<style>
.stApp { background: #f5f7fa !important; }

.title { font-size: 2.2rem; font-weight:700; text-align:center; margin-bottom:12px; color:#111827; }

.card { background:#fff; border-radius:12px; padding:18px; border:1px solid #e6e6e6; box-shadow:0 6px 18px rgba(15,23,42,0.06); }

input, textarea { background:#fff !important; border-radius:8px !important; }

.stButton>button { background:#2563eb !important; color:#fff !important; padding:8px 18px !important; border-radius:8px !important; font-weight:600 !important; }

.logbox { background:#0b1220; color:#10b981; padding:14px; height:320px; overflow:auto; border-radius:10px; font-family:monospace; font-size:13px; }
.small-muted { color:#6b7280; font-size:13px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">FB Automation Panel</div>', unsafe_allow_html=True)

# ---------------- Session state defaults ----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type('obj', (), {
        "running": False,
        "message_count": 0,
        "message_rotation_index": 0,
        "logs": []
    })()

# ---------------- Sidebar (menu + logout) ----------------
with st.sidebar:
    st.header("⚙️ Menu")
    if st.session_state.logged_in:
        st.write(f"Logged in as: **{st.session_state.get('user_id','')}**")
        if st.button("🚪 Logout"):
            # clear relevant session values
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.automation_running = False
            st.session_state.automation_state.running = False
            # optionally save config on logout
            st.experimental_rerun()
    else:
        st.write("Please login to access dashboard")
    st.markdown("---")
    st.markdown("<div class='small-muted'>Tip: Upload a .txt with one message per line for rotation.</div>", unsafe_allow_html=True)

# ---------------- Login / Create account ----------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Create Account"])
    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                uid = db.verify_user(u, p)
            except Exception as e:
                st.error(f"DB error: {e}")
                st.stop()
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                cfg = db.get_user_config(uid) or {}
                st.session_state.chat_id = cfg.get('chat_id', '')
                st.session_state.chat_type = cfg.get('chat_type', 'E2EE')
                st.session_state.delay = cfg.get('delay', 15)
                st.session_state.cookies = cfg.get('cookies', '')
                st.session_state.messages = cfg.get('messages', '').split("\n") if cfg.get('messages') else []
                # restore running flag if stored (optional)
                if cfg.get('running', False):
                    st.session_state.automation_state.running = True
                    st.session_state.automation_running = True
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        nu = st.text_input("New Username", key="new_user")
        np = st.text_input("New Password", type="password", key="new_pass")
        npc = st.text_input("Confirm Password", type="password", key="new_pass_c")
        if st.button("Create User"):
            if np != npc:
                st.error("Passwords do not match")
            else:
                ok, msg = db.create_user(nu, np)
                if ok:
                    st.success("User created! You can login now.")
                else:
                    st.error(msg)
    st.stop()

# ---------------- Main dashboard content ----------------
st.subheader("🔧 Configuration")
colA, colB = st.columns([2,1])
with colA:
    chat_id = st.text_input("Chat ID", value=getattr(st.session_state, 'chat_id', ''))
    chat_type = st.selectbox("Chat Type", ["E2EE", "Non-E2EE"], index=0 if getattr(st.session_state, 'chat_type', 'E2EE') == 'E2EE' else 1)
    delay = st.number_input("Delay (seconds)", min_value=1, max_value=3600, value=getattr(st.session_state, 'delay', 15))
    cookies = st.text_area("Cookies (name=value; separate with ; )", value=getattr(st.session_state, 'cookies', ''))
with colB:
    msg_file = st.file_uploader("Upload .txt Messages", type=["txt"])
    if msg_file:
        try:
            content = msg_file.read().decode("utf-8")
        except:
            content = msg_file.read().decode(errors='ignore')
        st.session_state.messages = [ln for ln in content.splitlines() if ln.strip()]
        st.success(f"{len(st.session_state.messages)} messages loaded")
    st.markdown("**Current message count:** " + str(len(getattr(st.session_state, 'messages', []))))

if st.button("Save Config"):
    try:
        db.update_user_config(st.session_state.user_id, chat_id, chat_type, delay, cookies, "\n".join(st.session_state.messages), running=st.session_state.automation_running)
        # keep local session values too
        st.session_state.chat_id = chat_id
        st.session_state.chat_type = chat_type
        st.session_state.delay = delay
        st.session_state.cookies = cookies
        st.success("Saved!")
    except Exception as e:
        st.error(f"Save failed: {e}")

# ---------------- Browser automation helpers ----------------
def setup_browser():
    opt = Options()
    opt.add_argument('--headless=new')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    # add any additional options needed for your environment
    return webdriver.Chrome(options=opt)

def find_input(driver, chat_type):
    selectors = ["div[contenteditable='true']"] if chat_type == "E2EE" else ["div[contenteditable='true']", "textarea", "[role='textbox']"]
    for s in selectors:
        try:
            return driver.find_element(By.CSS_SELECTOR, s)
        except Exception:
            pass
    return None

def send_messages(cfg, stt):
    # NOTE: this runs in a background thread; avoid Streamlit calls here (we append to stt.logs only)
    stt.logs.append("[INFO] Starting browser...")
    try:
        d = setup_browser()
        d.get("https://www.facebook.com")
        time.sleep(6)
        stt.logs.append("[INFO] Facebook opened")
        # set cookies if provided
        cookie_str = cfg.get('cookies') or ""
        for c in cookie_str.split(";"):
            if "=" in c:
                n, v = c.split("=", 1)
                try:
                    d.add_cookie({"name": n.strip(), "value": v.strip(), "domain": ".facebook.com", "path": "/"})
                except Exception as e:
                    stt.logs.append(f"[WARN] Cookie add failed: {n.strip()} -> {e}")
        # go to chat
        d.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
        time.sleep(8)
        stt.logs.append(f"[INFO] Opened chat {cfg.get('chat_id','')}")
        box = find_input(d, cfg.get('chat_type', 'E2EE'))
        if not box:
            stt.logs.append("[ERROR] Input box not found. Stopping automation.")
            stt.running = False
            return
        msgs = [m for m in (cfg.get('messages') or "").split("\n") if m.strip()]
        if not msgs:
            msgs = ["Hello!"]
        while stt.running:
            m = msgs[stt.message_rotation_index % len(msgs)]
            stt.message_rotation_index += 1
            try:
                box.send_keys(m)
                box.send_keys("\n")
                stt.message_count += 1
                stt.logs.append(f"[SENT #{stt.message_count}] {m}")
            except Exception as e:
                stt.logs.append(f"[ERROR] Send failed: {e}")
            # sleep but check running flag in smaller intervals for responsive stop
            total_sleep = int(cfg.get('delay', 15))
            for _ in range(total_sleep):
                if not stt.running:
                    break
                time.sleep(1)
        try:
            d.quit()
        except:
            pass
        stt.logs.append("[INFO] Automation stopped")
    except Exception as e:
        stt.logs.append(f"[FATAL] Exception in automation: {e}")
        stt.running = False

# ---------------- Automation controls (start/stop) ----------------
st.subheader("🚀 Automation Control")
c1, c2, c3 = st.columns([1,1,1])
with c1:
    if st.button("▶️ START", disabled=st.session_state.automation_running):
        cfg = {
            'chat_id': chat_id,
            'chat_type': chat_type,
            'delay': delay,
            'cookies': cookies,
            'messages': "\n".join(getattr(st.session_state, 'messages', []))
        }
        # set flags
        st.session_state.automation_state.running = True
        st.session_state.automation_running = True
        # start background thread
        t = threading.Thread(target=send_messages, args=(cfg, st.session_state.automation_state), daemon=True)
        t.start()
        st.success("Automation started")
with c2:
    if st.button("⏹️ STOP", disabled=not st.session_state.automation_running):
        st.session_state.automation_state.running = False
        st.session_state.automation_running = False
        st.success("Stopping automation...")
with c3:
    if st.button("💾 Save & Persist (current state)"):
        try:
            db.update_user_config(st.session_state.user_id, chat_id, chat_type, delay, cookies, "\n".join(getattr(st.session_state, 'messages', [])), running=st.session_state.automation_running)
            st.success("Saved to DB.")
        except Exception as e:
            st.error(f"Save failed: {e}")

# ---------------- Live logs ----------------
st.subheader("📡 Live Logs & Messages Sent")
st.write(f"Messages Sent: **{st.session_state.automation_state.message_count}**")

# Display logs inside a div so copy works reliably
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="logbox">', unsafe_allow_html=True)
# show last 200 logs for context
for log in st.session_state.automation_state.logs[-200:]:
    # escape/format basic html
    safe = str(log).replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(f"{safe}")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Optional: auto-save config periodically (every 10 hours) ----------------
def auto_save_periodically():
    while True:
        time.sleep(36000)  # 10 hours
        try:
            db.update_user_config(
                st.session_state.user_id,
                getattr(st.session_state, 'chat_id', ''),
                getattr(st.session_state, 'chat_type', 'E2EE'),
                getattr(st.session_state, 'delay', 15),
                getattr(st.session_state, 'cookies', ''),
                "\n".join(getattr(st.session_state, 'messages', [])),
                running=st.session_state.automation_running
            )
        except Exception:
            pass

# start background auto-save thread once
if not st.session_state.get("_autosave_thread_started", False):
    t_as = threading.Thread(target=auto_save_periodically, daemon=True)
    t_as.start()
    st.session_state._autosave_thread_started = True

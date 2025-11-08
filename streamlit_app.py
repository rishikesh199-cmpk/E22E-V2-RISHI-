# streamlit_app.py
import streamlit as st
import time
import threading
from pathlib import Path
import database as db
import os

st.set_page_config(page_title="OFFLINE💋PY", page_icon="🏴‍☠️", layout="wide")

# ---------- CSS: Professional Transparent Blue Theme ----------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

.stApp {
  background-image: url('https://i.postimg.cc/L51fQrQH/681be2a77443fb2f2f74fd42da1bc40f.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

/* Main container glass */
.main .block-container {
  background: rgba(12,16,20,0.50);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 14px;
  padding: 22px;
  border: 1px solid rgba(255,255,255,0.04);
  box-shadow: 0 10px 30px rgba(14,165,233,0.06);
}

/* Header */
.header {
  display:flex;
  gap:16px;
  align-items:center;
  margin-bottom: 12px;
}
.header img { width:72px; height:72px; border-radius:12px; border:1px solid rgba(255,255,255,0.04); box-shadow:0 8px 20px rgba(14,165,233,0.04); }
.header h1 { margin:0; color: #FFFFFF; font-size:1.5rem; font-weight:700; }
.header p { margin:0; color: rgba(255,255,255,0.75); font-size:0.95rem; }

/* Buttons */
.stButton>button {
  background: linear-gradient(90deg, rgba(14,165,233,1), rgba(56,189,248,1));
  color: white;
  border-radius: 10px;
  padding: 8px 14px;
  font-weight: 700;
  border: none;
  box-shadow: 0 10px 30px rgba(14,165,233,0.08);
  transition: transform .16s ease, box-shadow .16s;
}
.stButton>button:hover { transform: translateY(-3px); box-shadow: 0 18px 40px rgba(14,165,233,0.12); }

/* Inputs */
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.04) !important;
  color: #fff !important;
  border-radius: 8px !important;
  padding: 10px !important;
}

/* Console */
.console {
  background: rgba(2,6,10,0.45);
  border-radius: 10px;
  padding: 12px;
  color: #9ef;
  font-family: monospace;
  font-size: 13px;
  max-height: 420px;
  overflow-y: auto;
  border: 1px solid rgba(255,255,255,0.02);
}

/* Metric cards */
.metric {
  background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.005));
  border-radius: 10px;
  padding: 10px;
  border: 1px solid rgba(255,255,255,0.03);
}
.metric .value { font-size: 1.5rem; font-weight:800; color: rgb(56,189,248); }
.metric .label { color: rgba(255,255,255,0.8); font-weight:600; font-size:0.9rem; }

.footer { text-align:center; color: rgba(255,255,255,0.6); padding-top:10px; font-weight:600; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- Session defaults ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'automation' not in st.session_state:
    class _A:
        running = False
        logs = []
        sent_count = 0
        index = 0
    st.session_state.automation = _A()

# ---------- Helpers ----------
def add_log(line: str):
    ts = time.strftime("%H:%M:%S")
    st.session_state.automation.logs.append(f"[{ts}] {line}")

# ---------- Safe background "task" (simulation) ----------
def worker_task(config, user_id):
    """
    SAFE placeholder task that simulates sending messages.
    Replace the body of this function with any allowed logic.
    Do NOT add automation of third-party platforms here.
    """
    add_log("Worker started (simulation).")
    messages = [m.strip() for m in config.get('messages', '').splitlines() if m.strip()]
    if not messages:
        messages = ["Hello from simulator!"]

    delay = int(config.get('delay', 5))
    st.session_state.automation.sent_count = 0

    try:
        while st.session_state.automation.running:
            idx = st.session_state.automation.index % len(messages)
            message = messages[idx]
            st.session_state.automation.index += 1

            # --- Simulate doing work with the message ---
            add_log(f"Simulated send #{st.session_state.automation.sent_count + 1}: {message[:80]}")
            st.session_state.automation.sent_count += 1

            # Sleep for configured delay
            for i in range(delay):
                if not st.session_state.automation.running:
                    add_log("Worker detected stop signal. Exiting loop.")
                    break
                time.sleep(1)

    except Exception as e:
        add_log(f"Worker error: {e}")
    finally:
        st.session_state.automation.running = False
        db.set_automation_running(user_id, False)
        add_log("Worker stopped.")

# ---------- Start / Stop control ----------
def start_automation(config, user_id):
    if st.session_state.automation.running:
        add_log("Automation already running.")
        return
    st.session_state.automation.running = True
    st.session_state.automation.logs.clear()
    st.session_state.automation.sent_count = 0
    st.session_state.automation.index = 0
    db.set_automation_running(user_id, True)
    t = threading.Thread(target=worker_task, args=(config, user_id), daemon=True)
    t.start()
    add_log("Automation thread started.")

def stop_automation(user_id):
    if not st.session_state.automation.running:
        add_log("Automation not running.")
        return
    st.session_state.automation.running = False
    db.set_automation_running(user_id, False)
    add_log("Stop signal sent to worker.")

# ---------- UI ----------
st.markdown('<div class="header"><img src="https://i.postimg.cc/VvB52mwW/In-Shot-20250608-213052061.jpg" alt="logo"/><div><h1>E2EE OFFLINE</h1><p>Professional Transparent Dashboard — Safe Template</p></div></div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])

    with tab1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True):
            uid = db.verify_user(username, password)
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                add_log(f"User '{username}' logged in.")
                st.success("Logged in successfully.")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        st.subheader("Create new account")
        new_user = st.text_input("New username", key="new_user")
        new_pass = st.text_input("New password", type="password", key="new_pass")
        new_pass_confirm = st.text_input("Confirm password", type="password", key="new_pass_confirm")
        if st.button("Create account", use_container_width=True):
            if new_pass != new_pass_confirm:
                st.error("Passwords do not match.")
            elif not new_user or not new_pass:
                st.warning("Provide username & password.")
            else:
                ok, msg = db.create_user(new_user, new_pass)
                if ok:
                    st.success("Account created — please login.")
                else:
                    st.error(msg)

else:
    # Sidebar user box
    st.sidebar.markdown(f"### 👤 {db.get_username(st.session_state.user_id)}")
    st.sidebar.markdown(f"**User ID:** {st.session_state.user_id}")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if st.session_state.automation.running:
            stop_automation(st.session_state.user_id)
        st.session_state.logged_in = False
        st.rerun()

    # Load user's saved config
    cfg = db.get_user_config(st.session_state.user_id)

    tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Automation"])

    with tab1:
        st.subheader("Your Configuration")
        chat_id = st.text_input("Conversation / Target ID (any label)", value=cfg.get('chat_id', ''), help="This is just a label in the safe template.")
        name_prefix = st.text_input("Prefix (optional)", value=cfg.get('name_prefix', ''))
        delay = st.number_input("Delay (seconds)", min_value=1, max_value=3600, value=int(cfg.get('delay', 5)))
        st.markdown("**Upload messages file (.txt or .csv)** — each line will be treated as one message.")
        uploaded = st.file_uploader("Messages file", type=['txt', 'csv'], help="One message per line", accept_multiple_files=False)

        messages_text = cfg.get('messages', '')
        if uploaded:
            try:
                raw = uploaded.read()
                try:
                    txt = raw.decode('utf-8')
                except:
                    txt = raw.decode('latin-1', errors='ignore')
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                messages_text = "\n".join(lines)
                st.markdown(f"**Preview ({len(lines)} messages)**")
                st.text_area("Preview", value=messages_text, height=200)
            except Exception as e:
                st.error(f"Failed to read file: {e}")

        cookies = st.text_area("Secret / Cookies (optional & encrypted)", placeholder="Optional: encrypted storage for your secrets", value="", height=80)
        if st.button("💾 Save Configuration", use_container_width=True):
            # Save messages_text into DB (if none uploaded, keep old)
            final_messages = messages_text if messages_text.strip() else cfg.get('messages', '')
            final_cookies = cookies.strip() if cookies.strip() else cfg.get('cookies', '')
            db.update_user_config(st.session_state.user_id, chat_id.strip(), name_prefix.strip(), int(delay), final_cookies, final_messages)
            st.success("Configuration saved.")
            add_log("Configuration saved by user.")
            st.rerun()

    with tab2:
        st.subheader("Automation Control")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric"><div class="value">{st.session_state.automation.sent_count}</div><div class="label">Messages Sent (sim)</div></div>', unsafe_allow_html=True)
        with c2:
            status = "🟢 Running" if st.session_state.automation.running else "🔴 Stopped"
            st.markdown(f'<div class="metric"><div class="value">{status}</div><div class="label">Status</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric"><div class="value">{len(st.session_state.automation.logs)}</div><div class="label">Log Lines</div></div>', unsafe_allow_html=True)

        run_col, stop_col = st.columns(2)
        with run_col:
            if st.button("▶️ Start", disabled=st.session_state.automation.running, use_container_width=True):
                cfg_saved = db.get_user_config(st.session_state.user_id)
                start_automation(cfg_saved, st.session_state.user_id)
                st.success("Started (simulation).")
                st.rerun()
        with stop_col:
            if st.button("⏹ Stop", disabled=not st.session_state.automation.running, use_container_width=True):
                stop_automation(st.session_state.user_id)
                st.success("Stop signal sent.")
                st.experimental_rerun()

        st.markdown("### Live Console")
        if st.session_state.automation.logs:
            st.markdown(f'<div class="console">{"<br>".join(st.session_state.automation.logs[-100:])}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="console">Console ready — run the simulation to see logs.</div>', unsafe_allow_html=True)

        if st.session_state.automation.running:
            time.sleep(1)
            st.rerun()

st.markdown('<div class="footer">Professional Transparent Dashboard • Safe Template</div>', unsafe_allow_html=True)

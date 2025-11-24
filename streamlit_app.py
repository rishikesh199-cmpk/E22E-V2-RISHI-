# streamlit_app.py
# Full merged Streamlit + Selenium multi-conversation automation dashboard
# - Aura/neon/glass UI, side slide menu, 10-hour timer, per-conversation auto-reboot & auto-restart
# - Threads do not call Streamlit UI. UI refresh via JS.
# - Requires a working `database` module as described in comments above.

import streamlit as st
import threading, time, traceback, html
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import database as db  # Your DB module (see top comments in assistant message for API)

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="AURA E23E - Multi Convo Automation", page_icon="⚡", layout="wide")

# -------------------------
# Auto refresh (safe): reload every 2500ms when not focusing inputs
# -------------------------
REFRESH_INTERVAL_MS = 2500
st.markdown(f"""
<script>
let reloadInterval = setInterval(() => {{
    // don't reload if user is typing in an input
    try {{
        if (!document.activeElement || document.activeElement.tagName.toLowerCase() === 'body') {{
            window.location.reload();
        }}
    }} catch(e){{}}
}}, {REFRESH_INTERVAL_MS});
</script>
""", unsafe_allow_html=True)

# -------------------------
# Tiny global lock for session_state writes from threads
# -------------------------
_global_lock = threading.Lock()

# -------------------------
# Session defaults
# -------------------------
def s_init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

s_init("logged_in", False)
s_init("user_id", None)
s_init("conversations", {})   # map chat_id -> conv dict (stored in session while running)
s_init("ui_last_update", time.time())
s_init("sidebar_open", True)

# -------------------------
# CSS / AURA / GLASS / 3D / FONTS
# -------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&family=Orbitron:wght@700;900&display=swap');

html, body, [class*="css"] { font-family: 'Montserrat', sans-serif !important; }

/* Background */
body {
    background: radial-gradient(circle at 10% 20%, rgba(0,38,51,0.9), rgba(0,0,0,0.95)), url('https://i.ibb.co/9k1k2c6f/bg.png') no-repeat center center fixed;
    background-size: cover;
}

/* Aura ring */
.aura-ring { position:absolute; width:480px; height:480px; border-radius:50%; top:-120px; left:calc(50% - 240px);
  background: radial-gradient(circle, rgba(0,255,255,0.12), rgba(255,0,255,0.08) 40%, rgba(0,0,0,0) 70%);
  filter: blur(48px); animation: auraPulse 7s infinite ease-in-out; z-index:-1;}
@keyframes auraPulse { 0%{transform:scale(1);opacity:0.7}50%{transform:scale(1.18);opacity:1}100%{transform:scale(1);opacity:0.7} }

/* Title holo */
.holo-title { font-family: 'Orbitron', sans-serif; font-weight:900; font-size:44px; text-align:center;
  background: linear-gradient(90deg,#00eaff,#ff00d4,#8a2be2,#00eaff); -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  background-size:200%; animation: holoFlow 6s linear infinite; text-shadow:0 0 18px rgba(0,255,255,0.18); margin-bottom:6px; }
@keyframes holoFlow { 0%{background-position:0%}50%{background-position:100%}100%{background-position:0%} }

/* Glass card */
.glass-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
    border-radius: 16px;
    padding: 18px;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 10px 35px rgba(0,0,0,0.6);
    backdrop-filter: blur(12px);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    position: relative;
}
.glass-card:hover { transform: perspective(600px) rotateX(3deg) rotateY(-3deg) translateY(-6px); box-shadow: 0 20px 60px rgba(0,0,0,0.7); }

/* Sidebar glass */
.sidebar-glass { padding:12px; border-radius:12px; background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); backdrop-filter: blur(10px); }

/* Buttons */
.stButton>button { background: linear-gradient(90deg,#00eaff,#ff00d4); color:#fff !important; border:none !important;
    padding:10px 14px !important; border-radius:10px !important; font-weight:700 !important; }

/* Log terminal */
.log-terminal { background: rgba(0,0,0,0.58); border-radius:10px; padding:12px; height:300px; overflow-y:auto; border:1px solid rgba(0,255,255,0.08); color:#bff; font-family:monospace; font-size:13px; }

/* rainbow underline */
.rainbow-aura { height:6px; background: linear-gradient(90deg,#00eaff,#ff00d4,#8a2be2); filter: blur(6px); border-radius:6px; margin-top:12px; }

/* small helpers */
.small-muted { color: #cfefff; opacity:0.75; font-size:13px; }
</style>

<div class="aura-ring"></div>
""", unsafe_allow_html=True)

# -------------------------
# Helper: HTML-escape safely
# -------------------------
def esc(s):
    return html.escape(str(s), quote=False)

# -------------------------
# Selenium helpers
# -------------------------
def setup_browser():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--log-level=3")
    try:
        driver = webdriver.Chrome(options=opt)
    except Exception as e:
        raise RuntimeError(f"Failed to start Chrome webdriver: {e}")
    return driver

def find_input(driver, chat_type="E2EE", timeout=12):
    selectors = ["div[contenteditable='true']", "textarea", "[role='textbox']"]
    wait = WebDriverWait(driver, timeout)
    for sel in selectors:
        try:
            elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            return elem
        except Exception:
            continue
    return None

# -------------------------
# Thread worker: send messages, update st.session_state under lock only
# -------------------------
def send_messages_thread(cfg, conv_key):
    """
    Background thread: uses Selenium to send messages, updates st.session_state['conversations'][conv_key] only.
    Does not call Streamlit UI functions directly.
    """
    try:
        # sanity
        with _global_lock:
            conv = st.session_state['conversations'].get(conv_key)
            if not conv:
                return
            conv['running'] = True
            conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Thread starting...")
            conv['last_thread_start'] = time.time()

        # init browser
        driver = None
        try:
            driver = setup_browser()
            driver.get("https://www.facebook.com")
            time.sleep(4)
            # add cookies (if provided)
            raw_cookies = cfg.get('cookies','') or ""
            for cookie in [c.strip() for c in raw_cookies.split(";") if c.strip()]:
                if "=" in cookie:
                    name, val = cookie.split("=",1)
                    try:
                        driver.add_cookie({"name": name.strip(), "value": val.strip(), "domain": ".facebook.com", "path": "/"})
                    except Exception:
                        pass
            # go to chat
            driver.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
            time.sleep(6)
        except Exception as e:
            with _global_lock:
                conv = st.session_state['conversations'].get(conv_key)
                if conv:
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Browser init error: {e}")
                    conv['running'] = False
            if driver:
                try: driver.quit()
                except: pass
            return

        # find input
        box = find_input(driver, cfg.get('chat_type','E2EE'), timeout=12)
        if not box:
            with _global_lock:
                conv = st.session_state['conversations'].get(conv_key)
                if conv:
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Input box not found; stopping.")
                    conv['running'] = False
            try: driver.quit()
            except: pass
            return

        # prepare messages list
        messages_raw = cfg.get('messages','') or ""
        if isinstance(messages_raw, list):
            msgs = [m for m in messages_raw if m.strip()]
        else:
            msgs = [m for m in str(messages_raw).splitlines() if m.strip()]
        if not msgs: msgs = ["Hello!"]

        # sending loop
        while True:
            with _global_lock:
                conv = st.session_state['conversations'].get(conv_key)
                if not conv or not conv.get('running'):
                    break
                rotation_index = conv.get('rotation_index', 0)
                delay = conv.get('delay', 15)
                last_reboot = conv.get('last_reboot', 0)

            msg = msgs[rotation_index % len(msgs)]
            try:
                box.send_keys(msg)
                box.send_keys(Keys.ENTER)
                with _global_lock:
                    conv = st.session_state['conversations'][conv_key]
                    conv['rotation_index'] = rotation_index + 1
                    conv['message_count'] = conv.get('message_count', 0) + 1
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sent: {msg}")
                    conv['logs'] = conv['logs'][-1000:]
            except Exception as e:
                with _global_lock:
                    conv = st.session_state['conversations'][conv_key]
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Send error: {e}")
                # try to re-find input
                try:
                    box = find_input(driver, cfg.get('chat_type','E2EE'), timeout=8)
                except:
                    pass

            # auto-reboot per conversation: restart browser and counters after 10 hours
            if time.time() - last_reboot > 36000:
                with _global_lock:
                    conv = st.session_state['conversations'][conv_key]
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-rebooting conversation.")
                    conv['last_reboot'] = time.time()
                    conv['rotation_index'] = 0
                    conv['message_count'] = 0
                # restart browser
                try:
                    driver.quit()
                except:
                    pass
                try:
                    driver = setup_browser()
                    driver.get("https://www.facebook.com/messages/t/" + cfg.get('chat_id',''))
                    time.sleep(6)
                    box = find_input(driver, cfg.get('chat_type','E2EE'), timeout=12)
                    if not box:
                        with _global_lock:
                            conv = st.session_state['conversations'][conv_key]
                            conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Post-reboot input box not found; stopping.")
                            conv['running'] = False
                        break
                except Exception as e:
                    with _global_lock:
                        conv = st.session_state['conversations'][conv_key]
                        conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Reboot failed: {e}")
                        conv['running'] = False
                    break

            time.sleep(max(1, int(delay)))

        # cleanup
        try: driver.quit()
        except: pass
        with _global_lock:
            conv = st.session_state['conversations'].get(conv_key)
            if conv:
                conv['running'] = False
                conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Thread finished/cleaned.")
    except Exception as e:
        tb = traceback.format_exc()
        with _global_lock:
            conv = st.session_state['conversations'].get(conv_key)
            if conv:
                conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Thread exception: {e}\\n{tb}")
                conv['running'] = False

# -------------------------
# DB sync helpers
# -------------------------
def load_user_conversations_from_db(user_id):
    """
    Loads conversations for the logged-in user from DB and merges them into session_state['conversations'].
    Conversations in DB should include 'running' flag so we can autorun those after app start.
    """
    try:
        convs = db.get_user_conversations(user_id) or []
    except Exception as e:
        st.warning(f"DB load error: {e}")
        convs = []

    with _global_lock:
        for c in convs:
            cid = c.get('chat_id')
            if not cid:
                continue
            # If already in session_state, do not overwrite active thread state; else create entry.
            if cid not in st.session_state['conversations']:
                st.session_state['conversations'][cid] = {
                    "chat_type": c.get('chat_type','E2EE'),
                    "delay": int(c.get('delay',15)),
                    "cookies": c.get('cookies',''),
                    "messages": c.get('messages','').splitlines() if isinstance(c.get('messages',''), str) else c.get('messages',[]),
                    "running": bool(c.get('running', False)),
                    "rotation_index": 0,
                    "message_count": 0,
                    "last_reboot": time.time(),
                    "logs": [f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Loaded from DB."],
                    "thread_id": None
                }

def save_conv_to_db(user_id, chat_id):
    conv = st.session_state['conversations'].get(chat_id)
    if not conv:
        return
    try:
        db.update_conversation_config(
            user_id,
            chat_id,
            conv.get('chat_type','E2EE'),
            conv.get('delay',15),
            conv.get('cookies',''),
            "\n".join(conv.get('messages',[])),
            running=bool(conv.get('running', False))
        )
    except Exception as e:
        # non-fatal
        with _global_lock:
            conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DB save failed: {e}")

# -------------------------
# Login / Create UI
# -------------------------
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["Login","Create Account"])
    with tab1:
        uname = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                uid = db.verify_user(uname, pwd)
            except Exception as e:
                st.error(f"DB error: {e}")
                uid = None
            if uid:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = uid
                # load convs from DB
                load_user_conversations_from_db(uid)
                # autorun convs that had running=True in DB
                # start threads for those
                with _global_lock:
                    for cid, conv in st.session_state['conversations'].items():
                        if conv.get('running'):
                            cfg = {
                                "chat_id": cid,
                                "chat_type": conv.get('chat_type','E2EE'),
                                "delay": conv.get('delay',15),
                                "cookies": conv.get('cookies',''),
                                "messages": conv.get('messages',[])
                            }
                            t = threading.Thread(target=send_messages_thread, args=(cfg, cid), daemon=True)
                            conv['thread_id'] = t.name
                            t.start()
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        nuser = st.text_input("New username")
        npass = st.text_input("New password", type="password")
        npass2 = st.text_input("Confirm password", type="password")
        if st.button("Create"):
            if npass != npass2:
                st.error("Passwords do not match")
            else:
                ok, msg = db.create_user(nuser, npass)
                if ok:
                    st.success("User created. Please login.")
                else:
                    st.error(f"Create failed: {msg}")
    st.stop()

# -------------------------
# Top bar: user info & global status
# -------------------------
colL, colR = st.columns([3,1])
with colL:
    st.markdown(f"<div class='holo-title'>⚡ AURA E23E — Automation</div>", unsafe_allow_html=True)
with colR:
    any_running = any(conv.get('running') for conv in st.session_state['conversations'].values())
    color = "#00ff88" if any_running else "#ff4466"
    status_text = "RUNNING" if any_running else "IDLE"
    st.markdown(f"<div class='glass-card' style='text-align:center'><b style='color:#dff'>{st.session_state['user_id']}</b><div style='margin-top:6px'><span style='color:{color}; font-weight:800'>● {status_text}</span></div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------
# Sidebar slide panel: username, logout, timer (10-hour countdown), add conv
# -------------------------
with st.sidebar:
    st.markdown("<div class='sidebar-glass'>", unsafe_allow_html=True)
    st.markdown(f"### 👤 {esc(st.session_state['user_id'])}", unsafe_allow_html=True)
    st.write("---")

    # Global timer: show minimum remaining time among running convs or 10:00 if none
    running_conv_times = []
    for cid, conv in st.session_state['conversations'].items():
        if conv.get('running'):
            elapsed = time.time() - conv.get('last_reboot', time.time())
            remaining = max(0, 36000 - elapsed)
            running_conv_times.append(remaining)
    if running_conv_times:
        remaining = min(running_conv_times)
        hr = int(remaining // 3600)
        mn = int((remaining % 3600) // 60)
        sec = int(remaining % 60)
        st.metric("⏳ Next auto-reboot in", f"{hr:02d}:{mn:02d}:{sec:02d}")
    else:
        st.metric("⏳ Auto-reboot timer", "10:00:00")

    st.write("---")
    if st.button("🔓 Logout"):
        # stop threads gently and clear session
        with _global_lock:
            for cid in list(st.session_state['conversations'].keys()):
                st.session_state['conversations'][cid]['running'] = False
                st.session_state['conversations'][cid]['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Logout requested.")
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.rerun()

    st.write("---")
    st.markdown("#### ➕ Add Conversation", unsafe_allow_html=True)
    new_chat_id = st.text_input("Chat ID (thread id)")
    new_chat_type = st.selectbox("Chat type", ["E2EE","Non-E2EE"])
    new_delay = st.number_input("Delay (sec)", 1, 3600, value=15)
    new_cookies = st.text_area("Cookies (k=v; k2=v2)")
    new_msgs = st.text_area("Messages (one per line)", height=120)
    if st.button("Add / Save conversation"):
        if not new_chat_id.strip() or not new_msgs.strip():
            st.error("Chat ID and messages required")
        else:
            with _global_lock:
                st.session_state['conversations'][new_chat_id] = {
                    "chat_type": new_chat_type,
                    "delay": int(new_delay),
                    "cookies": new_cookies,
                    "messages": [m for m in new_msgs.splitlines() if m.strip()],
                    "running": False,
                    "rotation_index": 0,
                    "message_count": 0,
                    "last_reboot": time.time(),
                    "logs": [f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Created locally."],
                    "thread_id": None
                }
            # save to DB
            save_conv_to_db(st.session_state['user_id'], new_chat_id)
            st.success(f"Conversation {new_chat_id} added and saved.")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# Main: display conversations in premium cards
# -------------------------
for cid, conv in list(st.session_state['conversations'].items()):
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    cL, cC, cR = st.columns([3,1,1])
    with cL:
        st.markdown(f"### Chat: <b>{esc(cid)}</b>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-muted'>Type: {esc(conv.get('chat_type','E2EE'))} &nbsp; | &nbsp; Delay: {int(conv.get('delay',15))}s</div>", unsafe_allow_html=True)
        # preview messages safely
        preview = conv.get('messages',[])[:6]
        if preview:
            preview_html = "<div style='margin-top:8px; font-size:13px; color:#cfefff; opacity:0.9'>Preview:</div><ul style='margin-top:6px;'>"
            for m in preview:
                preview_html += f"<li style='color:#bfeffb; font-size:13px; margin-bottom:3px'>{esc(m)[:200]}</li>"
            preview_html += "</ul>"
            st.markdown(preview_html, unsafe_allow_html=True)

    with cC:
        # circular stat (messages sent)
        sent = conv.get('message_count', 0)
        pct = min(100, sent % 100)
        svg = f"""
        <svg viewBox='0 0 36 36' style='width:120px;height:120px;display:block;margin:auto'>
          <path d='M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831' fill='none' stroke='rgba(255,255,255,0.06)' stroke-width='2'/>
          <path d='M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831' fill='none' stroke='url(#g{esc(cid)})' stroke-width='2.8' stroke-dasharray='{pct},100' stroke-linecap='round'/>
          <defs><linearGradient id='g{esc(cid)}' x1='0%' y1='0%' x2='100%' y2='0%'>
            <stop offset='0%' stop-color='#00eaff'/><stop offset='50%' stop-color='#ff00d4'/><stop offset='100%' stop-color='#8a2be2'/>
          </linearGradient></defs>
          <text x='18' y='20.5' font-size='4' text-anchor='middle' fill='#bff' font-family='Orbitron'>{sent}</text>
        </svg>
        """
        st.markdown(svg, unsafe_allow_html=True)

    with cR:
        running = conv.get('running', False)
        badge_col = "#00ff88" if running else "#ff4466"
        st.markdown(f"<div style='text-align:center'><div style='font-weight:800;color:{badge_col}'>● {'RUNNING' if running else 'STOPPED'}</div></div>", unsafe_allow_html=True)
        # start/stop buttons
        colS, colT = st.columns(2)
        with colS:
            if st.button(f"▶ START {cid}", key=f"start_{cid}", disabled=running):
                with _global_lock:
                    st.session_state['conversations'][cid]['running'] = True
                    st.session_state['conversations'][cid]['last_reboot'] = time.time()
                cfg = {
                    "chat_id": cid,
                    "chat_type": conv.get('chat_type','E2EE'),
                    "delay": conv.get('delay',15),
                    "cookies": conv.get('cookies',''),
                    "messages": conv.get('messages',[])
                }
                t = threading.Thread(target=send_messages_thread, args=(cfg, cid), daemon=True)
                with _global_lock:
                    st.session_state['conversations'][cid]['thread_id'] = t.name
                t.start()
                # persist changed running flag into DB
                save_conv_to_db(st.session_state['user_id'], cid)
                st.rerun()
        with colT:
            if st.button(f"⏹ STOP {cid}", key=f"stop_{cid}", disabled=not running):
                with _global_lock:
                    st.session_state['conversations'][cid]['running'] = False
                    st.session_state['conversations'][cid]['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Manual stop.")
                save_conv_to_db(st.session_state['user_id'], cid)
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    # logs
    logs_html = "<br>".join([esc(x) for x in conv.get('logs', [])[-200:]])
    st.markdown(f"<div class='log-terminal'>{logs_html}</div>", unsafe_allow_html=True)
    st.markdown("<div class='rainbow-aura'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# -------------------------
# Footer global controls
# -------------------------
cA, cB = st.columns(2)
with cA:
    if st.button("⏯ Start all"):
        started = 0
        with _global_lock:
            for cid, conv in st.session_state['conversations'].items():
                if not conv.get('running'):
                    conv['running'] = True
                    conv['last_reboot'] = time.time()
                    cfg = {
                        "chat_id": cid,
                        "chat_type": conv.get('chat_type','E2EE'),
                        "delay": conv.get('delay',15),
                        "cookies": conv.get('cookies',''),
                        "messages": conv.get('messages',[])
                    }
                    t = threading.Thread(target=send_messages_thread, args=(cfg, cid), daemon=True)
                    conv['thread_id'] = t.name
                    t.start()
                    save_conv_to_db(st.session_state['user_id'], cid)
                    started += 1
        st.success(f"Started {started} conv(s).")
        st.rerun()
with cB:
    if st.button("⏹ Stop all"):
        stopped = 0
        with _global_lock:
            for cid in st.session_state['conversations']:
                if st.session_state['conversations'][cid].get('running'):
                    st.session_state['conversations'][cid]['running'] = False
                    st.session_state['conversations'][cid]['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Global stop requested.")
                    save_conv_to_db(st.session_state['user_id'], cid)
                    stopped += 1
        st.success(f"Requested stop for {stopped} conv(s).")
        st.rerun()

# -------------------------
# Save all configs to DB action
# -------------------------
if st.button("💾 Save all configs to DB"):
    saved = 0
    for cid, conv in st.session_state['conversations'].items():
        try:
            save_conv_to_db(st.session_state['user_id'], cid)
            saved += 1
        except Exception as e:
            st.error(f"Save fail {cid}: {e}")
    st.success(f"Saved {saved} conv(s).")

# End of file

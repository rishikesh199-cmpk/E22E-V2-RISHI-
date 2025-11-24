# streamlit_app.py
import streamlit as st
import threading, time, traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import database as db  # your DB module (must implement: verify_user, create_user, get_user_config, update_user_config)

# ----------------------------------------------------------------
#  Global tiny lock for thread-safe session_state updates
# ----------------------------------------------------------------
_global_lock = threading.Lock()

# ----------------------------------------------------------------
#  Page config
# ----------------------------------------------------------------
st.set_page_config(page_title="AURA E23E - Premium Automation", page_icon="⚡", layout="wide")

# ----------------------------------------------------------------
#  AUTO-REFRESH (JS based) - reload page every X ms so UI shows updated logs
#  Using JS reload keeps st.session_state persistent and avoids Streamlit thread UI calls.
#  Set refresh interval (ms)
# ----------------------------------------------------------------
REFRESH_INTERVAL_MS = 2500  # 2.5s
st.markdown(f"""
<script>
    // Only auto-reload when not focusing form inputs to avoid interrupting user typing.
    let reloadInterval = setInterval(() => {{
        if (!document.activeElement || document.activeElement.tagName.toLowerCase() === 'body') {{
            window.location.reload();
        }}
    }}, {REFRESH_INTERVAL_MS});
</script>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
#  Helper: safe session init
# ----------------------------------------------------------------
def s_init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

# Session defaults
s_init("logged_in", False)
s_init("user_id", None)
s_init("conversations", {})  # dict: chat_id -> conv_state
s_init("global_running", False)  # global master switch (not required but useful)
s_init("ui_last_update", time.time())

# ----------------------------------------------------------------
#  CSS + AURA + HOLOGRAM + 3D TILT + STYLES
# ----------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap');

/* ---------- AURA / BACKGROUND ---------- */
body {
    background: radial-gradient(ellipse at 10% 10%, rgba(0,255,255,0.06), transparent 10%),
                radial-gradient(ellipse at 90% 90%, rgba(255,0,255,0.04), transparent 10%),
                url('https://i.ibb.co/9k1k2c6f/bg.png') no-repeat center center fixed;
    background-size: cover;
    color: #c7fbff;
}

/* ---------- AURA RING ---------- */
.aura-ring {
    position: absolute;
    width: 420px;
    height: 420px;
    border-radius: 50%;
    top: -100px;
    left: calc(50% - 210px);
    background: radial-gradient(circle, rgba(0,255,255,0.12) 0%, rgba(255,0,255,0.08) 40%, rgba(0,0,0,0) 70%);
    filter: blur(40px);
    animation: auraPulse 6s infinite ease-in-out;
    z-index:-1;
}
@keyframes auraPulse {
    0% { transform: scale(1); opacity:0.7; }
    50% { transform: scale(1.18); opacity:1; }
    100% { transform: scale(1); opacity:0.7; }
}

/* ---------- TITLE / HOLOGRAM ---------- */
.holo-title {
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    font-size: 46px;
    text-align: center;
    margin: 18px 0;
    background: linear-gradient(90deg,#00eaff,#ff00d4,#8a2be2,#00eaff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-size: 200%;
    animation: holoFlow 6s linear infinite;
    text-shadow: 0 0 18px rgba(0,255,255,0.25);
}
@keyframes holoFlow {
    0% { background-position: 0% 0%; }
    50% { background-position: 100% 0%; }
    100% { background-position: 0% 0%; }
}

/* ---------- GLASS CARD ---------- */
.glass-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
    border-radius: 18px;
    padding: 18px;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 6px 30px rgba(0,0,0,0.45), 0 0 30px rgba(0,255,255,0.06);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    position: relative;
}

/* 3D tilt effect on hover */
.glass-card:hover {
    transform: perspective(600px) rotateX(3deg) rotateY(-3deg) translateY(-6px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.6), 0 0 50px rgba(0,255,255,0.09);
}

/* ---------- STATUS BADGE ---------- */
.status-badge {
    font-size: 16px;
    font-weight: 800;
    padding: 8px 18px;
    border-radius: 999px;
    display:inline-block;
    border: 1px solid rgba(255,255,255,0.06);
}

/* ---------- LOG TERMINAL ---------- */
.log-terminal {
    background: rgba(0,0,0,0.55);
    border-radius: 12px;
    padding: 12px;
    height: 300px;
    overflow-y: auto;
    border: 1px solid rgba(0,255,255,0.14);
    box-shadow: inset 0 0 35px rgba(0,255,255,0.05);
    color: #a8ffff;
    font-family: 'Courier New', monospace;
    font-size: 13px;
}

/* ---------- NEON BUTTONS ---------- */
.stButton>button {
    background: linear-gradient(90deg,#00eaff,#ff00d4);
    color: white !important;
    border: none !important;
    padding: 10px 18px !important;
    border-radius: 12px !important;
    font-weight: 800 !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.45), 0 0 20px rgba(0,255,255,0.08);
}

/* ---------- RAINBOW AURA UNDER CARDS ---------- */
.rainbow-aura {
    position: absolute;
    left: 0; right: 0;
    height: 6px;
    background: linear-gradient(90deg, rgba(0,234,255,0.6), rgba(255,0,212,0.6), rgba(255,255,0,0.6));
    filter: blur(8px);
    margin-top: 10px;
    border-radius: 6px;
    opacity: 0.9;
}

/* ---------- CIRCULAR STATS (SVG container) ---------- */
.stats-svg {
    display:block;
    margin:auto;
    width:120px;
    height:120px;
}

/* ---------- PARTICLES ---------- */
.particle {
    position: absolute;
    width: 8px; height: 8px; border-radius:50%;
    background: radial-gradient(circle,#0ff,#f0f);
    filter: blur(1px);
    opacity:0.8;
    animation: float 5s infinite ease-in-out;
}
.p1 { left:6%; top:20%; animation-duration:6s; }
.p2 { left:88%; top:18%; animation-duration:4.5s; }
.p3 { left:60%; top:84%; animation-duration:7s; }
.p4 { left:22%; top:72%; animation-duration:5.5s; }
@keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-18px); }
    100% { transform: translateY(0px); }
}
</style>

<div class="aura-ring"></div>
<div class="particle p1"></div>
<div class="particle p2"></div>
<div class="particle p3"></div>
<div class="particle p4"></div>

<div class="holo-title">⚡ AURA E23E — Premium Automation</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
#  Utility functions for Selenium/browser setup & finders
# ----------------------------------------------------------------
def setup_browser(cfg):
    """
    Create and return a Chrome webdriver. Adjust options/path here for your deployment.
    """
    opt = Options()
    # headless in newer chrome:
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    # recommended for many servers:
    opt.add_argument("--disable-gpu")
    opt.add_argument("--log-level=3")
    try:
        driver = webdriver.Chrome(options=opt)
    except Exception as e:
        # try to raise a helpful message in logs instead of crashing thread
        raise RuntimeError(f"Failed to init Chrome webdriver: {e}")
    return driver

def find_input(driver, chat_type="E2EE", timeout=12):
    """
    Try to find a message input element (contenteditable etc.). Use explicit waits.
    """
    selectors = ["div[contenteditable='true']", "textarea", "[role='textbox']"]
    wait = WebDriverWait(driver, timeout)
    for sel in selectors:
        try:
            elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            return elem
        except Exception:
            continue
    return None

# ----------------------------------------------------------------
#  Thread target: ONLY update st.session_state (no Streamlit calls!)
# ----------------------------------------------------------------
def send_messages_thread(cfg, conv_key):
    """
    Background thread: sends messages via Selenium and updates st.session_state['conversations'][conv_key]
    IMPORTANT: Do NOT call Streamlit functions here (like st.markdown). Only update session state.
    """
    try:
        with _global_lock:
            conv = st.session_state['conversations'].get(conv_key)
            if not conv:
                return
            conv['running'] = True
            conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting browser...")
            conv['last_thread_start'] = time.time()

        # open browser
        driver = None
        try:
            driver = setup_browser(cfg)
            # initial domain load required before adding cookies
            driver.get("https://www.facebook.com")
            time.sleep(4)

            # add cookies if any (format: "k=v;k2=v2;...")
            raw_cookies = cfg.get('cookies') or ""
            for c in [cc.strip() for cc in raw_cookies.split(";") if cc.strip()]:
                if "=" in c:
                    name, val = c.split("=", 1)
                    try:
                        driver.add_cookie({"name": name.strip(), "value": val.strip(), "domain": ".facebook.com", "path": "/"})
                    except Exception:
                        # skip cookie
                        pass
            # navigate to chat
            driver.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
            time.sleep(6)
        except Exception as e:
            with _global_lock:
                conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Browser init error: {e}")
                conv['running'] = False
            if driver:
                try:
                    driver.quit()
                except: pass
            return

        # find input box
        box = find_input(driver, cfg.get('chat_type','E2EE'), timeout=12)
        if not box:
            with _global_lock:
                conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Input box not found; stopping.")
                conv['running'] = False
            try:
                driver.quit()
            except: pass
            return

        messages = cfg.get('messages') or ["Hello!"]
        # ensure messages list
        if isinstance(messages, str):
            messages = messages.split("\n")
        messages = [m for m in messages if m.strip()]
        if not messages:
            messages = ["Hello!"]

        # sending loop
        while True:
            with _global_lock:
                conv = st.session_state['conversations'].get(conv_key)
                if not conv or not conv.get('running'):
                    break
                rotation_index = conv.get('rotation_index', 0)
                delay = conv.get('delay', 15)
                last_reboot = conv.get('last_reboot', 0)

            # prepare message
            msg = messages[rotation_index % len(messages)]
            # attempt send
            try:
                box.send_keys(msg)
                box.send_keys(Keys.ENTER)
                with _global_lock:
                    conv = st.session_state['conversations'][conv_key]
                    conv['rotation_index'] = rotation_index + 1
                    conv['message_count'] = conv.get('message_count', 0) + 1
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sent: {msg}")
                    # keep logs trimmed
                    conv['logs'] = conv['logs'][-1000:]
            except Exception as e:
                with _global_lock:
                    conv = st.session_state['conversations'][conv_key]
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Send error: {e}")
                # maybe try to reacquire input box
                try:
                    box = find_input(driver, cfg.get('chat_type','E2EE'), timeout=8)
                except:
                    pass

            # check auto-reboot
            if time.time() - last_reboot > 36000:  # 10 hours
                with _global_lock:
                    conv = st.session_state['conversations'][conv_key]
                    conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-reboot: restarting browser and state.")
                    # reset counters as desired
                    conv['last_reboot'] = time.time()
                    conv['rotation_index'] = 0
                    conv['message_count'] = 0
                # restart logic: close driver and re-init
                try:
                    driver.quit()
                except:
                    pass
                try:
                    driver = setup_browser(cfg)
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

            # sleep for delay interval (non-blocking to UI since thread)
            time.sleep(max(1, int(delay)))

        # cleanup
        try:
            driver.quit()
        except:
            pass
        with _global_lock:
            conv = st.session_state['conversations'].get(conv_key)
            if conv:
                conv['running'] = False
                conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Automation stopped.")
    except Exception as e:
        # log unexpected thread exception
        tb = traceback.format_exc()
        with _global_lock:
            conv = st.session_state['conversations'].get(conv_key)
            if conv:
                conv['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Thread exception: {e}\\n{tb}")
                conv['running'] = False

# ----------------------------------------------------------------
#  UI: Login / Create
# ----------------------------------------------------------------
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["Login", "Create Account"])
    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            uid = db.verify_user(u, p)
            if uid:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = uid
                # optionally load user convs from DB if implemented
                cfg = db.get_user_config(uid) or {}
                # keep as-is; user will add convs manually
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        npc = st.text_input("Confirm Password", type="password")
        if st.button("Create"):
            if np != npc:
                st.error("Passwords do not match")
            else:
                ok, msg = db.create_user(nu, np)
                if ok:
                    st.success("User created — please login.")
                else:
                    st.error(f"Create failed: {msg}")
    st.stop()

# ----------------------------------------------------------------
#  Top control & global monitor
# ----------------------------------------------------------------
col_top_left, col_top_right = st.columns([3,1])
with col_top_left:
    st.markdown(f"<div class='glass-card'><b style='font-size:18px'>User:</b> <span style='opacity:0.9;margin-left:8px'>{st.session_state['user_id']}</span></div>", unsafe_allow_html=True)
with col_top_right:
    # Global running indicator
    any_running = any(conv.get('running') for conv in st.session_state['conversations'].values())
    badge_color = "#00ff88" if any_running else "#ff3366"
    status_text = "RUNNING" if any_running else "IDLE"
    st.markdown(f"<div class='glass-card' style='text-align:center'><span class='status-badge' style='color:{badge_color}; border-color:{badge_color};'>● {status_text}</span></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ----------------------------------------------------------------
#  Add Conversation form
# ----------------------------------------------------------------
with st.expander("➕ Add / Load Conversation", expanded=False):
    new_chat_id = st.text_input("Chat ID (thread ID or username)")
    new_chat_type = st.selectbox("Chat Type", ["E2EE", "Non-E2EE"], index=0)
    new_delay = st.number_input("Delay (sec)", 1, 3600, value=15)
    new_cookies = st.text_area("Cookies (k=v; k2=v2; ...)")
    new_file = st.file_uploader("Upload .txt messages file", type=["txt"])
    new_messages = []
    if new_file:
        new_messages = new_file.read().decode("utf-8").splitlines()
    new_messages_text = st.text_area("Or paste messages (one per line)", value="\n".join(new_messages), height=120)
    if st.button("Add Conversation"):
        if not new_chat_id or not new_messages_text.strip():
            st.error("Chat ID and messages are required.")
        else:
            with _global_lock:
                st.session_state['conversations'][new_chat_id] = {
                    "running": False,
                    "logs": [f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Conversation added."],
                    "rotation_index": 0,
                    "last_reboot": time.time(),
                    "thread_id": None,
                    "chat_type": new_chat_type,
                    "delay": int(new_delay),
                    "cookies": new_cookies,
                    "messages": [m for m in new_messages_text.splitlines() if m.strip()],
                    "message_count": 0
                }
            st.success(f"Conversation {new_chat_id} added.")

st.markdown("<hr>", unsafe_allow_html=True)

# ----------------------------------------------------------------
#  Display conversations: each in a premium card with controls, logs, circular stats
# ----------------------------------------------------------------
for cid, conv in list(st.session_state['conversations'].items()):
    # container for each conversation
    st.markdown(f"<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3,1,1])
    with c1:
        st.markdown(f"<h3 style='margin:0 0 6px 0'>Chat: <b>{cid}</b></h3>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #cfefff; opacity:0.85; margin-bottom:6px;'>Type: {conv.get('chat_type','E2EE')} &nbsp; | &nbsp; Delay: {conv.get('delay',15)}s</div>", unsafe_allow_html=True)
        # message list preview
        msgs_preview = conv.get('messages', [])[:6]
        if msgs_preview:
            preview_html = "<div style='opacity:0.8; font-size:13px; margin-bottom:6px;'>Messages preview:</div><ul style='margin-top:0;'>"
            for m in msgs_preview:
                preview_html += f"<li style='color:#bdf9ff; font-size:13px; margin-bottom:2px;'>{st.utils.escape(m)[:120]}</li>"
            preview_html += "</ul>"
            st.markdown(preview_html, unsafe_allow_html=True)

    with c2:
        # circular stat (messages sent)
        sent = conv.get('message_count', 0)
        # simple SVG circle progress based on message_count % 100 for visualization
        pct = min(100, sent % 100)
        svg = f"""
        <svg class='stats-svg' viewBox='0 0 36 36'>
          <path d='M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831' fill='none' stroke='rgba(255,255,255,0.06)' stroke-width='2'/>
          <path d='M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831' fill='none' stroke='url(#g{cid})' stroke-width='2.8' stroke-dasharray='{pct},100' stroke-linecap='round'/>
          <defs>
            <linearGradient id='g{cid}' x1='0%' y1='0%' x2='100%' y2='0%'>
              <stop offset='0%' stop-color='#00eaff'/>
              <stop offset='50%' stop-color='#ff00d4'/>
              <stop offset='100%' stop-color='#8a2be2'/>
            </linearGradient>
          </defs>
          <text x='18' y='20.5' font-size='4' text-anchor='middle' fill='#bff' font-family='Orbitron'>{sent}</text>
        </svg>
        """
        st.markdown(svg, unsafe_allow_html=True)

    with c3:
        # status and buttons
        running = conv.get('running', False)
        badge_color = "#00ff88" if running else "#ff4466"
        state_text = "RUNNING" if running else "STOPPED"
        st.markdown(f"<div style='text-align:center; margin-top:4px;'><span class='status-badge' style='color:{badge_color}; border:1px solid {badge_color};'>{state_text}</span></div>", unsafe_allow_html=True)
        col_start, col_stop = st.columns(2)
        with col_start:
            if st.button(f"▶ START {cid}", key=f"start_{cid}", disabled=running):
                # start thread
                with _global_lock:
                    # Update conv config from UI-held values (if user changed)
                    st.session_state['conversations'][cid]['running'] = True
                    st.session_state['conversations'][cid]['last_reboot'] = time.time()
                cfg = {
                    "chat_id": cid,
                    "chat_type": conv.get('chat_type', 'E2EE'),
                    "delay": conv.get('delay', 15),
                    "cookies": conv.get('cookies', ''),
                    "messages": conv.get('messages', [])
                }
                t = threading.Thread(target=send_messages_thread, args=(cfg, cid), daemon=True)
                with _global_lock:
                    st.session_state['conversations'][cid]['thread_id'] = t.name
                t.start()
                st.experimental_rerun()
        with col_stop:
            if st.button(f"⏹ STOP {cid}", key=f"stop_{cid}", disabled=not running):
                with _global_lock:
                    st.session_state['conversations'][cid]['running'] = False
                    st.session_state['conversations'][cid]['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Manual stop requested.")
                st.experimental_rerun()

    # logs and controls full-width
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    log_html = "<br>".join(conv.get('logs', [])[-200:])
    st.markdown(f"<div class='log-terminal'>{log_html}</div>", unsafe_allow_html=True)

    # rainbow aura underline
    st.markdown("<div class='rainbow-aura' style='margin-top:10px;'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ----------------------------------------------------------------
#  Footer: global actions and save/load to DB
# ----------------------------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    if st.button("⏯️ Start all"):
        started = 0
        for cid, conv in st.session_state['conversations'].items():
            if not conv.get('running'):
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
                started += 1
        st.success(f"Started {started} conversations.")
        st.experimental_rerun()
with col_b:
    if st.button("⏹ Stop all"):
        stopped = 0
        with _global_lock:
            for cid in st.session_state['conversations']:
                if st.session_state['conversations'][cid]['running']:
                    st.session_state['conversations'][cid]['running'] = False
                    st.session_state['conversations'][cid]['logs'].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Global stop requested.")
                    stopped += 1
        st.success(f"Requested stop for {stopped} conversations.")
        st.experimental_rerun()

st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

# ----------------------------------------------------------------
#  Optional: Save conversation configs to DB (if DB supports it)
# ----------------------------------------------------------------
if st.button("💾 Save all configs to DB"):
    saved = 0
    for cid, conv in st.session_state['conversations'].items():
        try:
            # DB API assumed: update_user_config(user_id, chat_id, chat_type, delay, cookies, messages_joined, running)
            db.update_user_config(st.session_state['user_id'],
                                  cid,
                                  conv.get('chat_type','E2EE'),
                                  conv.get('delay',15),
                                  conv.get('cookies',''),
                                  "\n".join(conv.get('messages',[])),
                                  running=conv.get('running', False))
            saved += 1
        except Exception as e:
            st.error(f"Save failed for {cid}: {e}")
    st.success(f"Saved {saved} conv(s).")

# ----------------------------------------------------------------
#  End of app
# ----------------------------------------------------------------

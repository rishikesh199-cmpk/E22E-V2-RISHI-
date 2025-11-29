import streamlit as st
import threading, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import database as db  # Your database module
from pathlib import Path

st.set_page_config(page_title="Automation", page_icon="🔥", layout="wide")

# ---------------- CSS & STYLING ----------------
st.markdown("""
<style>
/* Full HD background */
.stApp {
    background: url('https://i.ibb.co/9k1k2c6f/bg.png') no-repeat center center fixed;
    background-size: cover;
}
.stApp::before {
    content: "";
    position: fixed;
    top:0; left:0; width:0%; height:0%;
    background: rgba(0,0,0,0.1);  /* overlay for text readability */
    pointer-events:none;
    z-index:0;
}

/* Cards */
.stCard {
    background: rgba(255,255,255,0.002) !important;
    border-radius: 20px !important;
    padding: 25px !important;
    border: 2px solid rgba(255,255,255,0.25) !important;
    box-shadow: 0 0 25px rgba(0,255,255,0.4), 0 0 60px rgba(255,0,255,0.3);
    transition: all 0.3s ease-in-out;
}
.stCard:hover {
    box-shadow: 0 0 35px rgba(0,255,255,0.6), 0 0 70px rgba(255,0,255,0.5);
}

/* Inputs glowing */
input, textarea {
    background: rgba(0,0,0,0.5) !important;
    border: 2px solid #0ff !important;
    border-radius: 10px !important;
    color: #0ff !important;
    padding: 5px 10px !important;
}
input:focus, textarea:focus {
    outline: none;
    border: 2px solid #ff00ff !important;
    box-shadow: 0 0 15px #ff00ff;
}

/* Buttons glowing */
.stButton>button {
    background: linear-gradient(45deg,#00eaff,#ff00d4) !important;
    color:#fff !important;
    border:none !important;
    border-radius:10px !important;
    padding:10px 25px !important;
    font-weight:700 !important;
}

/* Logo */
.logo {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    animation: pulse 2s infinite;
    display:block;
    margin:auto;
}
@keyframes pulse {
    0% { transform: scale(1); box-shadow: 0 0 15px rgba(0,255,255,0.6); }
    50% { transform: scale(1.12); box-shadow: 0 0 40px rgba(0,255,255,0.8); }
    100% { transform: scale(1); box-shadow: 0 0 15px rgba(0,255,255,0.6); }
}

/* Title: watercolor text */
.title {
    font-family: 'Orbitron', sans-serif;
    font-size: 3.2rem;
    font-weight: 900;
    text-align:center;
    background: url('https://i.ibb.co/0G6Kj8V/watercolor-texture.jpg') repeat;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-size: cover;
    animation: waterFlow 6s ease-in-out infinite;
    margin-bottom: 25px;
}
@keyframes waterFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Live logs */
.logbox {
    background: rgba(0,0,0,0.55);
    color: #0ff;
    padding: 15px;
    height: 300px;
    overflow:auto;
    border-radius: 20px;
    box-shadow: 0 0 20px rgba(0,255,255,0.35);
    font-family: monospace;
    white-space: pre-wrap;
}

/* Sparkles */
@keyframes sparkle {
    0% { transform: translate(0,0) rotate(0deg); opacity:1; }
    100% { transform: translate(100px,-100px) rotate(360deg); opacity:0; }
}
.sparkle {
    position: absolute;
    width: 6px;
    height: 6px;
    background: linear-gradient(45deg, #0ff, #f0f, #ff0);
    border-radius: 50%;
    animation: sparkle 2s linear infinite;
}
</style>

<img class="logo" src="https://i.ibb.co/m5G9GdXx/logo.png" alt="Logo">
<div class="sparkle" style="top:5%; left:5%;"></div>
<div class="sparkle" style="top:10%; right:10%;"></div>
<div class="sparkle" style="bottom:10%; left:15%;"></div>
<div class="sparkle" style="bottom:5%; right:5%;"></div>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown('<div class="title"><h1>E23E FB<h1></div>', unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in=False
if 'user_id' not in st.session_state: st.session_state.user_id=None
if 'automation_running' not in st.session_state: st.session_state.automation_running=False
if 'automation_state' not in st.session_state:
    st.session_state.automation_state=type('obj',(object,),{
        "running":False,
        "message_count":0,
        "message_rotation_index":0,
        "logs":[]
    })()

# helper to append logs safely
def append_log(line):
    try:
        st.session_state.automation_state.logs.append(f"[{time.strftime('%H:%M:%S')}] {str(line)}")
    except Exception:
        # fallback: ensure logs exist
        if 'automation_state' not in st.session_state:
            st.session_state.automation_state=type('obj',(object,),{
                "running":False,
                "message_count":0,
                "message_rotation_index":0,
                "logs":[]
            })()
        st.session_state.automation_state.logs.append(f"[{time.strftime('%H:%M:%S')}] {str(line)}")

# ---------------- LOGIN / CREATE ----------------
if not st.session_state.logged_in:
    tab1,tab2=st.tabs(["Login","Create Account"])
    with tab1:
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Login"):
            uid=db.verify_user(u,p)
            if uid:
                st.session_state.logged_in=True
                st.session_state.user_id=uid
                cfg=db.get_user_config(uid)
                # load previous settings
                st.session_state.chat_id=cfg.get('chat_id','')
                st.session_state.chat_type=cfg.get('chat_type','E2EE')
                st.session_state.delay=cfg.get('delay',15)
                st.session_state.cookies=cfg.get('cookies','')
                msgs = cfg.get('messages','')
                st.session_state.messages=msgs.split("\n") if msgs else []
                if cfg.get('running',False):
                    st.session_state.automation_state.running=True
                    st.session_state.automation_running=True
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        nu=st.text_input("New Username")
        np=st.text_input("New Password",type="password")
        npc=st.text_input("Confirm Password",type="password")
        if st.button("Create User"):
            if np!=npc: st.error("Passwords do not match")
            else:
                ok,msg=db.create_user(nu,np)
                if ok: st.success("User created!")
                else: st.error(msg)
    st.stop()

# ---------------- DASHBOARD ----------------
st.subheader(f"👤 Dashboard ({st.session_state.user_id})")
if st.button("Logout"):
    st.session_state.logged_in=False
    st.session_state.user_id=None
    st.session_state.automation_running=False
    st.session_state.automation_state.running=False
    st.rerun()

# ---------------- MESSAGE UPLOAD ----------------
msg_file=st.file_uploader("Upload .txt Messages File",type=["txt"])
if msg_file:
    st.session_state.messages=msg_file.read().decode("utf-8").split("\n")
    st.success("Messages loaded!")

# ---------------- CONFIG ----------------
chat_id=st.text_input("Chat ID",value=getattr(st.session_state,'chat_id',''))
chat_type=st.selectbox("Chat Type",["E2EE","Non-E2EE"],index=0 if getattr(st.session_state,'chat_type','E2EE')=='E2EE' else 1)
delay=st.number_input("Delay (sec)",1,300,value=getattr(st.session_state,'delay',15))
cookies=st.text_area("Cookies",value=getattr(st.session_state,'cookies',''))

if st.button("Save Config"):
    db.update_user_config(st.session_state.user_id,chat_id,chat_type,delay,cookies,"\n".join(st.session_state.messages),running=st.session_state.automation_running)
    st.success("Saved!")

# ---------------- AUTOMATION ENGINE ----------------
def setup_browser():
    opt=Options()
    opt.add_argument('--headless=new')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    # Try to set binary if available (improves reliability in some environments)
    chromium_paths = [
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/usr/bin/google-chrome',
        '/usr/bin/chrome'
    ]
    for p in chromium_paths:
        if Path(p).exists():
            opt.binary_location = p
            break
    return webdriver.Chrome(options=opt)

def find_input(driver,chat_type):
    selectors=["div[contenteditable='true']"] if chat_type=="E2EE" else ["div[contenteditable='true']","textarea","[role='textbox']"]
    for s in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR,s)
            return el
        except Exception:
            pass
    return None

def safe_add_cookies(driver, cookie_string):
    for c in (cookie_string or "").split(";"):
        c = c.strip()
        if not c:
            continue
        if "=" in c:
            n,v = c.split("=",1)
            try:
                driver.add_cookie({"name":n.strip(),"value":v.strip(),"domain":".facebook.com","path":"/"})
            except Exception as e:
                append_log(f"Cookie failed for {n.strip()}: {e}")
        else:
            append_log(f"Skipping invalid cookie part: {c}")

def send_messages(cfg, stt):
    """Runs in background thread. Writes logs into st.session_state.automation_state.logs"""
    try:
        append_log("Starting browser...")
        d = None
        try:
            d = setup_browser()
        except Exception as e:
            append_log(f"Browser setup failed: {e}")
            stt.running = False
            st.session_state.automation_running = False
            return

        try:
            d.get("https://www.facebook.com")
            append_log("Browser loaded Facebook")
            time.sleep(6)
        except Exception as e:
            append_log(f"Error loading Facebook: {e}")

        # cookies
        try:
            safe_add_cookies(d, cfg.get('cookies','') or "")
        except Exception as e:
            append_log(f"Adding cookies failed: {e}")

        try:
            chat_url = f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}"
            d.get(chat_url)
            append_log(f"Opened chat {cfg.get('chat_id','')}")
            time.sleep(8)
        except Exception as e:
            append_log(f"Error opening chat: {e}")

        box = find_input(d, cfg.get('chat_type','E2EE'))
        if not box:
            append_log("Input box not found!")
            stt.running = False
            st.session_state.automation_running = False
            try:
                d.quit()
            except:
                pass
            return

        msgs = [m for m in (cfg.get('messages') or "").split("\n") if m.strip()]
        if not msgs:
            msgs = ["Hello!"]

        delay_local = int(cfg.get('delay',15))

        while stt.running:
            try:
                m = msgs[stt.message_rotation_index % len(msgs)]
                stt.message_rotation_index += 1

                # try to send - prefer JavaScript injection for contenteditable divs
                try:
                    tag = box.tag_name.lower()
                except:
                    tag = ""
                if tag == 'div':
                    try:
                        d.execute_script("""
                            const el = arguments[0];
                            const message = arguments[1];
                            el.focus();
                            el.innerHTML = message.replace(/\\n/g,'<br>');
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                        """, box, m)
                        time.sleep(0.5)
                    except Exception as e:
                        append_log(f"JS insert failed: {e}")
                        try:
                            box.click()
                            box.send_keys(m)
                        except Exception as e2:
                            append_log(f"Fallback typing failed: {e2}")
                else:
                    try:
                        box.click()
                        box.send_keys(m)
                    except Exception as e:
                        append_log(f"Typing failed: {e}")

                # try to click send button
                try:
                    sent = d.execute_script("""
                        const sendButtons = Array.from(document.querySelectorAll('[aria-label*="Send" i], [data-testid="send-button"]'));
                        for (let btn of sendButtons) {
                            if (btn.offsetParent !== null) { btn.click(); return true; }
                        }
                        return false;
                    """)
                    if sent:
                        append_log(f"Sent: {m}")
                    else:
                        # try Enter key
                        try:
                            box.send_keys("\n")
                            append_log(f"Sent via Enter: {m}")
                        except Exception as e:
                            append_log(f"Send action failed: {e}")
                except Exception as e:
                    append_log(f"Click send failed: {e}")

                stt.message_count += 1
                st.session_state.automation_state.message_count = stt.message_count

            except Exception as e:
                append_log(f"Error in send loop: {e}")
                break

            # sleep with small increments to remain responsive if stopped
            slept = 0
            while slept < delay_local and stt.running:
                time.sleep(0.5)
                slept += 0.5

        append_log("Automation stopped")
    except Exception as e:
        append_log(f"Fatal error in automation: {e}")
    finally:
        try:
            if 'd' in locals() and d:
                try:
                    d.quit()
                except:
                    pass
        except:
            pass
        stt.running = False
        st.session_state.automation_running = False

# ---------------- AUTOMATION CONTROLS ----------------
st.subheader("🚀 Automation")
col1,col2=st.columns(2)
if col1.button("▶️ START",disabled=st.session_state.automation_running):
    cfg=db.get_user_config(st.session_state.user_id)
    # ensure required keys exist
    cfg = cfg or {}
    cfg.setdefault('chat_id', chat_id)
    cfg.setdefault('chat_type', chat_type)
    cfg.setdefault('delay', delay)
    cfg.setdefault('cookies', cookies)
    cfg.setdefault('messages', "\n".join(getattr(st.session_state,'messages',[])))
    cfg['running']=True
    st.session_state.automation_state.running=True
    st.session_state.automation_running=True
    t=threading.Thread(target=send_messages,args=(cfg,st.session_state.automation_state))
    t.daemon=True
    t.start()
if col2.button("⏹️ STOP",disabled=not st.session_state.automation_running):
    st.session_state.automation_state.running=False
    st.session_state.automation_running=False

# ---------------- LIVE LOGS ----------------
st.subheader("📡 Live Logs & Messages Sent")

# --- Auto-refresh mechanism ---
# If automation is running, rerun this script every 1 second to pick up new logs appended by background thread.
# We throttle reruns using last_refresh timestamp in session_state.
now = time.time()
last = st.session_state.get('last_logs_refresh', 0)
if st.session_state.automation_state.running and (now - last) > 1.0:
    st.session_state.last_logs_refresh = now
    # small sleep to let background thread append some logs if just started
    time.sleep(0.05)
    # Trigger rerun so UI refreshes and shows latest logs
    try:
        st.experimental_rerun()
    except Exception:
        pass

st.write(f"Messages Sent: {st.session_state.automation_state.message_count}")

# Render logs in a styled box. Show last 200 entries max.
logs_to_show = st.session_state.automation_state.logs[-200:]
# Provide an auto-scroll by printing logs as a single string (browser will scroll within div)
logs_joined = "\n".join(logs_to_show) if logs_to_show else "[No logs yet]"

st.markdown('<div class="logbox">',unsafe_allow_html=True)
st.markdown(f"```\n{logs_joined}\n```", unsafe_allow_html=True)
st.markdown('</div>',unsafe_allow_html=True)

# Buttons to clear logs or download logs
colc, cold = st.columns([1,1])
with colc:
    if st.button("🧹 Clear Logs"):
        st.session_state.automation_state.logs = []
        st.session_state.automation_state.message_count = 0
        st.session_state.automation_state.message_rotation_index = 0
        st.session_state.last_logs_refresh = time.time()
        st.experimental_rerun()
with cold:
    if st.button("📥 Download Logs"):
        txt = "\n".join(st.session_state.automation_state.logs)
        st.download_button("Download .txt", txt, file_name="automation_logs.txt", mime="text/plain")

# ---------------- AUTO-REBOOT 10 HOURS ----------------
def auto_reboot():
    time.sleep(36000)
    db.update_user_config(st.session_state.user_id,chat_id,chat_type,delay,cookies,"\n".join(st.session_state.messages),running=st.session_state.automation_running)
    try:
        st.experimental_rerun()
    except Exception:
        pass

if not hasattr(st.session_state,"reboot_thread"):
    t_reboot=threading.Thread(target=auto_reboot)
    t_reboot.daemon=True
    t_reboot.start()
    st.session_state.reboot_thread=True

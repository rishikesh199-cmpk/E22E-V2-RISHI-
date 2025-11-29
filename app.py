import streamlit as st
import threading, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import database as db  # Your database module

#---------------- PAGE CONFIG ----------------

st.set_page_config(page_title="Automation", page_icon="🔥", layout="wide")

#---------------- CSS & STYLING ----------------

st.markdown("""

<style>
/* Background */
.stApp { background: url('https://i.ibb.co/9k1k2c6f/bg.png') no-repeat center center fixed; background-size: cover; }
/* Cards */
.stCard { background: rgba(255,255,255,0.002); border-radius:20px; padding:25px; border:2px solid rgba(255,255,255,0.25); box-shadow:0 0 25px rgba(0,255,255,0.4),0 0 60px rgba(255,0,255,0.3); transition:0.3s; }
.stCard:hover { box-shadow:0 0 35px rgba(0,255,255,0.6),0 0 70px rgba(255,0,255,0.5); }
/* Inputs */
input,textarea { background: rgba(0,0,0,0.5); border:2px solid #0ff; border-radius:10px; color:#0ff; padding:5px 10px; }
input:focus,textarea:focus { outline:none; border:2px solid #ff00ff; box-shadow:0 0 15px #ff00ff; }
/* Buttons */
.stButton>button { background: linear-gradient(45deg,#00eaff,#ff00d4); color:#fff; border:none; border-radius:10px; padding:10px 25px; font-weight:700; }
/* Logo */
.logo { width:120px; height:120px; border-radius:50%; animation:pulse 2s infinite; display:block; margin:auto; }
@keyframes pulse {0%{transform:scale(1);box-shadow:0 0 15px rgba(0,255,255,0.6);}50%{transform:scale(1.12);box-shadow:0 0 40px rgba(0,255,255,0.8);}100%{transform:scale(1);box-shadow:0 0 15px rgba(0,255,255,0.6);}}
/* Title */
.title { font-family:'Orbitron',sans-serif; font-size:3.2rem; font-weight:900; text-align:center; background:url('https://i.ibb.co/0G6Kj8V/watercolor-texture.jpg') repeat; -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-size:cover; animation:waterFlow 6s ease-in-out infinite; margin-bottom:25px; }
@keyframes waterFlow { 0%{background-position:0% 50%;} 50%{background-position:100% 50%;} 100%{background-position:0% 50%;} }
</style><img class="logo" src="https://i.ibb.co/m5G9GdXx/logo.png">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)st.markdown('<div class="title"><h1>E23E FB</h1></div>', unsafe_allow_html=True)

#---------------- SESSION STATE ----------------

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

#---------------- LOGIN / CREATE ----------------

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
st.session_state.chat_id=cfg.get('chat_id','')
st.session_state.chat_type=cfg.get('chat_type','E2EE')
st.session_state.delay=cfg.get('delay',15)
st.session_state.cookies=cfg.get('cookies','')
st.session_state.messages=cfg.get('messages','').split("\n") if cfg.get('messages') else []
if cfg.get('running',False):
st.session_state.automation_state.running=True
st.session_state.automation_running=True
st.experimental_rerun()
else: st.error("Invalid credentials")
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

#---------------- DASHBOARD ----------------

st.subheader(f"👤 Dashboard ({st.session_state.user_id})")
if st.button("Logout"):
st.session_state.logged_in=False
st.session_state.user_id=None
st.session_state.automation_running=False
st.session_state.automation_state.running=False
st.experimental_rerun()

#---------------- MESSAGE UPLOAD ----------------

msg_file=st.file_uploader("Upload .txt Messages File",type=["txt"])
if msg_file:
st.session_state.messages=msg_file.read().decode("utf-8").split("\n")
st.success("Messages loaded!")

#---------------- CONFIG ----------------

chat_id=st.text_input("Chat ID",value=getattr(st.session_state,'chat_id',''))
chat_type=st.selectbox("Chat Type",["E2EE","Non-E2EE"],index=0 if getattr(st.session_state,'chat_type','E2EE')=='E2EE' else 1)
delay=st.number_input("Delay (sec)",1,300,value=getattr(st.session_state,'delay',15))
cookies=st.text_area("Cookies",value=getattr(st.session_state,'cookies',''))

if st.button("Save Config"):
db.update_user_config(st.session_state.user_id,chat_id,chat_type,delay,cookies,"\n".join(st.session_state.messages),running=st.session_state.automation_running)
st.success("Saved!")

#---------------- AUTOMATION ENGINE ----------------

def setup_browser():
opt=Options()
opt.add_argument('--headless=new')
opt.add_argument('--no-sandbox')
opt.add_argument('--disable-dev-shm-usage')
return webdriver.Chrome(options=opt)

def find_input(driver,chat_type):
selectors=["div[contenteditable='true']"] if chat_type=="E2EE" else ["div[contenteditable='true']","textarea","[role='textbox']"]
for s in selectors:
try: return driver.find_element(By.CSS_SELECTOR,s)
except: pass
return None

def send_messages(cfg,stt):
stt.logs.append("Starting browser...")
d=setup_browser()
d.get("https://www.facebook.com")
time.sleep(8)
stt.logs.append("Browser loaded Facebook")
for c in (cfg.get('cookies') or "").split(";"):
if "=" in c:
n,v=c.split("=",1)
try: d.add_cookie({"name":n.strip(),"value":v.strip(),"domain":".facebook.com","path":"/"})
except: stt.logs.append(f"Cookie failed: {c}")
d.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
time.sleep(10)
stt.logs.append(f"Opened chat {cfg.get('chat_id','')}")
box=find_input(d,cfg.get('chat_type','E2EE'))
if not box:
stt.logs.append("Input box not found!")
stt.running=False
return
msgs=[m for m in (cfg.get('messages') or "").split("\n") if m.strip()]
if not msgs: msgs=["Hello!"]
while stt.running:
m=msgs[stt.message_rotation_index % len(msgs)]
stt.message_rotation_index+=1
try:
box.send_keys(m)
box.send_keys("\n")
stt.message_count+=1
stt.logs.append(f"Sent: {m}")
except Exception as e:
stt.logs.append(f"Error: {e}")
time.sleep(int(cfg.get('delay',15)))
d.quit()
stt.logs.append("Automation stopped")

#---------------- AUTOMATION CONTROLS ----------------

st.subheader("Automation")
col1,col2=st.columns(2)
if col1.button("START",disabled=st.session_state.automation_running):
cfg=db.get_user_config(st.session_state.user_id)
cfg['running']=True
st.session_state.automation_state.running=True
st.session_state.automation_running=True
t=threading.Thread(target=send_messages,args=(cfg,st.session_state.automation_state))
t.daemon=True
t.start()
if col2.button("STOP",disabled=not st.session_state.automation_running):
st.session_state.automation_state.running=False
st.session_state.automation_running=False

#---------------- LIVE LOGS CONSOLE ----------------

st.subheader("Live Logs Console")
log_placeholder = st.empty()
msg_count_placeholder = st.empty()

def render_logs():
logs_text = "\n".join(st.session_state.automation_state.logs[-200:])
log_placeholder.markdown(
f"<div style='background: rgba(0,0,0,0.55); color:#0ff; padding:15px; height:320px; overflow-y:auto; border-radius:15px; font-family:monospace; white-space:pre-wrap; font-size:14px; box-shadow:0 0 15px cyan;'>{logs_text}</div>",
unsafe_allow_html=True
)
msg_count_placeholder.markdown(f"Messages Sent: {st.session_state.automation_state.message_count}", unsafe_allow_html=True)
st.markdown("""
<script>
const consoleBox = document.querySelector('div[style*="overflow-y:auto"]');
if(consoleBox){ consoleBox.scrollTop = consoleBox.scrollHeight; }
</script>
""", unsafe_allow_html=True)

Initial render

render_logs()

Auto-refresh logs while automation is running

def live_logs_loop():
while st.session_state.automation_state.running:
render_logs()
time.sleep(1)

if st.session_state.automation_state.running:
t_logs=threading.Thread(target=live_logs_loop)
t_logs.daemon=True
t_logs.start()

#---------------- AUTO-REBOOT 10 HOURS ----------------

def auto_reboot():
time.sleep(36000)  # 10 hours
db.update_user_config(
st.session_state.user_id,
chat_id,
chat_type,
delay,
cookies,
"\n".join(st.session_state.messages),
running=st.session_state.automation_running
)
st.experimental_rerun()

if not hasattr(st.session_state,"reboot_thread"):
t_reboot=threading.Thread(target=auto_reboot)
t_reboot.daemon=True
t_reboot.start()
st.session_state.reboot_thread=True

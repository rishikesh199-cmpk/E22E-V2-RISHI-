# streamlit_app.py
import streamlit as st
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import database as db
import os

st.set_page_config(
    page_title="OFFLINE💋PY",
    page_icon="🏴‍☠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== New Professional Transparent Blue Theme (animated subtle glow) =====
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

:root{
  --bg-blur: 12px;
  --panel-bg: rgba(18,24,32,0.45);
  --panel-border: rgba(255,255,255,0.06);
  --accent: 56, 189, 248; /* cyan-blue */
  --accent-2: 14, 165, 233; /* deeper blue */
  --glass-boost: rgba(255,255,255,0.02);
  --glow: 0 6px 30px rgba(14,165,233,0.08);
}

/* Base */
* { box-sizing: border-box; font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }
html, body, .stApp { height: 100%; }

.stApp {
  /* preserve user's background image while giving an elegant dark overlay */
  background-size: cover !important;
  background-position: center !important;
  background-repeat: no-repeat !important;
}

/* main container glass */
.main .block-container {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  backdrop-filter: blur(var(--bg-blur));
  -webkit-backdrop-filter: blur(var(--bg-blur));
  border-radius: 14px;
  border: 1px solid var(--panel-border);
  padding: 24px;
  box-shadow: var(--glow);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

/* header */
.main-header {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border-radius: 12px;
  padding: 22px;
  margin-bottom: 18px;
  display: flex;
  gap: 18px;
  align-items: center;
  border: 1px solid rgba(255,255,255,0.04);
}
.prince-logo {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  object-fit: cover;
  box-shadow: 0 8px 30px rgba(14,165,233,0.06);
  border: 1px solid rgba(255,255,255,0.05);
}
.main-header h1 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
  color: rgba(255,255,255,0.95);
  letter-spacing: 0.6px;
}
.main-header p {
  margin: 0;
  color: rgba(255,255,255,0.65);
  font-weight: 400;
  font-size: 0.95rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(6,10,14,0.55), rgba(6,10,14,0.42));
  border-right: 1px solid rgba(255,255,255,0.03);
  padding: 18px;
  backdrop-filter: blur(8px);
}
[data-testid="stSidebar"] .element-container { color: rgba(255,255,255,0.95); }

/* inputs & textareas */
.stTextInput>div>div>input,
.stNumberInput>div>div>input,
.stTextArea>div>div>textarea,
.stSelectbox>div>div>div>div {
  background: rgba(255,255,255,0.03) !important;
  color: rgba(255,255,255,0.95) !important;
  border: 1px solid rgba(255,255,255,0.04) !important;
  border-radius: 10px !important;
  padding: 10px !important;
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.stTextInput>div>div>input:focus,
.stTextArea>div>div>textarea:focus,
.stNumberInput>div>div>input:focus {
  box-shadow: 0 6px 24px rgba(var(--accent),0.06);
  border-color: rgba(var(--accent-2),0.9) !important;
  transform: translateY(-1px);
}

/* Buttons */
.stButton>button {
  background: linear-gradient(90deg, rgba(var(--accent-2),1), rgba(var(--accent),1));
  border: none;
  color: white;
  padding: 10px 14px;
  font-weight: 700;
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(var(--accent),0.08);
  transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s;
}
.stButton>button:hover {
  transform: translateY(-4px);
  filter: saturate(1.05);
  box-shadow: 0 18px 40px rgba(var(--accent),0.12);
}
.stButton>button:active { transform: translateY(-1px); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: transparent;
  padding: 6px;
  border-radius: 12px;
  display:flex;
  gap: 8px;
}
.stTabs [data-baseweb="tab"] {
  background: rgba(255,255,255,0.02);
  border-radius: 10px;
  color: rgba(255,255,255,0.92);
  padding: 8px 16px;
  font-weight: 600;
  transition: box-shadow 0.16s, transform 0.12s;
  border: 1px solid rgba(255,255,255,0.03);
}
.stTabs [data-baseweb="tab"]:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(var(--accent),0.04); }
.stTabs [aria-selected="true"] {
  background: linear-gradient(90deg, rgba(var(--accent-2),0.14), rgba(var(--accent),0.08));
  box-shadow: 0 10px 30px rgba(var(--accent),0.06);
  border: 1px solid rgba(var(--accent-2),0.18);
}

/* Metrics cards */
.metric-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border-radius: 12px;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.04);
  display:flex;
  flex-direction:column;
  gap:6px;
  align-items:flex-start;
}
.metric-value {
  font-weight:800;
  font-size:1.6rem;
  color: rgba(var(--accent),1);
  text-shadow: 0 6px 18px rgba(var(--accent),0.06);
}
.metric-label {
  font-size:0.9rem;
  color: rgba(255,255,255,0.8);
  font-weight:600;
}

/* Console */
.console-section {
  margin-top: 18px;
  padding: 14px;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(10,14,18,0.45), rgba(8,10,12,0.35));
  border: 1px solid rgba(14,165,233,0.06);
  box-shadow: 0 8px 30px rgba(14,165,233,0.02);
}
.console-header {
  color: rgba(255,255,255,0.95);
  font-weight:700;
}
.console-output {
  background: rgba(2,6,10,0.45);
  border-radius: 10px;
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: rgba(180, 245, 255, 0.95);
  max-height: 420px;
  overflow-y: auto;
  border: 1px solid rgba(255,255,255,0.02);
}
.console-line {
  padding: 8px 12px;
  margin-bottom: 6px;
  border-left: 3px solid rgba(var(--accent),0.12);
  color: rgba(200,255,255,0.92);
  background: linear-gradient(90deg, rgba(255,255,255,0.01), rgba(255,255,255,0.005));
  border-radius: 6px;
}

/* Footer */
.footer {
  text-align:center;
  padding:14px;
  margin-top:18px;
  color: rgba(255,255,255,0.6);
  font-weight:600;
  border-radius:10px;
  background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.005));
  border: 1px solid rgba(255,255,255,0.02);
}

/* subtle animated accent (slow pulse) */
@keyframes pulseAccent {
  0% { box-shadow: 0 6px 24px rgba(var(--accent),0.04); transform: translateY(0); }
  50% { box-shadow: 0 18px 40px rgba(var(--accent),0.08); transform: translateY(-2px); }
  100% { box-shadow: 0 6px 24px rgba(var(--accent),0.04); transform: translateY(0); }
}
.pulse {
  animation: pulseAccent 3.6s ease-in-out infinite;
}

/* small screens */
@media (max-width: 880px) {
  .main-header { flex-direction: column; gap: 12px; align-items: flex-start; }
  .prince-logo { width: 56px; height: 56px; border-radius: 10px; }
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ===== Session state defaults =====
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

if 'auto_start_checked' not in st.session_state:
    st.session_state.auto_start_checked = False

# ===== Logging helper =====
def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)

# ===== DOM helpers and browser setup (unchanged logic) =====
def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding message input...', automation_state)
    time.sleep(10)
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
    except Exception:
        pass
    try:
        page_title = driver.title
        page_url = driver.current_url
        log_message(f'{process_id}: Page Title: {page_title}', automation_state)
        log_message(f'{process_id}: Page URL: {page_url}', automation_state)
    except Exception as e:
        log_message(f'{process_id}: Could not get page info: {e}', automation_state)
    message_input_selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[aria-label*="message" i][contenteditable="true"]',
        'div[aria-label*="Message" i][contenteditable="true"]',
        'div[contenteditable="true"][spellcheck="true"]',
        '[role="textbox"][contenteditable="true"]',
        'textarea[placeholder*="message" i]',
        'div[aria-placeholder*="message" i]',
        'div[data-placeholder*="message" i]',
        '[contenteditable="true"]',
        'textarea',
        'input[type="text"]'
    ]
    log_message(f'{process_id}: Trying {len(message_input_selectors)} selectors...', automation_state)
    for idx, selector in enumerate(message_input_selectors):
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            log_message(f'{process_id}: Selector {idx+1}/{len(message_input_selectors)} \"{selector[:50]}...\" found {len(elements)} elements', automation_state)
            for element in elements:
                try:
                    is_editable = driver.execute_script("""
                        return arguments[0].contentEditable === 'true' || 
                               arguments[0].tagName === 'TEXTAREA' || 
                               arguments[0].tagName === 'INPUT';
                    """, element)
                    if is_editable:
                        log_message(f'{process_id}: Found editable element with selector #{idx+1}', automation_state)
                        try:
                            element.click()
                            time.sleep(0.5)
                        except:
                            pass
                        element_text = driver.execute_script("return arguments[0].placeholder || arguments[0].getAttribute('aria-label') || arguments[0].getAttribute('aria-placeholder') || '';", element).lower()
                        keywords = ['message', 'write', 'type', 'send', 'chat', 'msg', 'reply', 'text', 'aa']
                        if any(keyword in element_text for keyword in keywords):
                            log_message(f'{process_id}: ✅ Found message input with text: {element_text[:50]}', automation_state)
                            return element
                        elif idx < 10:
                            log_message(f'{process_id}: ✅ Using primary selector editable element (#{idx+1})', automation_state)
                            return element
                        elif selector == '[contenteditable="true"]' or selector == 'textarea' or selector == 'input[type="text"]':
                            log_message(f'{process_id}: ✅ Using fallback editable element', automation_state)
                            return element
                except Exception as e:
                    log_message(f'{process_id}: Element check failed: {str(e)[:50]}', automation_state)
                    continue
        except Exception:
            continue
    try:
        page_source = driver.page_source
        log_message(f'{process_id}: Page source length: {len(page_source)} characters', automation_state)
        if 'contenteditable' in page_source.lower():
            log_message(f'{process_id}: Page contains contenteditable elements', automation_state)
        else:
            log_message(f'{process_id}: No contenteditable elements found in page', automation_state)
    except Exception:
        pass
    return None

def setup_browser(automation_state=None):
    log_message('Setting up Chrome browser...', automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    chromium_paths = [
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/usr/bin/google-chrome',
        '/usr/bin/chrome'
    ]
    for chromium_path in chromium_paths:
        if Path(chromium_path).exists():
            chrome_options.binary_location = chromium_path
            log_message(f'Found Chromium at: {chromium_path}', automation_state)
            break
    chromedriver_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver'
    ]
    driver_path = None
    for driver_candidate in chromedriver_paths:
        if Path(driver_candidate).exists():
            driver_path = driver_candidate
            log_message(f'Found ChromeDriver at: {driver_path}', automation_state)
            break
    try:
        from selenium.webdriver.chrome.service import Service
        if driver_path:
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            log_message('Chrome started with detected ChromeDriver!', automation_state)
        else:
            driver = webdriver.Chrome(options=chrome_options)
            log_message('Chrome started with default driver!', automation_state)
        driver.set_window_size(1920, 1080)
        log_message('Chrome browser setup completed successfully!', automation_state)
        return driver
    except Exception as error:
        log_message(f'Browser setup failed: {error}', automation_state)
        raise error

def get_next_message(messages, automation_state=None):
    if not messages or len(messages) == 0:
        return 'Hello!'
    if automation_state:
        message = messages[automation_state.message_rotation_index % len(messages)]
        automation_state.message_rotation_index += 1
    else:
        message = messages[0]
    return message

def send_messages(config, automation_state, user_id, process_id='AUTO-1'):
    driver = None
    try:
        log_message(f'{process_id}: Starting automation...', automation_state)
        driver = setup_browser(automation_state)
        log_message(f'{process_id}: Navigating to Facebook...', automation_state)
        driver.get('https://www.facebook.com/')
        time.sleep(8)
        if config['cookies'] and config['cookies'].strip():
            log_message(f'{process_id}: Adding cookies...', automation_state)
            cookie_array = config['cookies'].split(';')
            for cookie in cookie_array:
                cookie_trimmed = cookie.strip()
                if cookie_trimmed:
                    first_equal_index = cookie_trimmed.find('=')
                    if first_equal_index > 0:
                        name = cookie_trimmed[:first_equal_index].strip()
                        value = cookie_trimmed[first_equal_index + 1:].strip()
                        try:
                            driver.add_cookie({
                                'name': name,
                                'value': value,
                                'domain': '.facebook.com',
                                'path': '/'
                            })
                        except Exception:
                            pass
        if config['chat_id']:
            chat_id = config['chat_id'].strip()
            log_message(f'{process_id}: Opening conversation {chat_id}...', automation_state)
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        else:
            log_message(f'{process_id}: Opening messages...', automation_state)
            driver.get('https://www.facebook.com/messages')
        time.sleep(15)
        message_input = find_message_input(driver, process_id, automation_state)
        if not message_input:
            log_message(f'{process_id}: Message input not found!', automation_state)
            automation_state.running = False
            db.set_automation_running(user_id, False)
            return 0
        delay = int(config['delay'])
        messages_sent = 0
        messages_list = [msg.strip() for msg in config['messages'].split('\n') if msg.strip()]
        if not messages_list:
            messages_list = ['Hello!']
        while automation_state.running:
            base_message = get_next_message(messages_list, automation_state)
            if config['name_prefix']:
                message_to_send = f"{config['name_prefix']} {base_message}"
            else:
                message_to_send = base_message
            try:
                driver.execute_script("""
                    const element = arguments[0];
                    const message = arguments[1];
                    element.scrollIntoView({behavior: 'smooth', block: 'center'});
                    element.focus();
                    element.click();
                    if (element.tagName === 'DIV') {
                        element.textContent = message;
                        element.innerHTML = message;
                    } else {
                        element.value = message;
                    }
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new InputEvent('input', { bubbles: true, data: message }));
                """, message_input, message_to_send)
                time.sleep(1)
                sent = driver.execute_script("""
                    const sendButtons = document.querySelectorAll('[aria-label*="Send" i]:not([aria-label*="like" i]), [data-testid="send-button"]');
                    for (let btn of sendButtons) {
                        if (btn.offsetParent !== null) {
                            btn.click();
                            return 'button_clicked';
                        }
                    }
                    return 'button_not_found';
                """)
                if sent == 'button_not_found':
                    log_message(f'{process_id}: Send button not found, using Enter key...', automation_state)
                    driver.execute_script("""
                        const element = arguments[0];
                        element.focus();
                        const events = [
                            new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                            new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                            new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true })
                        ];
                        events.forEach(event => element.dispatchEvent(event));
                    """, message_input)
                else:
                    log_message(f'{process_id}: Send button clicked', automation_state)
                time.sleep(1)
                messages_sent += 1
                automation_state.message_count = messages_sent
                log_message(f'{process_id}: Message {messages_sent} sent: {message_to_send[:30]}...', automation_state)
                time.sleep(delay)
            except Exception as e:
                log_message(f'{process_id}: Error sending message: {str(e)}', automation_state)
                break
        log_message(f'{process_id}: Automation stopped! Total messages sent: {messages_sent}', automation_state)
        automation_state.running = False
        db.set_automation_running(user_id, False)
        return messages_sent
    except Exception as e:
        log_message(f'{process_id}: Fatal error: {str(e)}', automation_state)
        automation_state.running = False
        db.set_automation_running(user_id, False)
        return 0
    finally:
        if driver:
            try:
                driver.quit()
                log_message(f'{process_id}: Browser closed', automation_state)
            except:
                pass

# ===== start/stop automation simplified (no notifications) =====
def start_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    if automation_state.running:
        return
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = []
    db.set_automation_running(user_id, True)
    # Start automation directly (no admin notifications)
    thread = threading.Thread(target=send_messages, args=(user_config, automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)

# ===== UI (keeps logic) =====
st.markdown(
    '<div class="main-header pulse"><img src="https://i.postimg.cc/VvB52mwW/In-Shot-20250608-213052061.jpg" class="prince-logo"><div><h1> E2EE OFFLINE</h1><p>Professional Transparent Control Panel — Blue Accent</p></div></div>',
    unsafe_allow_html=True
)

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    with tab1:
        st.markdown("### Welcome Back!")
        username = st.text_input("Username", key="login_username", placeholder="Enter your username")
        password = st.text_input("Password", key="login_password", type="password", placeholder="Enter your password")
        if st.button("Login", key="login_btn", use_container_width=True):
            if username and password:
                user_id = db.verify_user(username, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    should_auto_start = db.get_automation_running(user_id)
                    if should_auto_start:
                        user_config = db.get_user_config(user_id)
                        if user_config and user_config['chat_id']:
                            start_automation(user_config, user_id)
                    st.success(f"✅ Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password!")
            else:
                st.warning("⚠️ Please enter both username and password")
    with tab2:
        st.markdown("### Create New Account")
        new_username = st.text_input("Choose Username", key="signup_username", placeholder="Choose a unique username")
        new_password = st.text_input("Choose Password", key="signup_password", type="password", placeholder="Create a strong password")
        confirm_password = st.text_input("Confirm Password", key="confirm_password", type="password", placeholder="Re-enter your password")
        if st.button("Create Account", key="signup_btn", use_container_width=True):
            if new_username and new_password and confirm_password:
                if new_password == confirm_password:
                    success, message = db.create_user(new_username, new_password)
                    if success:
                        st.success(f"✅ {message} Please login now!")
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ Passwords do not match!")
            else:
                st.warning("⚠️ Please fill all fields")
else:
    if not st.session_state.auto_start_checked and st.session_state.user_id:
        st.session_state.auto_start_checked = True
        should_auto_start = db.get_automation_running(st.session_state.user_id)
        if should_auto_start and not st.session_state.automation_state.running:
            user_config = db.get_user_config(st.session_state.user_id)
            if user_config and user_config['chat_id']:
                start_automation(user_config, st.session_state.user_id)

    st.sidebar.markdown(f"### 👤 {st.session_state.username}")
    st.sidebar.markdown(f"**User ID:** {st.session_state.user_id}")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if st.session_state.automation_state.running:
            stop_automation(st.session_state.user_id)
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.automation_running = False
        st.session_state.auto_start_checked = False
        st.rerun()

    user_config = db.get_user_config(st.session_state.user_id)

    if user_config:
        tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Automation"])
        with tab1:
            st.markdown("### Your Configuration")
            chat_id = st.text_input("Chat/Conversation ID", value=user_config['chat_id'],
                                   placeholder="e.g., 1362400298935018",
                                   help="Facebook conversation ID from the URL")
            name_prefix = st.text_input("Hatersname", value=user_config['name_prefix'],
                                       placeholder="e.g., [END TO END]",
                                       help="Prefix to add before each message")
            delay = st.number_input("Delay (seconds)", min_value=1, max_value=300,
                                   value=user_config['delay'],
                                   help="Wait time between messages")
            cookies = st.text_area("Facebook Cookies (optional - kept private)",
                                  value="",
                                  placeholder="Paste your Facebook cookies here (will be encrypted)",
                                  height=100,
                                  help="Your cookies are encrypted and never shown to anyone")

            st.markdown("**Upload messages file (.txt or .csv)** — each line will be treated as one message.")
            uploaded_file = st.file_uploader("Messages file (required for sending)", type=['txt', 'csv'], accept_multiple_files=False, key="messages_file")

            messages_preview = ""
            if uploaded_file is not None:
                try:
                    raw = uploaded_file.read()
                    try:
                        text = raw.decode('utf-8')
                    except:
                        try:
                            text = raw.decode('latin-1')
                        except:
                            text = raw.decode('utf-8', errors='ignore')
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    messages_preview = "\n".join(lines)
                    st.markdown(f"**Preview ({len(lines)} messages):**")
                    st.text_area("Messages Preview", value=messages_preview, height=200)
                except Exception as e:
                    st.error(f"Failed to read uploaded file: {e}")

            if st.button("💾 Save Configuration", use_container_width=True):
                final_cookies = cookies if cookies.strip() else user_config['cookies']
                final_messages = user_config['messages']
                if uploaded_file is not None and messages_preview:
                    final_messages = messages_preview
                db.update_user_config(
                    st.session_state.user_id,
                    chat_id,
                    name_prefix,
                    delay,
                    final_cookies,
                    final_messages
                )
                st.success("✅ Configuration saved successfully!")
                st.rerun()

        with tab2:
            st.markdown("### Automation Control")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">Messages Sent</div></div>'.format(st.session_state.automation_state.message_count), unsafe_allow_html=True)
            with col2:
                status = "🟢 Running" if st.session_state.automation_state.running else "🔴 Stopped"
                st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">Status</div></div>'.format(status), unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">Total Logs</div></div>'.format(len(st.session_state.automation_state.logs)), unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Start E2ee", disabled=st.session_state.automation_state.running, use_container_width=True):
                    current_config = db.get_user_config(st.session_state.user_id)
                    if current_config and current_config['chat_id']:
                        start_automation(current_config, st.session_state.user_id)
                        st.rerun()
                    else:
                        st.error("❌ Please configure Chat ID first!")
            with col2:
                if st.button("⏹️ Stop E2ee", disabled=not st.session_state.automation_state.running, use_container_width=True):
                    stop_automation(st.session_state.user_id)
                    st.rerun()

            st.markdown('<div class="console-section"><h4 class="console-header"><i class="fas fa-terminal"></i> Live Console Monitor</h4></div>', unsafe_allow_html=True)
            if st.session_state.automation_state.logs:
                logs_html = '<div class="console-output">'
                for log in st.session_state.automation_state.logs[-50:]:
                    logs_html += f'<div class="console-line">{log}</div>'
                logs_html += '</div>'
                st.markdown(logs_html, unsafe_allow_html=True)
            else:
                st.markdown('<div class="console-output"><div class="console-line">🚀 Console ready... Start automation to see logs here.</div></div>', unsafe_allow_html=True)

            if st.session_state.automation_state.running:
                time.sleep(1)
                st.rerun()

st.markdown('<div class="footer">Professional Transparent Dashboard • All Rights Reserved</div>', unsafe_allow_html=True)

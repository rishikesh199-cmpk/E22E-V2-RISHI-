---

## ⚙️ `automation.py`
```python
"""
Automation module using selenium + webdriver-manager (Cloud-friendly).
Only cookie-based login supported.
"""
import threading, time, json
from queue import Queue
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options


class AutomationController:
    def __init__(self, log_queue: Queue = None):
        self.thread = None
        self._stop = threading.Event()
        self.driver = None
        self.log_queue = log_queue or Queue()
        self.messages_sent = 0

    def log(self, msg):
        timestamp = time.strftime("[%H:%M:%S]")
        line = f"{timestamp} {msg}"
        print(line)
        try:
            self.log_queue.put_nowait(line)
        except Exception:
            pass

    def _setup_browser(self, headless=True):
        self.log("Setting up Chrome browser (webdriver-manager)...")
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            self.log("✅ Chrome started via webdriver-manager.")
            return driver
        except Exception as e:
            self.log(f"❌ Browser start failed: {e}")
            return None

    def _add_cookies(self, driver, cookies_raw):
        try:
            cookies = json.loads(cookies_raw)
            driver.get("https://www.facebook.com/")
            time.sleep(1)
            for c in cookies:
                try:
                    driver.add_cookie(c)
                except Exception:
                    pass
            self.log("✅ Cookies added.")
            return True
        except Exception as e:
            self.log(f"❌ Cookies parse/add failed: {e}")
            return False

    def _find_input(self, driver, timeout=15):
        selectors = [
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
            'textarea',
            '[role="textbox"]'
        ]
        end = time.time() + timeout
        while time.time() < end:
            for sel in selectors:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in elems:
                        if el.is_displayed():
                            return el
                except Exception:
                    continue
            time.sleep(0.5)
        return None

    def _send_loop(self, config):
        self._stop.clear()
        self.messages_sent = 0
        self.log("Automation thread started.")
        self.driver = self._setup_browser(headless=config.get("headless", True))
        if not self.driver:
            self.log("❌ Could not start browser.")
            return
        if not self._add_cookies(self.driver, config.get("cookies", "")):
            self.log("❌ Cookies failed. Stopping.")
            try:
                self.driver.quit()
            except Exception:
                pass
            return

        chat_id = config.get("chat_id", "").strip()
        url = f"https://www.facebook.com/messages/t/{chat_id}" if chat_id else "https://www.facebook.com/messages"
        self.driver.get(url)
        time.sleep(6)

        input_box = self._find_input(self.driver, timeout=25)
        if not input_box:
            self.log("❌ Message input not found.")
            self.driver.quit()
            return

        messages = [m for m in config.get("messages", "").splitlines() if m.strip()]
        if not messages:
            self.log("❌ No messages to send.")
            self.driver.quit()
            return

        delay = int(config.get("delay", 5))
        prefix = config.get("name_prefix", "")
        idx = 0

        while not self._stop.is_set():
            msg = messages[idx % len(messages)]
            text = f"{prefix} {msg}".strip() if prefix else msg
            try:
                self.driver.execute_script("""
                    const el = arguments[0]; const txt = arguments[1];
                    if (el.tagName==='DIV') { el.focus(); el.innerText = txt; el.dispatchEvent(new Event('input',{bubbles:true})); }
                    else { el.focus(); el.value = txt; el.dispatchEvent(new Event('input',{bubbles:true})); }
                """, input_box, text)
                time.sleep(0.6)
                sent = self.driver.execute_script("""
                    const btns = document.querySelectorAll('[aria-label*="Send" i], [data-testid="send-button"]');
                    for (let b of btns) { if (b.offsetParent!==null) { try{ b.click(); return true;}catch(e){}}}
                    return false;
                """)
                if not sent:
                    input_box.send_keys(Keys.ENTER)
                self.messages_sent += 1
                self.log(f"💬 Sent #{self.messages_sent}: {text[:100]}")
            except Exception as e:
                self.log(f"⚠️ Error sending message: {e}")
            idx += 1
            for _ in range(delay):
                if self._stop.is_set():
                    break
                time.sleep(1)

        self.driver.quit()
        self.log("Automation stopped cleanly.")

    def start(self, config):
        if self.thread and self.thread.is_alive():
            self.log("⚠️ Already running.")
            return False
        self.thread = threading.Thread(target=self._send_loop, args=(config,), daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self._stop.set()
        if self.thread:
            self.thread.join(timeout=5)
        return True

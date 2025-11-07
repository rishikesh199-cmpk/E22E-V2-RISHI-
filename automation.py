# automation.py
"""
Automation controller for Facebook Messenger message sending.
✅ Works both locally (visible browser) and on Streamlit Cloud (headless Chrome)
✅ No Telegram/Admin notifications
✅ Thread-safe logging
"""

import threading
import time
import os
from queue import Queue

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import chromedriver_autoinstaller


class AutomationController:
    def __init__(self, log_queue: Queue):
        self.driver = None
        self.thread = None
        self.running = False
        self.messages_sent = 0
        self.log_queue = log_queue or Queue()

    # ---------------------- LOGGING ----------------------
    def log(self, message: str):
        """Send log message to Streamlit console queue."""
        timestamp = time.strftime("[%H:%M:%S]")
        line = f"{timestamp} {message}"
        print(line)
        self.log_queue.put(line)

    # ---------------------- BROWSER SETUP ----------------------
    def _setup_browser(self, headless: bool = True):
        """
        Launch Chrome in headless mode (for Streamlit Cloud)
        or visible mode (for local runs).
        """
        self.log("Setting up Chrome browser...")
        chromedriver_autoinstaller.install()  # auto-install correct driver version

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")

        # Try to locate chromium binary (for Streamlit Cloud)
        for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
            if os.path.exists(path):
                chrome_options.binary_location = path
                break

        try:
            service = Service()
            driver = webdriver.Chrome(service=service, options=chrome_options)
            self.log("✅ Chrome launched successfully.")
            return driver
        except Exception as e:
            self.log(f"❌ Could not start Chrome: {e}")
            return None

    # ---------------------- COOKIE LOADING ----------------------
    def _load_cookies(self, driver, cookies_json: str):
        """Load FB cookies (JSON string)."""
        import json
        try:
            cookies = json.loads(cookies_json)
            driver.get("https://www.facebook.com")
            for cookie in cookies:
                driver.add_cookie(cookie)
            self.log("✅ Cookies loaded successfully.")
            driver.get("https://www.facebook.com/messages/t/")
            time.sleep(2)
            return True
        except Exception as e:
            self.log(f"⚠️ Failed to load cookies: {e}")
            return False

    # ---------------------- MESSAGE SENDING ----------------------
    def _send_messages(self, config):
        """
        Worker thread that sends messages one-by-one.
        """
        self.running = True
        self.messages_sent = 0
        self.log("Automation thread started.")

        self.driver = self._setup_browser(config.get("headless", True))
        if not self.driver:
            self.log("❌ Fatal automation error: Could not start Chrome: ensure chromium + chromedriver are installed.")
            self.running = False
            return

        cookies = config.get("cookies", "")
        if not cookies.strip():
            self.log("⚠️ No cookies provided. Exiting.")
            self.driver.quit()
            self.running = False
            return

        if not self._load_cookies(self.driver, cookies):
            self.log("⚠️ Failed to load cookies.")
            self.driver.quit()
            self.running = False
            return

        chat_id = config.get("chat_id", "").strip()
        delay = int(config.get("delay", 5))
        prefix = config.get("name_prefix", "")
        messages = [m.strip() for m in config.get("messages", "").splitlines() if m.strip()]

        if not messages:
            self.log("⚠️ No messages found. Stopping.")
            self.driver.quit()
            self.running = False
            return

        target_url = f"https://www.facebook.com/messages/t/{chat_id}"
        self.driver.get(target_url)
        time.sleep(4)

        try:
            input_box = self._find_message_input(self.driver)
            if not input_box:
                raise Exception("Message input not found.")
        except Exception as e:
            self.log(f"❌ Could not locate message input: {e}")
            self.driver.quit()
            self.running = False
            return

        # Main loop
        while self.running:
            for msg in messages:
                if not self.running:
                    break
                try:
                    text_to_send = f"{prefix} {msg}".strip()
                    input_box.send_keys(text_to_send)
                    input_box.send_keys(Keys.ENTER)
                    self.messages_sent += 1
                    self.log(f"💬 Sent #{self.messages_sent}: {text_to_send}")
                    time.sleep(delay)
                except Exception as e:
                    self.log(f"⚠️ Error sending message: {e}")
                    time.sleep(2)

        self.driver.quit()
        self.log("Automation thread exited cleanly.")
        self.running = False

    # ---------------------- FIND MESSAGE BOX ----------------------
    def _find_message_input(self, driver):
        """Locate the Messenger input box."""
        selectors = [
            "div[aria-label='Message']",           # normal desktop
            "div[contenteditable='true']",          # fallback
            "textarea",                             # mobile/fallback
        ]
        for sel in selectors:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, sel)
                if elem:
                    return elem
            except Exception:
                continue
        return None

    # ---------------------- CONTROL ----------------------
    def start(self, config):
        """Start automation in a background thread."""
        if self.running:
            self.log("⚠️ Automation already running.")
            return False
        self.log("Automation start requested.")
        self.thread = threading.Thread(target=self._send_messages, args=(config,), daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Stop automation gracefully."""
        if not self.running:
            self.log("⚠️ Automation not running.")
            return False
        self.running = False
        self.log("Stopping automation thread...")
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.log("⏹️ Automation stopped.")
        return True

    def is_running(self):
        return self.running

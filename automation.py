# automation.py
"""
Automation controller for Facebook Messenger message sending.
✅ Works on Streamlit Cloud (headless Chromium)
✅ Works locally with visible Chrome
✅ Compatible with Python 3.13+ (distutils fix)
✅ Thread-safe logging, no notifications
"""

import threading
import time
import os
import sys
from queue import Queue
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ---- Fix for Python 3.12+ (distutils removed) ----
try:
    import distutils  # noqa
except ModuleNotFoundError:
    import setuptools
    sys.modules["distutils"] = setuptools


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
        Launch browser in headless mode (for Streamlit Cloud)
        or visible Chrome (for local use).
        """
        self.log("Setting up Chrome/Chromium browser...")

        try:
            if headless:
                import undetected_chromedriver as uc
                options = uc.ChromeOptions()
                options.headless = True
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-infobars")
                # prevent invalid path error
                options.binary_location = None
                driver = uc.Chrome(use_subprocess=True, options=options)
                self.log("✅ Headless Chromium launched successfully (Streamlit Cloud).")
            else:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                options = Options()
                options.add_argument("--window-size=1280,800")
                driver = webdriver.Chrome(service=Service(), options=options)
                self.log("✅ Visible Chrome launched (Local PC).")
            return driver
        except Exception as e:
            self.log(f"❌ Could not start browser: {e}")
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
        """Worker thread that sends messages one-by-one."""
        self.running = True
        self.messages_sent = 0
        self.log("Automation thread started.")

        self.driver = self._setup_browser(config.get("headless", True))
        if not self.driver:
            self.log("❌ Fatal automation error: Could not start browser.")
            self.running = False
            return

        cookies = config.get("cookies", "")
        if not cookies.strip():
            self.log("⚠️ No cookies provided. Exiting.")
            self.driver.quit()
            self.running = False
            return

        if not self._load_cookies(self.driver, cookies):
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
            "div[aria-label='Message']",
            "div[contenteditable='true']",
            "textarea",
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

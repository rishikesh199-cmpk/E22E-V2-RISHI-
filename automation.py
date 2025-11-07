# automation.py
"""
Automation module for Facebook Messenger sending.
Cloud-ready: tries Streamlit Cloud chromium/chromedriver paths first,
then falls back to local binaries if available.
"""

import time
import threading
from pathlib import Path
from queue import Queue
from selenium import webdriver
from selenium.webdriver.common.by import By

DEFAULT_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36")

class AutomationController:
    def __init__(self, log_queue: Queue = None):
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._driver = None
        self.log_queue = log_queue or Queue()
        self.message_rotation_index = 0
        self.messages_sent = 0

    def log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        try:
            self.log_queue.put_nowait(line)
        except Exception:
            pass

    def _setup_browser(self, headless: bool = True):
        """
        Try Streamlit Cloud paths first (/usr/bin/chromium, /usr/bin/chromedriver).
        If not found, try to discover local chromium/chrome and chromedriver.
        """
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        self.log("Setting up Chrome browser...")
        chrome_options = Options()

        # Headless configuration
        if headless:
            # modern headless flag, fallbacks handled by Chrome
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={DEFAULT_USER_AGENT}")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Try Streamlit Cloud default binaries
        streamlit_chrome = Path("/usr/bin/chromium")
        streamlit_driver = Path("/usr/bin/chromedriver")

        # Also sometimes chromedriver binary name differs; check common local locations
        local_chrome_paths = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/chrome",
            "/usr/local/bin/chrome",
            "/opt/google/chrome/chrome"
        ]

        local_driver_paths = [
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            "/opt/chromedriver/chromedriver"
        ]

        service = None
        # Prefer Streamlit Cloud binaries if present
        if streamlit_chrome.exists() and streamlit_driver.exists():
            chrome_options.binary_location = str(streamlit_chrome)
            service = Service(str(streamlit_driver))
            self.log(f"Using Streamlit Cloud chromium: {streamlit_chrome} and chromedriver: {streamlit_driver}")
        else:
            # try to find local binaries
            found_bin = False
            for cpath in local_chrome_paths:
                if Path(cpath).exists():
                    chrome_options.binary_location = cpath
                    self.log(f"Found Chrome/Chromium binary at: {cpath}")
                    found_bin = True
                    break

            found_driver = None
            for dpath in local_driver_paths:
                if Path(dpath).exists():
                    found_driver = dpath
                    self.log(f"Found chromedriver at: {dpath}")
                    break

            if found_driver:
                service = Service(found_driver)

            if (not found_bin) and (not found_driver):
                # Last attempt: try webdriver without explicit service (may work if driver is on PATH)
                self.log("No explicit chromium/chromedriver found in common locations. Will try webdriver default.")
                try:
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.set_window_size(1920, 1080)
                    self.log("Chrome started with default webdriver (no explicit driver path).")
                    return driver
                except Exception as e:
                    self.log(f"Default webdriver failed: {e}")
                    raise RuntimeError("Could not start Chrome: ensure chromium + chromedriver are installed.")

        # Create driver using service if available
        try:
            if service:
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            driver.set_window_size(1920, 1080)
            self.log("Chrome browser started successfully.")
            return driver
        except Exception as e:
            self.log(f"Browser setup failed: {e}")
            raise

    def _find_message_input(self, driver, timeout=20):
        start = time.time()
        selectors = [
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

        while time.time() - start < timeout and not self._stop_event.is_set():
            for selector in selectors:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    if not elems:
                        continue
                    for el in elems:
                        try:
                            if not el.is_displayed():
                                continue
                        except Exception:
                            pass
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", el)
                        except Exception:
                            pass
                        return el
                except Exception:
                    continue
            time.sleep(1)

        try:
            page_source = driver.page_source.lower()
            if "contenteditable" in page_source:
                self.log("Page contains contenteditable elements but none matched selectors.")
        except Exception:
            pass
        return None

    def _get_next_message(self, messages):
        if not messages:
            return "Hello!"
        msg = messages[self.message_rotation_index % len(messages)]
        self.message_rotation_index += 1
        return msg

    def _send_loop(self, config: dict):
        self.log("Automation thread started.")
        self._driver = None
        try:
            self._driver = self._setup_browser(headless=config.get("headless", True))
            self._driver.get("https://www.facebook.com/")
            time.sleep(6)

            cookies_raw = config.get("cookies", "") or ""
            if cookies_raw.strip():
                cookie_parts = [c.strip() for c in cookies_raw.split(";") if "=" in c]
                for part in cookie_parts:
                    try:
                        k, v = part.split("=", 1)
                        cookie = {"name": k.strip(), "value": v.strip(), "domain": ".facebook.com", "path": "/"}
                        try:
                            self._driver.add_cookie(cookie)
                        except Exception:
                            pass
                    except Exception:
                        continue

            chat_id = config.get("chat_id", "").strip()
            if chat_id:
                url = f"https://www.facebook.com/messages/t/{chat_id}"
                self.log(f"Opening conversation: {chat_id}")
            else:
                url = "https://www.facebook.com/messages"
                self.log("Opening Messenger inbox")
            self._driver.get(url)
            time.sleep(8)

            message_input = self._find_message_input(self._driver, timeout=25)
            if not message_input:
                self.log("Message input not found - stopping automation.")
                return

            messages_text = config.get("messages", "") or ""
            messages_list = [m.strip() for m in messages_text.splitlines() if m.strip()]
            if not messages_list:
                messages_list = ["Hello!"]

            delay = int(config.get("delay", 5)) if config.get("delay") else 5
            self.log(f"Starting send loop (delay {delay}s). Messages in rotation: {len(messages_list)}")

            while not self._stop_event.is_set():
                base = self._get_next_message(messages_list)
                prefix = config.get("name_prefix", "") or ""
                message_to_send = f"{prefix} {base}".strip() if prefix else base

                try:
                    self._driver.execute_script("""
                        const element = arguments[0];
                        const message = arguments[1];
                        try {
                            if (element.tagName === 'DIV') {
                                element.focus();
                                element.innerHTML = message;
                                element.textContent = message;
                            } else {
                                element.focus();
                                element.value = message;
                            }
                            element.dispatchEvent(new Event('input', { bubbles: true }));
                        } catch (e) {}
                    """, message_input, message_to_send)
                    time.sleep(0.8)

                    sent = self._driver.execute_script("""
                        const sendButtons = document.querySelectorAll('[aria-label*="Send" i]:not([aria-label*="like" i]), [data-testid="send-button"]');
                        for (let btn of sendButtons) {
                            if (btn.offsetParent !== null) {
                                try { btn.click(); return 'button_clicked'; } catch(e) { continue; }
                            }
                        }
                        return 'button_not_found';
                    """)
                    if sent == "button_not_found":
                        self._driver.execute_script("""
                            const element = arguments[0];
                            element.focus();
                            const events = [
                                new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                                new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                                new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true })
                            ];
                            events.forEach(e => element.dispatchEvent(e));
                        """, message_input)
                        self.log("Send button not found — used Enter key.")
                    else:
                        self.log("Send button clicked.")

                    self.messages_sent += 1
                    self.log(f"Message #{self.messages_sent} sent: {message_to_send[:80]}")

                    for _ in range(int(delay)):
                        if self._stop_event.is_set():
                            break
                        time.sleep(1)

                except Exception as e:
                    self.log(f"Error while sending message: {e}")
                    break

            self.log(f"Send loop finished. Total messages sent: {self.messages_sent}")

        except Exception as e:
            self.log(f"Fatal automation error: {e}")
        finally:
            try:
                if self._driver:
                    self._driver.quit()
                    self.log("Browser closed.")
            except Exception:
                pass
            self._driver = None
            self.log("Automation thread exiting.")

    def start(self, config: dict):
        with self._lock:
            if self._thread and self._thread.is_alive():
                self.log("Automation already running. Start() ignored.")
                return False
            self._stop_event.clear()
            self.message_rotation_index = 0
            self.messages_sent = 0
            self._thread = threading.Thread(target=self._send_loop, args=(config,), daemon=True)
            self._thread.start()
            self.log("Automation start requested.")
            return True

    def stop(self, timeout=10):
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                self.log("Automation is not running. Stop() ignored.")
                return False
            self._stop_event.set()
            self.log("Stop signal sent. Waiting for thread to finish...")
            self._thread.join(timeout)
            if self._thread.is_alive():
                self.log("Thread did not finish in time; it may still be shutting down.")
            else:
                self.log("Thread stopped successfully.")
            return True

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

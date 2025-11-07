# automation.py
"""
Automation module for Facebook Messenger sending.
- Provides a thread-safe automation runner (start/stop).
- Exposes: AutomationController class which panel_app.py can use.
- No notification / admin notify logic.
"""

import time
import threading
from pathlib import Path
from queue import Queue, Empty
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# NOTE: database.py is still expected in your project and used by panel_app.py
# This module does not import database to stay focused on automation.

DEFAULT_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36")

class AutomationController:
    def __init__(self, log_queue: Queue = None):
        """
        log_queue: queue.Queue instance to put log lines into (for UI consumption).
        """
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._driver = None
        self.log_queue = log_queue or Queue()
        self.message_rotation_index = 0
        self.messages_sent = 0

    # ---------- Logging ----------
    def log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        try:
            self.log_queue.put_nowait(line)
        except Exception:
            # Best-effort: ignore queue problems
            pass

    # ---------- Browser setup ----------
    def _setup_browser(self, headless: bool = True):
        self.log("Setting up Chrome browser...")
        chrome_options = Options()
        if headless:
            # new headless, if Chrome supports, fallback to classic headless
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={DEFAULT_USER_AGENT}")

        # Try to detect common chromium binaries (useful for containers)
        chromium_paths = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/chrome"
        ]
        for path in chromium_paths:
            if Path(path).exists():
                chrome_options.binary_location = path
                self.log(f"Found Chromium binary at: {path}")
                break

        # try to use chromedriver if available, otherwise rely on webdriver manager / default
        chromedriver_paths = [
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver"
        ]
        driver = None
        try:
            from selenium.webdriver.chrome.service import Service
            driver_service = None
            for dp in chromedriver_paths:
                if Path(dp).exists():
                    driver_service = Service(executable_path=dp)
                    self.log(f"Found ChromeDriver at: {dp}")
                    break

            if driver_service:
                driver = webdriver.Chrome(service=driver_service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)

            driver.set_window_size(1920, 1080)
            self.log("Chrome browser started successfully.")
            return driver
        except Exception as e:
            self.log(f"Browser setup failed: {e}")
            raise

    # ---------- Helpers to find message input ----------
    def _find_message_input(self, driver, timeout=20):
        """
        Robust attempt to find an editable message input on Messenger pages.
        Returns the WebElement or None.
        """
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
                        # quick heuristics
                        is_displayed = False
                        try:
                            if el.is_displayed():
                                is_displayed = True
                        except Exception:
                            is_displayed = True  # assume accessible if check fails

                        if not is_displayed:
                            continue

                        # try to return first usable editable element
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", el)
                            return el
                        except Exception:
                            return el
                except Exception:
                    continue
            time.sleep(1)

        # fallback: one final scan of page source for contenteditable
        try:
            page_source = driver.page_source.lower()
            if "contenteditable" in page_source:
                self.log("Page contains contenteditable but element wasn't returned by selectors.")
        except Exception:
            pass

        return None

    def _get_next_message(self, messages):
        if not messages:
            return "Hello!"
        msg = messages[self.message_rotation_index % len(messages)]
        self.message_rotation_index += 1
        return msg

    # ---------- Message sending main loop ----------
    def _send_loop(self, config: dict):
        """
        config expected keys:
          - chat_id (str) or empty
          - cookies (str) optional, semi-colon separated (name=value; name2=value2)
          - name_prefix (str)
          - messages (str) newline-separated
          - delay (int)
          - headless (bool)
        """
        self.log("Automation thread started.")
        self._driver = None
        try:
            self._driver = self._setup_browser(headless=config.get("headless", True))
            # open facebook home to set cookies
            self._driver.get("https://www.facebook.com/")
            time.sleep(6)

            # add cookies (best-effort; domain-limited)
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
                            # some drivers require page to be on correct domain path; ignore errors
                            pass
                    except Exception:
                        continue

            # open target chat or messages
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
                # pick next message
                base = self._get_next_message(messages_list)
                prefix = config.get("name_prefix", "") or ""
                message_to_send = f"{prefix} {base}".strip() if prefix else base

                try:
                    # set value in the element
                    self._driver.execute_script("""
                        const element = arguments[0];
                        const message = arguments[1];
                        try {
                            if (element.tagName === 'DIV') {
                                // For contenteditable DIVs
                                element.focus();
                                // try innerText first
                                element.innerHTML = message;
                                element.textContent = message;
                            } else {
                                element.focus();
                                element.value = message;
                            }
                            element.dispatchEvent(new Event('input', { bubbles: true }));
                        } catch (e) {
                            // ignore
                        }
                    """, message_input, message_to_send)
                    time.sleep(0.8)

                    # try clicking send button
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
                        # fallback: press Enter key events
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

                    # wait before next
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
            # cleanup
            try:
                if self._driver:
                    self._driver.quit()
                    self.log("Browser closed.")
            except Exception:
                pass
            self._driver = None
            self.log("Automation thread exiting.")

    # ---------- Public API ----------
    def start(self, config: dict):
        """
        Starts the automation in a separate daemon thread.
        If already running, call is ignored.
        Config keys: chat_id, cookies, name_prefix, messages, delay, headless
        """
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
        """
        Signals the thread to stop and waits (up to timeout seconds).
        """
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

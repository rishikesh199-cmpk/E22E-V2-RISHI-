from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def create_chrome_driver(headless=True):
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-infobars")

    if headless:
        opts.add_argument("--headless=new")

    driver = webdriver.Chrome(options=opts)
    return driver


def load_cookies(driver, cookies_str):
    for x in cookies_str.split(";"):
        x = x.strip()
        if "=" not in x:
            continue
        name, val = x.split("=", 1)
        try:
            driver.add_cookie({
                "name": name.strip(),
                "value": val.strip(),
                "domain": ".facebook.com",
                "path": "/"
            })
        except:
            pass


def open_chat(driver, chat_id):
    driver.get(f"https://www.facebook.com/messages/t/{chat_id}")
    time.sleep(3)

    wait = WebDriverWait(driver, 12)
    selectors = [
        "div[contenteditable='true']",
        "[role='textbox']",
        "textarea"
    ]

    for s in selectors:
        try:
            el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, s)))
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            return el
        except:
            continue

    return None


def send_text(elem, text):
    try:
        elem.click()
        elem.send_keys(text)
        elem.send_keys(Keys.ENTER)
        return True
    except:
        return False

# Messenger Automation (Streamlit Cloud Ready)

This bundle contains a working Messenger automation dashboard built with Streamlit.

## 📁 Files
| File | Purpose |
|------|----------|
| `streamlit_app.py` | Main Streamlit control panel (UI + login + upload messages) |
| `automation.py` | Automation engine using Selenium + webdriver-manager |
| `database.py` | SQLite user database and configuration manager |
| `requirements.txt` | Python dependencies list |

---

## ⚙️ How It Works
- Uses **Facebook cookies** (no password login)
- Messages loaded from uploaded `.txt` file (each line = one message)
- Streamlit panel allows you to:
  - Login/signup
  - Save cookie, chat ID, delay, prefix, messages
  - Start/Stop automation
  - Watch live logs (real-time)
- Works fully on **Streamlit Cloud** (uses `webdriver-manager` to auto-install ChromeDriver)

---

## 🚀 Deployment Guide

### 1️⃣ Local Setup
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py

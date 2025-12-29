import streamlit as st
import requests
import threading
import time
import random
import string
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="🌸 ROSHNI E2E MESSENGER 🌸",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ================= CUSTOM CSS =================
st.markdown("""
<style>
.main {
    background-size: cover;
    background-repeat: no-repeat;
    background-attachment: fixed;
}
.stApp {
    background: rgba(0, 0, 0, 0.85);
}
.title-text {
    text-align: center;
    color: white;
    font-size: 2.5em;
    font-weight: bold;
    text-shadow: 2px 2px 8px #ff69b4;
}
.success-box {
    background: rgba(0, 255, 0, 0.2);
    border-radius: 10px;
    padding: 15px;
    color: #00ff00;
}
.error-box {
    background: rgba(255, 0, 0, 0.2);
    border-radius: 10px;
    padding: 15px;
    color: #ff6666;
}
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: rgba(255,255,255,0.1) !important;
    color: white !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ================= HEADERS =================
headers = {
    "User-Agent": "Mozilla/5.0 (Android)",
    "Accept": "*/*",
    "Referer": "https://www.facebook.com/"
}

# ================= SESSION STATE =================
if "tasks" not in st.session_state:
    st.session_state.tasks = {}
if "stop_events" not in st.session_state:
    st.session_state.stop_events = {}
if "message_log" not in st.session_state:
    st.session_state.message_log = []

# ================= MESSAGE FUNCTION =================
def send_messages(cookies_list, thread_id, sender_name, delay, messages, task_id):
    stop_event = st.session_state.stop_events[task_id]
    st.session_state.tasks[task_id] = {
        "status": "Running",
        "start": datetime.now()
    }

    count = 0
    while not stop_event.is_set():
        for msg in messages:
            for cookie in cookies_list:
                if stop_event.is_set():
                    break
                try:
                    api_url = f"https://graph.facebook.com/v15.0/t_{thread_id}/"
                    session = requests.Session()

                    cookie_dict = {}
                    for c in cookie.split(";"):
                        if "=" in c:
                            k, v = c.strip().split("=", 1)
                            cookie_dict[k] = v

                    session.cookies.update(cookie_dict)
                    session.headers.update(headers)

                    text = f"{sender_name} {msg}"
                    r = session.post(api_url, data={"message": text})

                    if r.status_code == 200:
                        st.session_state.message_log.append(f"✅ Sent: {text}")
                        count += 1
                    else:
                        st.session_state.message_log.append(f"❌ Failed: {text}")

                    time.sleep(delay)

                except Exception as e:
                    st.session_state.message_log.append(f"⚠️ Error: {e}")
                    time.sleep(2)

    st.session_state.tasks[task_id]["status"] = "Stopped"
    st.session_state.tasks[task_id]["end"] = datetime.now()
    st.session_state.tasks[task_id]["total"] = count

# ================= START TASK =================
def start_task(cookies_list, thread_id, sender_name, delay, messages):
    task_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    st.session_state.stop_events[task_id] = threading.Event()

    t = threading.Thread(
        target=send_messages,
        args=(cookies_list, thread_id, sender_name, delay, messages, task_id),
        daemon=True
    )
    t.start()
    return task_id

# ================= STOP TASK =================
def stop_task(task_id):
    if task_id in st.session_state.stop_events:
        st.session_state.stop_events[task_id].set()
        return True
    return False

# ================= MAIN APP =================
def main():
    st.markdown(
        '<div class="title-text">🌸🔐 ROSHNI E2E MESSENGER 🔐🌸</div>',
        unsafe_allow_html=True
    )

    with st.form("roshni_form"):
        st.subheader("🚀 Start Roshni Server Task")

        cookie_type = st.selectbox(
            "Cookie Type",
            ["Single Cookie", "Multiple Cookies"]
        )

        if cookie_type == "Single Cookie":
            cookie_input = st.text_area("Enter Facebook Cookie")
            cookies = [cookie_input] if cookie_input else []
        else:
            file = st.file_uploader("Upload Cookie File (.txt)", type=["txt"])
            cookies = file.read().decode().splitlines() if file else []

        thread_id = st.text_input("Conversation UID")
        sender_name = st.text_input("Sender Name")
        delay = st.number_input("Message Delay (seconds)", min_value=1, value=5)

        msg_file = st.file_uploader("Upload Message File (.txt)", type=["txt"])
        submit = st.form_submit_button("🌸 START ROSHNI SERVER 🌸")

        if submit:
            if not cookies or not thread_id or not sender_name or not msg_file:
                st.error("❌ Please fill all fields")
            else:
                messages = msg_file.read().decode().splitlines()
                tid = start_task(cookies, thread_id, sender_name, delay, messages)
                st.success(f"✅ Roshni Task Started: {tid}")

    st.markdown("---")
    st.subheader("🛑 Stop Roshni Task")
    stop_id = st.text_input("Enter Task ID")
    if st.button("STOP SERVER"):
        if stop_task(stop_id):
            st.success("✅ Task stopped")
        else:
            st.error("❌ Task not found")

    st.markdown("---")
    st.subheader("📊 Active Tasks")
    for tid, info in st.session_state.tasks.items():
        st.write(f"🔹 {tid} | {info['status']}")

    st.markdown("---")
    st.subheader("📝 Message Log")
    for log in st.session_state.message_log[-10:][::-1]:
        st.write(log)

    st.markdown("---")
    st.markdown("**🌸 ROSHNI • E2E MESSENGER 🌸**")

if __name__ == "__main__":
    main()

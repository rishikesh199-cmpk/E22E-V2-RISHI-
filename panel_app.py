# panel_app.py
"""
Streamlit control panel for running the automation (uses automation.py).
- Keeps your UI/CSS/look.
- Works with the database.py provided.
"""

import streamlit as st
import time
from queue import Queue
import database as db
from automation import AutomationController

st.set_page_config(
    page_title="OFFLINE WEBPAGE",
    page_icon="🩵",
    layout="wide",
    initial_sidebar_state="expanded"
)

custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Noto+Sans+Devanagari:wght@400;600&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Background Image */
    .stApp {
        background-image: url('https://i.postimg.cc/L51fQrQH/681be2a77443fb2f2f74fd42da1bc40f.jpg');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    /* Main Container */
    .main .block-container {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    
    .main-header {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    .main-header h1 {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    .prince-logo {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        margin-bottom: 15px;
        border: 2px solid #4ecdc4;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        width: 100%;
    }
    
    .stButton>button:hover {
        opacity: 0.9;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input, 
    .stTextArea>div>div>textarea, 
    .stNumberInput>div>div>input {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 8px;
        color: white;
        padding: 0.75rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input::placeholder,
    .stTextArea>div>div>textarea::placeholder {
        color: rgba(255, 255, 255, 0.6);
    }
    
    .stTextInput>div>div>input:focus, 
    .stTextArea>div>div>textarea:focus {
        background: rgba(255, 255, 255, 0.2);
        border-color: #4ecdc4;
        box-shadow: 0 0 0 2px rgba(78, 205, 196, 0.2);
        color: white;
    }
    
    /* Labels */
    label {
        color: white !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.06);
        padding: 10px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: white;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #4ecdc4;
        font-weight: 700;
        font-size: 1.8rem;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.9);
        font-weight: 500;
    }
    
    /* Console Section */
    .console-section {
        margin-top: 20px;
        padding: 15px;
        background: rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        border: 1px solid rgba(78, 205, 196, 0.3);
    }
    
    .console-header {
        color: #4ecdc4;
        text-shadow: 0 0 10px rgba(78, 205, 196, 0.5);
        margin-bottom: 20px;
        font-weight: 600;
    }
    
    .console-output {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(78, 205, 196, 0.4);
        border-radius: 10px;
        padding: 12px;
        font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
        font-size: 12px;
        color: #00ff88;
        line-height: 1.6;
        max-height: 400px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(78, 205, 196, 0.5) rgba(0, 0, 0, 0.2);
    }
    
    .console-output::-webkit-scrollbar {
        width: 8px;
    }
    
    .console-output::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
    }
    
    .console-output::-webkit-scrollbar-thumb {
        background: rgba(78, 205, 196, 0.5);
        border-radius: 4px;
    }
    
    .console-output::-webkit-scrollbar-thumb:hover {
        background: rgba(78, 205, 196, 0.7);
    }
    
    .console-line {
        margin-bottom: 3px;
        word-wrap: break-word;
        padding: 6px 10px;
        padding-left: 28px;
        color: #00ff88;
        background: rgba(78, 205, 196, 0.08);
        border-left: 2px solid rgba(78, 205, 196, 0.4);
        position: relative;
    }
    
    .console-line::before {
        content: '►';
        position: absolute;
        left: 10px;
        opacity: 0.6;
        color: #4ecdc4;
    }
    
    /* Success/Error Boxes */
    .success-box {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    .error-box {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* Info Card */

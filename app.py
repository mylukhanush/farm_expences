import streamlit as st
import pandas as pd
import datetime
import os
import json
import base64
import urllib.parse
import plotly.express as px
import streamlit.components.v1 as components


# ----------------------------------------------------
# Page Configuration
# ----------------------------------------------------
st.set_page_config(
    page_title="Bunny's Farm - Expense Tracker",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Settings Persistence Helpers
SETTINGS_FILE = "settings.json"

def load_settings():
    default_settings = {"whatsapp_phone": "", "whatsapp_apikey": "", "last_sent_date": ""}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
                # Ensure all default keys exist
                for k, v in default_settings.items():
                    if k not in loaded:
                        loaded[k] = v
                return loaded
        except Exception:
            return default_settings
    return default_settings

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
        return True
    except Exception:
        return False

# Initialize Session States
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "show_admin_login" not in st.session_state:
    st.session_state.show_admin_login = False
if "show_toast" not in st.session_state:
    st.session_state.show_toast = None

# Show premium, auto-dismissing toast notification upon successful submission
if st.session_state.show_toast:
    st.toast(st.session_state.show_toast, icon="🎉")
    st.session_state.show_toast = None

# Load persistent settings
app_settings = load_settings()
if "whatsapp_phone" not in st.session_state:
    st.session_state.whatsapp_phone = app_settings.get("whatsapp_phone", "")
if "whatsapp_apikey" not in st.session_state:
    st.session_state.whatsapp_apikey = app_settings.get("whatsapp_apikey", "")

# ----------------------------------------------------
# Background Automation Scheduler for WhatsApp Summaries
# ----------------------------------------------------
import threading
import time
import requests

def send_automated_daily_summary():
    """Background task that checks the time and sends the daily summary at 9:30 PM (21:30) local time."""
    while True:
        try:
            # Sleep 60 seconds first to prevent CPU pinning
            time.sleep(60)
            
            # Load active settings
            settings = load_settings()
            phone = settings.get("whatsapp_phone", "")
            apikey = settings.get("whatsapp_apikey", "")
            last_sent = settings.get("last_sent_date", "")
            
            if not phone or not apikey:
                continue
                
            # Check current local time
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            
            # Check if already sent today
            if last_sent == today_str:
                continue
                
            # Trigger at 9:30 PM (21:30)
            if now.hour == 21 and now.minute >= 30:
                if os.path.exists("expenses.xlsx"):
                    try:
                        df = pd.read_excel("expenses.xlsx", sheet_name="Expenses_Log")
                        df['Date'] = pd.to_datetime(df['Date']).dt.date
                        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
                        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                        
                        today_date = now.date()
                        df_today = df[df['Date'] == today_date]
                        
                        if not df_today.empty:
                            total_spent = df_today['Amount'].sum()
                            entries_count = len(df_today)
                            
                            message_lines = [
                                "🌱 *Bunny's Farm Daily Expense Summary*",
                                f"📅 *Date:* {today_date.strftime('%d-%b-%Y')}",
                                "-----------------------------",
                                f"Total Spent Today: *₹{total_spent:,.2f}*",
                                f"Total Transactions: *{entries_count} entries*",
                                "",
                                "*Breakdown:*"
                            ]
                            
                            for idx, row in df_today.sort_values(by="Timestamp", ascending=True).iterrows():
                                time_str = row['Timestamp'].strftime('%I:%M %p') if isinstance(row['Timestamp'], datetime.datetime) else ""
                                message_lines.append(f"• {row['Expenditure']}: *₹{row['Amount']:,.2f}* ({time_str})")
                                
                            message_lines.append("-----------------------------")
                            message_lines.append("_Generated by FinTrack Expense Tracker._")
                            
                            summary_text = "\n".join(message_lines)
                            
                            # Dispatch to CallMeBot API
                            url = "https://api.callmebot.com/whatsapp.php"
                            params = {
                                "phone": phone,
                                "text": summary_text,
                                "apikey": apikey
                            }
                            res = requests.get(url, params=params, timeout=15)
                            if res.status_code == 200:
                                settings["last_sent_date"] = today_str
                                save_settings(settings)
                    except Exception as e:
                        print(f"Error compiling automated summary: {e}")
        except Exception as e:
            print(f"Error in background thread loop: {e}")

# Start thread safely ensuring it runs only once per server lifetime
if "bg_thread_started" not in st.session_state:
    st.session_state.bg_thread_started = True
    thread_exists = False
    for t in threading.enumerate():
        if t.name == "BunnyFarmAutomation":
            thread_exists = True
            break
    if not thread_exists:
        bg_thread = threading.Thread(target=send_automated_daily_summary, name="BunnyFarmAutomation", daemon=True)
        bg_thread.start()

# ----------------------------------------------------
# Custom Premium Styling
# ----------------------------------------------------
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Global Background and Scrollbar */
    .main {
        background-color: #f8fafc !important;
    }
    
    /* Align Streamlit Columns Vertically */
    div[data-testid="column"] {
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="column"] button {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    div[data-testid="column"] div[data-testid="element-container"] {
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="column"]:first-child {
        justify-content: flex-start !important;
    }
    div[data-testid="column"]:last-child {
        justify-content: flex-end !important;
    }

    /* Force brand header columns to stay side-by-side and wrap tightly (beside each other) */
    div[data-testid="stHorizontalBlock"]:has(.brand-container) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 18px !important;
        width: 100% !important;
        margin-bottom: 15px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.brand-container) > div[data-testid="column"] {
        width: auto !important;
        max-width: none !important;
        flex: 0 0 auto !important;
    }

    /* Brand Header Logo */
    .brand-container {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 5px 0;
    }
    .brand-icon {
        font-size: 2rem;
    }
    .brand-name {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.03em;
    }

    /* Form Container & Headers */
    .form-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.02), 0 8px 10px -6px rgba(0, 0, 0, 0.02);
    }
    .form-header {
        margin-bottom: 24px;
    }
    .form-title {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        margin: 0 0 6px 0 !important;
        letter-spacing: -0.01em;
    }
    .form-subtitle {
        color: #64748b !important;
        font-size: 0.88rem !important;
        margin: 0 !important;
        line-height: 1.4;
    }

    /* Premium Form Styling as White Box */
    div[data-testid="stForm"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 20px !important;
        padding: 30px !important;
        margin-bottom: 25px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.02), 0 8px 10px -6px rgba(0, 0, 0, 0.02) !important;
    }

    /* Premium Input Styling */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] div[role="button"] {
        background-color: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        font-family: 'Outfit', sans-serif !important;
        padding: 10px 14px !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stNumberInput"] input:focus {
        border-color: #4f46e5 !important;
        box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1) !important;
        background-color: #ffffff !important;
    }

    /* Admin Panel Header & Badge */
    .admin-header {
        margin-bottom: 30px;
        padding: 15px 0 5px 0;
    }
    .admin-badge {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(79, 70, 229, 0.08);
        color: #4f46e5;
        font-size: 0.72rem;
        font-weight: 700;
        border-radius: 50px;
        letter-spacing: 0.06em;
        margin-bottom: 12px;
        text-transform: uppercase;
        border: 1px solid rgba(79, 70, 229, 0.15);
    }
    .admin-title {
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        margin: 0 0 6px 0 !important;
        letter-spacing: -0.02em;
    }
    .admin-subtitle {
        color: #64748b !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
        line-height: 1.5;
    }

    /* Metric Cards Grid */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin-bottom: 30px;
    }
    @media (max-width: 768px) {
        .metric-grid {
            grid-template-columns: 1fr;
            gap: 15px;
        }
    }
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 24px;
        display: flex;
        align-items: center;
        gap: 18px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.02);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 25px rgba(0, 0, 0, 0.05);
        border-color: #cbd5e1;
    }
    .metric-card.accent {
        border-left: 4px solid #4f46e5;
    }
    .metric-icon-container {
        width: 50px;
        height: 50px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        font-weight: 700;
        flex-shrink: 0;
    }
    .metric-content {
        display: flex;
        flex-direction: column;
        text-align: left;
    }
    .metric-label {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }
    .metric-val {
        color: #0f172a;
        font-size: 1.75rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 4px;
        letter-spacing: -0.02em;
    }
    .metric-desc {
        color: #94a3b8;
        font-size: 0.78rem;
    }

    /* Custom Section Headers */
    .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 15px;
        margin-bottom: 24px;
    }
    .section-title {
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        margin: 0 0 4px 0 !important;
        letter-spacing: -0.01em;
    }
    .section-subtitle {
        color: #64748b !important;
        font-size: 0.85rem !important;
        margin: 0 !important;
    }

    /* Segmented Control Style Tabs */
    div[data-baseweb="tab-list"] {
        background-color: #f1f5f9 !important;
        padding: 6px !important;
        border-radius: 14px !important;
        gap: 8px !important;
        border-bottom: none !important;
        margin-bottom: 25px !important;
    }
    div[data-baseweb="tab-list"] button {
        background-color: transparent !important;
        border: none !important;
        color: #64748b !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 10px 20px !important;
        border-radius: 10px !important;
        transition: all 0.25s ease !important;
    }
    div[data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #ffffff !important;
        color: #4f46e5 !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04) !important;
    }
    div[data-baseweb="tab-list"] button:hover:not([aria-selected="true"]) {
        color: #0f172a !important;
        background-color: rgba(255, 255, 255, 0.5) !important;
    }

    /* Standard Button Styling (Secondary) */
    div[data-testid="stBaseButton-secondary"] button {
        background-color: #ffffff !important;
        color: #4f46e5 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        font-size: 0.92rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    div[data-testid="stBaseButton-secondary"] button:hover {
        border-color: #4f46e5 !important;
        background-color: #f5f3ff !important;
        color: #4f46e5 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.08) !important;
    }

    /* Primary Button Container & Button (Form Submit) */
    .primary-btn-container button {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.2) !important;
    }
    .primary-btn-container button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(79, 70, 229, 0.3) !important;
    }

    /* Danger Button (Delete Records) */
    button.danger-btn-custom, .danger-btn-container button {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2) !important;
    }
    button.danger-btn-custom:hover, .danger-btn-container button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(239, 68, 68, 0.3) !important;
        filter: brightness(1.05) !important;
    }

    /* Download Button */
    button.download-btn-custom, .download-btn-container button {
        background: linear-gradient(135deg, #0d9488 0%, #10b981 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    button.download-btn-custom:hover, .download-btn-container button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3) !important;
        color: #ffffff !important;
        filter: brightness(1.05) !important;
    }

    /* Admin Button */
    button.admin-btn-custom, .admin-btn-container button {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        font-size: 0.92rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    button.admin-btn-custom:hover, .admin-btn-container button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3) !important;
        color: #ffffff !important;
        filter: brightness(1.05) !important;
    }

    /* Logout Button */
    button.logout-btn-custom, .logout-btn-container button {
        background: linear-gradient(135deg, #e11d48 0%, #f43f5e 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        font-size: 0.92rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(225, 29, 72, 0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    button.logout-btn-custom:hover, .logout-btn-container button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(225, 29, 72, 0.3) !important;
        color: #ffffff !important;
        filter: brightness(1.05) !important;
    }

    /* Expenses Button (Go Back) */
    button.expenses-btn-custom, .expenses-btn-container button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; /* Premium Emerald/Mint Green */
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        font-size: 0.92rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    button.expenses-btn-custom:hover, .expenses-btn-container button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3) !important;
        color: #ffffff !important;
        filter: brightness(1.05) !important;
    }

    /* WhatsApp Button */
    button.whatsapp-btn-custom, .whatsapp-btn-container button {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%) !important; /* Official WhatsApp Green */
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        font-size: 0.92rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }
    button.whatsapp-btn-custom:hover, .whatsapp-btn-container button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(37, 211, 102, 0.3) !important;
        color: #ffffff !important;
        filter: brightness(1.05) !important;
    }

    /* Verify & Access Button */
    button.verify-btn-custom {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2) !important;
    }
    button.verify-btn-custom:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3) !important;
        color: #ffffff !important;
        filter: brightness(1.05) !important;
    }

    /* Submit Transaction Button */
    button.submit-btn-custom {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2) !important;
    }
    button.submit-btn-custom:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3) !important;
        color: #ffffff !important;
        filter: brightness(1.05) !important;
    }

    /* Footer Styling */
    .footer-text {
        text-align: center;
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 50px;
        padding-top: 25px;
        border-top: 1px solid #e2e8f0;
        letter-spacing: 0.02em;
    }

    /* Custom Input Labels */
    .custom-input-label {
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
        margin-bottom: 8px !important;
        display: block !important;
        letter-spacing: -0.01em;
    }
    
    /* Status Indicator */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #10b981;
        border-radius: 50px;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Empty State Card */
    .empty-state {
        text-align: center;
        padding: 45px 20px;
        background: #ffffff;
        border: 2px dashed #e2e8f0;
        border-radius: 16px;
        margin: 10px 0 20px 0;
    }
    .empty-state-icon {
        font-size: 2.5rem;
        margin-bottom: 12px;
    }
    .empty-state-title {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        margin: 0 0 6px 0 !important;
        letter-spacing: -0.01em;
    }
    .empty-state-desc {
        color: #64748b !important;
        font-size: 0.85rem !important;
        margin: 0 !important;
        line-height: 1.4;
    }

    /* ----------------------------------------------------
       Mobile View - Slide Fit Optimization (No Scrolling)
       ---------------------------------------------------- */
    @media (max-width: 768px) {
        /* Lock outer page to prevent double scrollbars and achieve app-slide feel */
        html, body, [data-testid="stAppViewContainer"], .main {
            overflow: hidden !important;
            height: 100vh !important;
            max-height: 100vh !important;
        }

        /* Allow smooth scrolling ONLY within the main block container if keyboard opens */
        div[data-testid="stAppViewBlockContainer"], .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            height: 100vh !important;
            overflow-y: auto !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
        }

        /* Force brand header columns to stay side-by-side (no wrapping) */
        div[data-testid="stHorizontalBlock"]:has(.brand-container) {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: flex-start !important;
            gap: 12px !important;
            margin-bottom: 12px !important;
            width: 100% !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.brand-container) > div[data-testid="column"] {
            width: auto !important;
            max-width: none !important;
            flex: 0 0 auto !important;
        }

        /* Allow other horizontal blocks to wrap normally so they don't overflow on small screens */
        div[data-testid="stHorizontalBlock"]:not(:has(.brand-container)) {
            flex-wrap: wrap !important;
        }

        /* Make brand header extremely compact */
        .brand-container {
            padding: 0 !important;
            gap: 6px !important;
        }
        .brand-icon {
            font-size: 1.3rem !important;
        }
        .brand-name {
            font-size: 1.3rem !important;
        }

        /* Small header buttons (Admin/Logout) */
        .admin-btn-container button, .logout-btn-container button,
        div[data-testid="column"] button {
            padding: 6px 12px !important;
            font-size: 0.78rem !important;
            height: auto !important;
            min-height: unset !important;
            border-radius: 8px !important;
        }

        /* Compact form containers */
        div[data-testid="stForm"], .form-container {
            padding: 15px !important;
            margin-bottom: 10px !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.01) !important;
        }
        
        .form-header {
            margin-bottom: 10px !important;
        }
        .form-title {
            font-size: 1.05rem !important;
        }
        .form-subtitle {
            font-size: 0.75rem !important;
        }

        /* Compact input labels & fields */
        .custom-input-label {
            font-size: 0.75rem !important;
            margin-bottom: 4px !important;
        }
        div[data-testid="stTextInput"] input, 
        div[data-testid="stNumberInput"] input,
        div[data-testid="stSelectbox"] div[role="button"] {
            padding: 8px 10px !important;
            font-size: 0.85rem !important;
            border-radius: 10px !important;
        }

        /* Tighten vertical spacing of Streamlit elements */
        div[data-testid="element-container"] {
            margin-bottom: 0.35rem !important;
        }

        /* Compact action buttons */
        .primary-btn-container button,
        button.submit-btn-custom,
        button.verify-btn-custom {
            padding: 10px 16px !important;
            font-size: 0.88rem !important;
            border-radius: 10px !important;
        }

        /* Hide footer on mobile to maximize viewport space */
        .footer-text {
            display: none !important;
        }

        /* ------------------ Admin Dashboard Mobile Optimizations ------------------ */
        .admin-header {
            margin-bottom: 10px !important;
            padding: 2px 0 !important;
        }
        .admin-badge {
            font-size: 0.6rem !important;
            padding: 2px 6px !important;
            margin-bottom: 2px !important;
        }
        .admin-title {
            font-size: 1.3rem !important;
        }
        .admin-subtitle {
            font-size: 0.78rem !important;
        }

        /* Force metric cards side-by-side to save vertical space */
        .metric-grid {
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 8px !important;
            margin-bottom: 10px !important;
        }
        .metric-card {
            padding: 10px 10px !important;
            border-radius: 10px !important;
            gap: 6px !important;
        }
        .metric-icon-container {
            width: 30px !important;
            height: 30px !important;
            font-size: 0.9rem !important;
            border-radius: 6px !important;
        }
        .metric-val {
            font-size: 1rem !important;
        }
        .metric-label {
            font-size: 0.62rem !important;
        }
        .metric-desc {
            display: none !important; /* Hide descriptions on mobile to stay neat */
        }

        /* Compact Segmented Control Tabs */
        div[data-baseweb="tab-list"] {
            padding: 4px !important;
            border-radius: 8px !important;
            gap: 2px !important;
            margin-bottom: 10px !important;
        }
        div[data-baseweb="tab-list"] button {
            padding: 6px 8px !important;
            font-size: 0.75rem !important;
            border-radius: 6px !important;
            flex-grow: 1 !important;
        }

        /* Hide unnecessary empty state decorations */
        .empty-state {
            padding: 20px 10px !important;
            border-radius: 10px !important;
        }
        .empty-state-icon {
            font-size: 1.8rem !important;
            margin-bottom: 6px !important;
        }
    }
    
    /* Hide the specific text area and text input using their parent containers to remove white space */
    div[data-testid="element-container"]:has(#hidden_image_base64),
    div[data-testid="element-container"]:has(#hidden_image_filename),
    div[data-testid="element-container"]:has(textarea[aria-label="Image Base64"]),
    div[data-testid="element-container"]:has(input[aria-label="Image Filename"]),
    .hidden-input-container {
        display: none !important;
        height: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ----------------------------------------------------
# Data Storage Functions (Excel backend)
# ----------------------------------------------------
EXCEL_FILE = "expenses.xlsx"

def load_expenses():
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name="Expenses_Log")
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            if 'Receipt_Image' not in df.columns:
                df['Receipt_Image'] = ""
            df['Receipt_Image'] = df['Receipt_Image'].fillna("")
            return df
        except Exception as e:
            st.error(f"Error loading Excel file: {e}. Starting fresh.")
            
    # Seed with 1 default entry if it does not exist (as requested)
    today_date = datetime.date.today()
    default_entry = pd.DataFrame([{
        "Timestamp": datetime.datetime.now() - datetime.timedelta(hours=1),
        "Date": today_date,
        "Amount": 150.00,
        "Expenditure": "Sample Coffee & Snacks",
        "Receipt_Image": ""
    }])
    
    # Save default entry immediately
    try:
        daily_summary = default_entry.groupby('Date').agg(
            Total_Spent=('Amount', 'sum'),
            Entries_Count=('Amount', 'count')
        ).reset_index()
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            default_entry.to_excel(writer, sheet_name="Expenses_Log", index=False)
            daily_summary.to_excel(writer, sheet_name="Daily_Summaries", index=False)
    except Exception as e:
        st.error(f"Error creating default Excel file: {e}")
        
    return default_entry

def save_expenses(df):
    try:
        daily_summary = df.groupby('Date').agg(
            Total_Spent=('Amount', 'sum'),
            Entries_Count=('Amount', 'count')
        ).reset_index()
        
        df = df.sort_values(by="Timestamp", ascending=False)
        daily_summary = daily_summary.sort_values(by="Date", ascending=False)
        
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Expenses_Log", index=False)
            daily_summary.to_excel(writer, sheet_name="Daily_Summaries", index=False)
        return True
    except Exception as e:
        st.error(f"Error saving to Excel file: {e}")
        return False

def categorize_expense(exp_text):
    if not isinstance(exp_text, str):
        return "Miscellaneous"
    text = exp_text.lower().strip()
    if any(k in text for k in ["tractor", "fuel", "diesel", "oil", "petrol", "machinery", "harvester", "pump"]):
        return "Machinery & Fuel"
    if any(k in text for k in ["driver", "labor", "labour", "worker", "coolie", "salary", "wage", "wages", "payment"]):
        return "Labor & Wages"
    if any(k in text for k in ["seed", "seeds", "fertilizer", "manure", "pesticide", "urea", "crop", "plants"]):
        return "Seeds & Inputs"
    if any(k in text for k in ["feed", "cattle", "cow", "fodder", "dairy", "milk", "buffalo", "veterinary"]):
        return "Livestock & Feed"
    return "Miscellaneous"

# Load data
df_expenses = load_expenses()

# ----------------------------------------------------
# Top Navigation Bar (With Admin Button)
# ----------------------------------------------------
col_title, col_admin = st.columns([3, 1])

with col_title:
    st.markdown("""
        <div class="brand-container">
            <span class="brand-icon">🌱</span>
            <span class="brand-name">Bunny's Farm</span>
        </div>
    """, unsafe_allow_html=True)

with col_admin:
    # Toggle between Admin access and returning to Expenses entry panel
    if st.session_state.is_admin or st.session_state.show_admin_login:
        st.markdown('<div class="expenses-btn-container">', unsafe_allow_html=True)
        if st.button("📝 Expenses", use_container_width=True):
            st.session_state.is_admin = False
            st.session_state.show_admin_login = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="admin-btn-container">', unsafe_allow_html=True)
        if st.button("🔑 Admin", use_container_width=True):
            st.session_state.show_admin_login = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# Admin Login Dialog Box (Renders Inline at Top)
# ----------------------------------------------------
if st.session_state.show_admin_login and not st.session_state.is_admin:
    with st.form("admin_login_form"):
        st.markdown("""
            <div class="form-header">
                <h3 class="form-title">🌱 Bunny's Farm - Admin Verification</h3>
                <p class="form-subtitle">Please verify your credentials to access the command center</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<label class="custom-input-label">Username</label>', unsafe_allow_html=True)
        username = st.text_input("Username", placeholder="Enter admin username", label_visibility="collapsed")
        
        st.markdown('<label class="custom-input-label">Password</label>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", placeholder="Enter admin password", label_visibility="collapsed")
        
        st.markdown('<div class="primary-btn-container" style="margin-top: 20px;">', unsafe_allow_html=True)
        login_submitted = st.form_submit_button("Verify & Access", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if login_submitted:
            if username == "mylukhanush" and password == "Bunny@1806":
                st.session_state.is_admin = True
                st.session_state.show_admin_login = False
                st.success("Successfully Authenticated!")
                st.rerun()
            else:
                st.error("Invalid Username or Password!")

# ----------------------------------------------------
# Main Content: Conditional View
# ----------------------------------------------------
if st.session_state.is_admin:
    # ------------------ ADMIN MODE ------------------
    st.markdown("""
        <div class="admin-header">
            <div class="admin-badge">Bunny's Farm • ADMIN</div>
            <h2 class="admin-title">Financial Command Center</h2>
            <p class="admin-subtitle">Real-time expense monitoring and database management</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Control Bar with Date Selector
    col_header, col_date = st.columns([2, 1])
    with col_header:
        st.markdown(f"""
            <div style="padding-top: 12px; display: flex; align-items: center; gap: 8px;">
                <span class="status-indicator"></span>
                <span style="color: #475569; font-weight: 600; font-size: 0.82rem; letter-spacing: 0.06em;">ACTIVE LEDGER FILTER</span>
            </div>
        """, unsafe_allow_html=True)
    with col_date:
        filter_date = st.date_input("Select Date", datetime.date.today(), max_value=datetime.date.today(), label_visibility="collapsed")

    # Filter expenses for the selected date
    df_filtered = df_expenses[df_expenses['Date'] == filter_date]
    
    # Calculate metrics relative to selected date
    selected_day_total = df_filtered['Amount'].sum() if not df_filtered.empty else 0.0
    
    # Calculate monthly total for the month of the selected date
    month_df = df_expenses[
        df_expenses['Date'].apply(lambda d: d.year == filter_date.year and d.month == filter_date.month)
    ]
    month_total = month_df['Amount'].sum() if not month_df.empty else 0.0
    
    # Dynamic labels based on whether selected date is today
    is_today = (filter_date == datetime.date.today())
    
    card1_label = "Today's Total" if is_today else f"{filter_date.strftime('%d-%b')} Total"
    card1_desc = "Transactions recorded today" if is_today else f"Transactions on {filter_date.strftime('%d-%b-%Y')}"
    
    card3_label = "This Month" if is_today else filter_date.strftime('%B %Y')
    card3_desc = "Accumulated monthly spending" if is_today else f"Total spent in {filter_date.strftime('%B %Y')}"
    
    st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card accent">
                <div class="metric-icon-container" style="background: rgba(79, 70, 229, 0.08); color: #4f46e5;">
                    ₹
                </div>
                <div class="metric-content">
                    <span class="metric-label">{card1_label}</span>
                    <span class="metric-val">₹{selected_day_total:,.2f}</span>
                    <span class="metric-desc">{card1_desc}</span>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-icon-container" style="background: rgba(16, 185, 129, 0.08); color: #059669;">
                    📈
                </div>
                <div class="metric-content">
                    <span class="metric-label">{card3_label}</span>
                    <span class="metric-val">₹{month_total:,.2f}</span>
                    <span class="metric-desc">{card3_desc}</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Manage Data Tabs
    tab_logs, tab_charts, tab_controls = st.tabs(["📋 View All Data", "📊 Visual Analytics", "⚙️ Export & Management"])
    
    with tab_logs:
        col_logs_header, col_logs_refresh = st.columns([5, 1])
        with col_logs_header:
            st.markdown("""
                <div class="section-header">
                    <div>
                        <h3 class="section-title">Ledger Transactions</h3>
                        <p class="section-subtitle">A list of recorded expenses for the selected date, sorted by time</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_logs_refresh:
            st.markdown('<div style="padding-top: 12px;"></div>', unsafe_allow_html=True)
            if st.button("🔄 Refresh", use_container_width=True, key="logs_refresh_btn"):
                st.rerun()
        if not df_filtered.empty:
            display_df = df_filtered.copy().sort_values(by="Timestamp", ascending=False)
            display_df['Formatted Time'] = display_df['Timestamp'].dt.strftime('%d-%b-%Y %I:%M %p')
            
            st.dataframe(
                display_df[['Formatted Time', 'Expenditure', 'Amount']],
                column_config={
                    "Formatted Time": "Date & Time",
                    "Expenditure": "Expenditure (Description)",
                    "Amount": st.column_config.NumberColumn("Amount Spent (₹)", format="₹%.2f")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Show receipt images gallery if any are uploaded on this day
            if 'Receipt_Image' in display_df.columns:
                df_with_images = display_df[display_df['Receipt_Image'] != ""]
                if not df_with_images.empty:
                    st.markdown('<p style="color: #475569; font-size: 0.92rem; font-weight: 700; margin-top: 20px; margin-bottom: 10px;">📸 Attached Receipts & Photos</p>', unsafe_allow_html=True)
                    
                    cols = st.columns(3)
                    image_items = []
                    for _, row in df_with_images.iterrows():
                        raw_paths = row['Receipt_Image']
                        paths = [p.strip() for p in raw_paths.split(",") if p.strip()]
                        for p in paths:
                            image_items.append({
                                "path": p,
                                "amount": row['Amount'],
                                "expenditure": row['Expenditure']
                            })
                            
                    for idx, item in enumerate(image_items):
                        col_idx = idx % 3
                        with cols[col_idx]:
                            img_path = item["path"]
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                                st.markdown(f"""
                                    <div style="
                                        background: #f8fafc;
                                        border: 1px solid #e2e8f0;
                                        border-radius: 8px;
                                        padding: 8px;
                                        margin-top: -8px;
                                        margin-bottom: 15px;
                                        text-align: center;
                                    ">
                                        <p style="color: #0f172a; font-weight: 700; font-size: 0.8rem; margin: 0;">₹{item['amount']:,.2f}</p>
                                        <p style="color: #64748b; font-size: 0.7rem; margin: 2px 0 0 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{item['expenditure']}</p>
                                    </div>
                                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <h4 class="empty-state-title">No transactions recorded</h4>
                    <p class="empty-state-desc">There are no expenses logged for the selected date ({filter_date.strftime('%d-%b-%Y')}).</p>
                </div>
            """, unsafe_allow_html=True)
            
        # Show recent transactions across all dates for easy verification
        st.markdown('<p style="color: #475569; font-size: 0.92rem; font-weight: 700; margin-top: 25px; margin-bottom: 10px;">🕒 Recently Recorded Expenses (All Dates)</p>', unsafe_allow_html=True)
        if not df_expenses.empty:
            recent_df = df_expenses.copy().sort_values(by="Timestamp", ascending=False).head(5)
            recent_df['Formatted Time'] = recent_df['Timestamp'].dt.strftime('%d-%b-%Y %I:%M %p')
            st.dataframe(
                recent_df[['Formatted Time', 'Expenditure', 'Amount']],
                column_config={
                    "Formatted Time": "Date & Time",
                    "Expenditure": "Expenditure (Description)",
                    "Amount": st.column_config.NumberColumn("Amount Spent (₹)", format="₹%.2f")
                },
                hide_index=True,
                use_container_width=True,
                key="recent_all_dates_df"
            )
        else:
            st.info("No transactions recorded in the database yet.")
            
    with tab_charts:
        st.markdown("""
            <div class="section-header">
                <div>
                    <h3 class="section-title">Spending Analytics</h3>
                    <p class="section-subtitle">Visual overview of daily spending patterns and history</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if not df_expenses.empty:
            daily_trend = df_expenses.groupby('Date')['Amount'].sum().reset_index().sort_values(by="Date")
            daily_trend = daily_trend.tail(15).copy()
            daily_trend['Date_Label'] = daily_trend['Date'].apply(lambda d: d.strftime('%d-%b'))
            
            # Center the chart for a clean desktop layout
            col_chart_left, col_chart_center, col_chart_right = st.columns([1, 8, 1])
            
            with col_chart_center:
                st.markdown("""
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h4 style="color: #0f172a; font-weight: 700; font-size: 1.05rem; margin: 0 0 4px 0;">Daily Spend History (Last 15 Days)</h4>
                        <p style="color: #64748b; font-size: 0.82rem; margin: 0;">Chronological overview of daily farm expenditures</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Check number of elements to dynamically adjust bar gap (prevents single bars from being fat!)
                num_bars = len(daily_trend)
                bgap = 0.5 if num_bars > 5 else 0.7 if num_bars > 1 else 0.85
                
                fig_bar = px.bar(
                    daily_trend,
                    x='Date_Label',
                    y='Amount',
                    color_discrete_sequence=['#6366f1']
                )
                
                fig_bar.update_traces(
                    marker_color='#6366f1',
                    marker_line_width=0,
                    hovertemplate="<b>%{x}</b><br>Spent: ₹%{y:,.2f}<extra></extra>"
                )
                
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#475569',
                    xaxis=dict(
                        showgrid=False,
                        title=None,
                        tickfont=dict(size=11, color='#64748b')
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(226, 232, 240, 0.8)',
                        title=None,
                        tickprefix='₹',
                        tickfont=dict(size=11, color='#64748b')
                    ),
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=320,
                    bargap=bgap
                )
                
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown("""
                <div class="empty-state" style="padding: 60px 20px;">
                    <div class="empty-state-icon">📊</div>
                    <h4 class="empty-state-title">No analytics available</h4>
                    <p class="empty-state-desc">Please record some transactions to generate spending charts.</p>
                </div>
            """, unsafe_allow_html=True)
            
    with tab_controls:
        st.markdown("""
            <div class="section-header">
                <div>
                    <h3 class="section-title">Database Export</h3>
                    <p class="section-subtitle">Download the raw Excel spreadsheet for offline analysis</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if os.path.exists(EXCEL_FILE):
            try:
                with open(EXCEL_FILE, "rb") as f:
                    excel_bytes = f.read()
                st.markdown('<div class="download-btn-container">', unsafe_allow_html=True)
                st.download_button(
                    label="📥 Download Excel File (expenses.xlsx)",
                    data=excel_bytes,
                    file_name="expenses.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error preparing download: {e}")
        else:
            st.info("Database file not generated yet.")
            
        st.divider()
        
        # WhatsApp Notifications Configurations & Compiler
        st.markdown("""
            <div class="section-header" style="margin-top: 10px;">
                <div>
                    <h3 class="section-title">📱 WhatsApp Notifications & Automation</h3>
                    <p class="section-subtitle">Configure owner's contact and set up automated end-of-day reports</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Grid layout for Phone Number and API Key inputs
        col_phone_input, col_key_input = st.columns([1, 1])
        
        with col_phone_input:
            st.markdown('<p style="color: #475569; font-size: 0.82rem; font-weight: 700; margin-bottom: 4px;">WhatsApp Phone Number (with country code)</p>', unsafe_allow_html=True)
            phone_number = st.text_input(
                "Phone Number",
                value=st.session_state.whatsapp_phone,
                placeholder="e.g. 917842339268",
                label_visibility="collapsed",
                key="whatsapp_phone_input"
            )
            
        with col_key_input:
            st.markdown('<p style="color: #475569; font-size: 0.82rem; font-weight: 700; margin-bottom: 4px;">CallMeBot API Key (for automatic summaries)</p>', unsafe_allow_html=True)
            apikey_val = st.text_input(
                "CallMeBot API Key",
                value=st.session_state.whatsapp_apikey,
                placeholder="Enter API key for automation",
                type="password",
                label_visibility="collapsed",
                key="whatsapp_apikey_input"
            )
            
        # Display instructions for CallMeBot key
        st.markdown("""
            <div style="
                background: rgba(79, 70, 229, 0.04);
                border: 1px solid rgba(79, 70, 229, 0.15);
                border-radius: 12px;
                padding: 12px 16px;
                margin-top: 8px;
                margin-bottom: 12px;
            ">
                <p style="color: #4f46e5; font-size: 0.82rem; font-weight: 700; margin: 0 0 6px 0; display: flex; align-items: center; gap: 6px;">
                    🤖 How to get your FREE WhatsApp Automation Key:
                </p>
                <ol style="color: #475569; font-size: 0.78rem; margin: 0; padding-left: 18px; line-height: 1.5;">
                    <li>Add the active bot number <b>+34 694 23 41 84</b> (CallMeBot) to your contacts.</li>
                    <li>Send the message <code>I allow callmebot to send me messages</code> via WhatsApp.</li>
                    <li>The bot will reply with your unique <b>API Key</b> (usually within 1–2 minutes). Enter it above and save!</li>
                </ol>
                <div style="margin-top: 10px; margin-bottom: 5px;">
                    <a href="https://wa.me/34694234184?text=I%20allow%20callmebot%20to%20send%20me%20messages" target="_blank" style="
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        background: #25D366;
                        color: white;
                        text-decoration: none;
                        padding: 8px 14px;
                        border-radius: 8px;
                        font-size: 0.78rem;
                        font-weight: 700;
                        box-shadow: 0 2px 5px rgba(37, 211, 102, 0.2);
                        transition: all 0.2s ease;
                    ">
                        💬 Click Here to Chat & Get Key Instantly
                    </a>
                </div>
                <p style="color: #64748b; font-size: 0.72rem; margin: 6px 0 0 0; font-style: italic;">
                    ⏰ <b>Automation Schedule:</b> A summary will be sent automatically to your WhatsApp every day at <b>9:30 PM</b> in the background.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Save button taking full width below
        if st.button("💾 Save Contact & Automation Settings", use_container_width=True, key="save_whatsapp_settings_btn"):
            cleaned_phone = "".join(c for c in phone_number if c.isdigit())
            # Auto prefix country code '91' for standard 10-digit Indian numbers
            if len(cleaned_phone) == 10:
                cleaned_phone = "91" + cleaned_phone
                
            st.session_state.whatsapp_phone = cleaned_phone
            st.session_state.whatsapp_apikey = apikey_val.strip()
            
            # Save to persistent file
            settings = load_settings()
            settings["whatsapp_phone"] = cleaned_phone
            settings["whatsapp_apikey"] = apikey_val.strip()
            save_settings(settings)
            
            st.success("Notification settings saved successfully!")
            st.rerun()
            
        # Daily Summary Generator
        st.markdown('<p style="color: #475569; font-size: 0.88rem; font-weight: 600; margin-top: 15px; margin-bottom: 8px;">📊 Today\'s WhatsApp Summary Compiler</p>', unsafe_allow_html=True)
        
        # Calculate today's entries
        today_date = datetime.date.today()
        df_today = df_expenses[df_expenses['Date'] == today_date]
        
        if not df_today.empty:
            total_spent = df_today['Amount'].sum()
            entries_count = len(df_today)
            
            # Format the breakdown message
            message_lines = [
                "🌱 *Bunny's Farm Daily Expense Summary*",
                f"📅 *Date:* {today_date.strftime('%d-%b-%Y')}",
                "-----------------------------",
                f"Total Spent Today: *₹{total_spent:,.2f}*",
                f"Total Transactions: *{entries_count} entries*",
                "",
                "*Breakdown:*"
            ]
            
            for idx, row in df_today.sort_values(by="Timestamp", ascending=True).iterrows():
                # Format timestamp safely
                time_str = row['Timestamp'].strftime('%I:%M %p') if isinstance(row['Timestamp'], datetime.datetime) else ""
                message_lines.append(f"• {row['Expenditure']}: *₹{row['Amount']:,.2f}* ({time_str})")
                
            message_lines.append("-----------------------------")
            message_lines.append("_Generated by FinTrack Expense Tracker._")
            
            summary_text = "\n".join(message_lines)
            
            # Show preview
            st.text_area("Message Preview", value=summary_text, height=140, disabled=True, key="whatsapp_summary_preview")
            
            # Create WhatsApp URL
            encoded_text = urllib.parse.quote(summary_text)
            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
            if st.session_state.whatsapp_phone:
                whatsapp_url = f"https://api.whatsapp.com/send?phone={st.session_state.whatsapp_phone}&text={encoded_text}"
                
            # Render link button
            st.link_button("💬 Send Daily Summary via WhatsApp", whatsapp_url, use_container_width=True)
        else:
            st.info("No transactions logged today yet. Record some expenses to compile a summary!")
            
        st.divider()
        col_maint_title, col_maint_refresh, col_maint_date = st.columns([10, 3, 5])
        with col_maint_title:
            st.markdown("""
                <div class="section-header" style="margin-top: 5px;">
                    <div>
                        <h3 class="section-title">Record Maintenance</h3>
                        <p class="section-subtitle">Permanently delete incorrect or unwanted records from the ledger</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_maint_refresh:
            st.markdown('<div style="padding-top: 8px;"></div>', unsafe_allow_html=True)
            if st.button("🔄 Refresh", use_container_width=True, key="maint_refresh_btn"):
                st.rerun()
        with col_maint_date:
            st.markdown('<div style="padding-top: 8px;"></div>', unsafe_allow_html=True)
            delete_date = st.date_input("Select Date for Deletion", datetime.date.today(), max_value=datetime.date.today(), key="delete_date_picker", label_visibility="collapsed")
        
        df_to_delete = df_expenses[df_expenses['Date'] == delete_date]
        if not df_to_delete.empty:
            df_display = df_to_delete.copy()
            df_display['Time'] = df_display['Timestamp'].dt.strftime('%I:%M %p')
            df_display['Select'] = False
            
            # Reorder columns to put Select first, followed by Time, Amount, and Expenditure
            df_display = df_display[['Select', 'Time', 'Amount', 'Expenditure']]
            
            # Render using st.data_editor
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Check this box to select this transaction for deletion",
                        default=False,
                    ),
                    "Time": st.column_config.TextColumn("Time", disabled=True),
                    "Amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f", disabled=True),
                    "Expenditure": st.column_config.TextColumn("Expenditure Details", disabled=True),
                },
                disabled=["Time", "Amount", "Expenditure"],
                use_container_width=True,
                hide_index=True,
                key="delete_records_editor"
            )
            
            selected_indices = edited_df[edited_df['Select'] == True].index.tolist()
            
            if selected_indices:
                st.markdown('<div class="danger-btn-container" style="margin-top: 15px;">', unsafe_allow_html=True)
                btn_label = "🗑️ Delete Selected Entry" if len(selected_indices) == 1 else f"🗑️ Delete {len(selected_indices)} Selected Entries"
                if st.button(btn_label, use_container_width=True):
                    # Delete physical files from disk first
                    for idx in selected_indices:
                        if idx in df_expenses.index:
                            img_field = df_expenses.loc[idx, 'Receipt_Image']
                            if img_field:
                                for img_path in [p.strip() for p in img_field.split(",") if p.strip()]:
                                    if os.path.exists(img_path):
                                        try:
                                            os.remove(img_path)
                                        except Exception:
                                            pass
                    df_expenses = df_expenses.drop(selected_indices)
                    if save_expenses(df_expenses):
                        st.success(f"Successfully deleted {len(selected_indices)} record(s)!")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #64748b; font-size: 0.85rem; font-style: italic; margin-top: 10px;">💡 Select the checkboxes in the table above to choose which entries you want to delete.</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p style="color: #64748b; font-size: 0.88rem; font-style: italic; margin-top: 10px;">No entries to manage for {delete_date.strftime("%d-%b-%Y")}.</p>', unsafe_allow_html=True)

else:
    # ------------------ REGULAR USER MODE ------------------

    with st.form("public_entry_form", clear_on_submit=True):
        # Combined Header & Smart Voice Assistant side-by-side
        components.html(r"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
            body {
                margin: 0;
                padding: 0;
                font-family: 'Outfit', sans-serif;
                background: transparent;
                overflow: hidden;
            }
            .header-container {
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
                width: 100%;
                height: 56px;
                box-sizing: border-box;
            }
            .text-section {
                display: flex;
                flex-direction: column;
                justify-content: center;
                min-width: 0;
                flex-grow: 1;
            }
            .title {
                font-size: 1.15rem;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
                line-height: 1.2;
            }
            .subtitle {
                font-size: 0.75rem;
                color: #64748b;
                margin: 2px 0 0 0;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                transition: all 0.3s ease;
            }
            
            /* Compact Mic Section */
            .mic-section {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-shrink: 0;
                position: relative;
            }
            .mic-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: none;
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 1.15rem;
                box-shadow: 0 4px 10px rgba(79, 70, 229, 0.2);
                transition: all 0.2s ease;
                position: relative;
                z-index: 5;
            }
            .mic-btn:active {
                transform: scale(0.92);
            }
            
            /* Listening State */
            .listening .mic-btn {
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                animation: pulse-ring 1.5s infinite;
            }
            @keyframes pulse-ring {
                0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
                70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
                100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
            }
            
            /* Listening text indicator */
            .status-text {
                font-size: 0.72rem;
                font-weight: 700;
                color: #ef4444;
                display: none;
                animation: fadeIn 0.2s ease;
                white-space: nowrap;
            }
            .listening .status-text {
                display: block;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateX(5px); }
                to { opacity: 1; transform: translateX(0); }
            }
        </style>
        </head>
        <body>
        <div class="header-container" id="container">
            <div class="text-section">
                <h3 class="title">📝 Record New Expense</h3>
                <p class="subtitle" id="subtitle-text">Add details below to log transaction</p>
            </div>
            <div class="mic-section">
                <span class="status-text" id="status-el">Listening...</span>
                <button type="button" class="mic-btn" id="mic-btn" onclick="toggleListening()" title="Smart Voice Assistant">🎙️</button>
            </div>
        </div>

        <script>
            let recognition = null;
            let isListening = false;
            
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-IN'; // Optimized for Indian accents & keywords like "rupees"
                
                recognition.onstart = () => {
                    isListening = true;
                    document.getElementById('container').classList.add('listening');
                    document.getElementById('subtitle-text').innerText = 'Speak expenditure & amount now...';
                    document.getElementById('subtitle-text').style.color = '#ef4444';
                    document.getElementById('subtitle-text').style.fontWeight = '600';
                    document.getElementById('mic-btn').innerText = '🛑';
                };
                
                recognition.onend = () => {
                    isListening = false;
                    document.getElementById('container').classList.remove('listening');
                    document.getElementById('subtitle-text').innerText = 'Add details below to log transaction';
                    document.getElementById('subtitle-text').style.color = '#64748b';
                    document.getElementById('subtitle-text').style.fontWeight = 'normal';
                    document.getElementById('mic-btn').innerText = '🎙️';
                };
                
                recognition.onerror = (event) => {
                    console.error(event.error);
                    let errMsg = 'Click mic to try again';
                    if (event.error === 'not-allowed') errMsg = 'Mic permission denied';
                    document.getElementById('subtitle-text').innerText = errMsg;
                    document.getElementById('subtitle-text').style.color = '#ef4444';
                    isListening = false;
                    document.getElementById('container').classList.remove('listening');
                    document.getElementById('mic-btn').innerText = '🎙️';
                };
                
                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    
                    // Extract amount and expenditure from the vocal command
                    let amount = null;
                    let expenditure = "";
                    
                    const numMatch = transcript.match(/\d+(\.\d+)?/);
                    if (numMatch) {
                        amount = parseFloat(numMatch[0]);
                        
                        // Expenditure is everything before the number, cleaned up
                        const numberIndex = transcript.indexOf(numMatch[0]);
                        expenditure = transcript.substring(0, numberIndex).trim();
                        
                        // Strip trailing/leading connector words
                        expenditure = expenditure.replace(/\b(for|of|worth|spent|rs|rupees|rupee)\b/gi, '').trim();
                    } else {
                        expenditure = transcript;
                    }
                    
                    if (expenditure) {
                        expenditure = expenditure.charAt(0).toUpperCase() + expenditure.slice(1);
                    }
                    
                    // Send to parent window
                    window.parent.postMessage({
                        type: 'voice_input',
                        expenditure: expenditure,
                        amount: amount,
                        raw: transcript
                    }, '*');
                };
            } else {
                document.getElementById('mic-btn').disabled = true;
                document.getElementById('mic-btn').style.background = '#94a3b8';
                document.getElementById('subtitle-text').innerText = 'Voice input not supported on this browser';
            }
            
            function toggleListening() {
                if (!recognition) return;
                if (isListening) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            }
        </script>
        </body>
        </html>
        """, height=56)

        st.markdown('<label class="custom-input-label">Expenditure Details</label>', unsafe_allow_html=True)
        expenditure = st.text_input("Expenditure", placeholder="e.g. Tractor fuel, seeds, labor...", label_visibility="collapsed")
        
        # Side-by-side columns for Amount and Image Picker
        col_amt, col_img = st.columns([1, 1])
        
        with col_amt:
            st.markdown('<label class="custom-input-label">Amount Spent (₹)</label>', unsafe_allow_html=True)
            amount = st.number_input("Amount (₹)", min_value=0.0, value=None, step=10.0, format="%.2f", placeholder="0.00", label_visibility="collapsed")
            
        with col_img:
            st.markdown('<label class="custom-input-label">📸 Photo / Receipt</label>', unsafe_allow_html=True)
            components.html(r"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
                body {
                    margin: 0;
                    padding: 0;
                    font-family: 'Outfit', sans-serif;
                    background: transparent;
                    overflow: hidden;
                }
                .dotted-box {
                    border: 2px dashed #cbd5e1;
                    border-radius: 10px;
                    height: 44px; /* Matches Streamlit input height perfectly */
                    display: flex;
                    flex-direction: row;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    background: rgba(248, 250, 252, 0.6);
                    box-sizing: border-box;
                    padding: 0 6px;
                }
                .dotted-box:hover {
                    border-color: #4f46e5;
                    background: rgba(79, 70, 229, 0.02);
                }
                .dotted-box:active {
                    transform: scale(0.98);
                }
                .state-container {
                    width: 100%;
                    height: 100%;
                    display: flex;
                    flex-direction: row;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                }
                .icon-container {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                }
                .camera-icon {
                    font-size: 1.3rem;
                    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.02));
                }
                .plus-badge {
                    position: absolute;
                    bottom: -3px;
                    right: -5px;
                    background: #4f46e5;
                    color: white;
                    border-radius: 50%;
                    width: 13px;
                    height: 13px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.55rem;
                    font-weight: 800;
                    border: 1.5px solid white;
                }
                .box-text {
                    font-size: 0.8rem;
                    font-weight: 600;
                    color: #64748b;
                    margin: 0;
                    white-space: nowrap;
                }
                
                /* Choice Buttons styling */
                .choice-btn {
                    flex: 1;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    background: white;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    font-size: 0.72rem;
                    font-weight: 600;
                    color: #334155;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
                }
                .choice-btn:hover {
                    background: #f8fafc;
                    border-color: #4f46e5;
                    color: #4f46e5;
                }
                .choice-btn:active {
                    transform: scale(0.95);
                }
                .close-btn {
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.7rem;
                    font-weight: bold;
                    color: #94a3b8;
                    cursor: pointer;
                    border-radius: 50%;
                    transition: all 0.2s ease;
                }
                .close-btn:hover {
                    background: #f1f5f9;
                    color: #ef4444;
                }
                
                /* Multi-Image List styling */
                .thumb-list {
                    display: flex;
                    flex-direction: row;
                    gap: 5px;
                    align-items: center;
                    overflow: hidden;
                    max-width: calc(100% - 42px);
                }
                .thumb-wrapper {
                    position: relative;
                    width: 38px;
                    height: 32px;
                    border-radius: 6px;
                    border: 1px solid #cbd5e1;
                    overflow: hidden;
                    flex-shrink: 0;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                }
                .thumb-img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
                .thumb-clear {
                    position: absolute;
                    top: 1px;
                    right: 1px;
                    background: rgba(15, 23, 42, 0.75);
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 11px;
                    height: 11px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    font-size: 0.45rem;
                    font-weight: bold;
                    transition: all 0.2s ease;
                    z-index: 10;
                    padding: 0;
                    line-height: 1;
                }
                .thumb-clear:hover {
                    background: rgba(239, 68, 68, 0.95);
                    transform: scale(1.1);
                }
                .add-more-btn {
                    width: 34px;
                    height: 32px;
                    border: 1px dashed #cbd5e1;
                    border-radius: 6px;
                    background: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    font-size: 1.1rem;
                    font-weight: 600;
                    color: #64748b;
                    transition: all 0.2s ease;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
                    flex-shrink: 0;
                }
                .add-more-btn:hover {
                    border-color: #4f46e5;
                    color: #4f46e5;
                    background: #f8fafc;
                }
                .add-more-btn:active {
                    transform: scale(0.95);
                }
            </style>
            </head>
            <body>
            <div class="dotted-box" id="box">
                <!-- Default State -->
                <div id="normal-state" class="state-container" onclick="showMenu(event)">
                    <div class="icon-container">
                        <span class="camera-icon">📸</span>
                        <span class="plus-badge">+</span>
                    </div>
                    <span class="box-text">Add Photo</span>
                </div>
                
                <!-- Choice State -->
                <div id="choice-state" class="state-container" style="display: none;">
                    <div class="choice-btn" onclick="triggerInput('camera-el', event)">
                        📷 Camera
                    </div>
                    <div class="choice-btn" onclick="triggerInput('file-el', event)">
                        📁 Gallery
                    </div>
                    <div class="close-btn" onclick="hideMenu(event)">✕</div>
                </div>
                
                <!-- Multi-Image List State -->
                <div id="list-state" class="state-container" style="display: none; justify-content: flex-start; padding: 0 2px;">
                    <div class="thumb-list" id="thumb-list"></div>
                    <div class="add-more-btn" id="add-more-btn" onclick="showMenu(event)" title="Add another photo">+</div>
                </div>
            </div>
            
            <!-- Hidden Native Inputs -->
            <input type="file" id="camera-el" accept="image/*" capture="environment" style="display: none;" onchange="handleFile(this)">
            <input type="file" id="file-el" accept="image/*" style="display: none;" onchange="handleFile(this)">
            
            <script>
                let images = [];
                const MAX_IMAGES = 3;
                
                function showMenu(event) {
                    if (event) event.stopPropagation();
                    document.getElementById('normal-state').style.display = 'none';
                    document.getElementById('list-state').style.display = 'none';
                    document.getElementById('choice-state').style.display = 'flex';
                }
                
                function hideMenu(event) {
                    if (event) event.stopPropagation();
                    document.getElementById('choice-state').style.display = 'none';
                    updateUI();
                }
                
                function triggerInput(id, event) {
                    if (event) event.stopPropagation();
                    document.getElementById(id).click();
                }
                
                function handleFile(input) {
                    if (input.files && input.files[0]) {
                        const file = input.files[0];
                        const reader = new FileReader();
                        
                        reader.onload = function(e) {
                            const img = new Image();
                            img.onload = function() {
                                // Create HTML5 canvas for compression
                                const canvas = document.createElement('canvas');
                                let width = img.width;
                                let height = img.height;
                                
                                // Set maximum dimensions (perfect for receipts, keeps text sharp)
                                const MAX_WIDTH = 1024;
                                const MAX_HEIGHT = 1024;
                                
                                if (width > height) {
                                    if (width > MAX_WIDTH) {
                                        height *= MAX_WIDTH / width;
                                        width = MAX_WIDTH;
                                    }
                                } else {
                                    if (height > MAX_HEIGHT) {
                                        width *= MAX_HEIGHT / height;
                                        height = MAX_HEIGHT;
                                    }
                                }
                                
                                canvas.width = width;
                                canvas.height = height;
                                
                                // Draw and compress
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(img, 0, 0, width, height);
                                
                                // Export as high-quality JPEG (quality: 0.75)
                                const compressedBase64 = canvas.toDataURL('image/jpeg', 0.75);
                                
                                // Add compressed image to collection
                                images.push({
                                    base64: compressedBase64,
                                    filename: file.name.replace(/\.[^/.]+$/, "") + ".jpg"
                                });
                                
                                // Clear input so same image can be reselected if deleted
                                input.value = '';
                                
                                // Update UI and notify Streamlit
                                updateUI();
                                notifyParent();
                            };
                            img.src = e.target.result;
                        };
                        
                        reader.readAsDataURL(file);
                    } else {
                        hideMenu();
                    }
                }
                
                function removeImage(index, event) {
                    if (event) event.stopPropagation();
                    images.splice(index, 1);
                    updateUI();
                    notifyParent();
                }
                
                function updateUI() {
                    document.getElementById('choice-state').style.display = 'none';
                    
                    if (images.length === 0) {
                        document.getElementById('list-state').style.display = 'none';
                        document.getElementById('normal-state').style.display = 'flex';
                    } else {
                        document.getElementById('normal-state').style.display = 'none';
                        document.getElementById('list-state').style.display = 'flex';
                        
                        // Render thumbnails
                        const listEl = document.getElementById('thumb-list');
                        listEl.innerHTML = '';
                        
                        images.forEach((img, idx) => {
                            const wrapper = document.createElement('div');
                            wrapper.className = 'thumb-wrapper';
                            
                            const image = document.createElement('img');
                            image.className = 'thumb-img';
                            image.src = img.base64;
                            
                            const clearBtn = document.createElement('button');
                            clearBtn.type = 'button';
                            clearBtn.className = 'thumb-clear';
                            clearBtn.innerHTML = '✕';
                            clearBtn.onclick = (e) => removeImage(idx, e);
                            
                            wrapper.appendChild(image);
                            wrapper.appendChild(clearBtn);
                            listEl.appendChild(wrapper);
                        });
                        
                        // Manage add button visibility
                        const addBtn = document.getElementById('add-more-btn');
                        if (images.length >= MAX_IMAGES) {
                            addBtn.style.display = 'none';
                        } else {
                            addBtn.style.display = 'flex';
                        }
                    }
                }
                
                function notifyParent() {
                    window.parent.postMessage({
                        type: 'image_input',
                        images: JSON.stringify(images)
                    }, '*');
                }
            </script>
            </body>
            </html>
            """, height=44)
            
        # Hidden inputs to hold the base64 and filename values (populated by JS bridge)
        st.markdown('<div class="hidden-input-container">', unsafe_allow_html=True)
        image_base64 = st.text_area("Image Base64", value="", key="hidden_image_base64", label_visibility="collapsed")
        image_filename = st.text_input("Image Filename", value="", key="hidden_image_filename", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # We auto-generate the Date and Time in the background
        st.markdown('<div class="primary-btn-container" style="margin-top: 20px;">', unsafe_allow_html=True)
        submit_clicked = st.form_submit_button("Submit Transaction", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if submit_clicked:
            if expenditure.strip() == "":
                st.error("Please enter the expenditure details.")
            elif amount is None or amount <= 0:
                st.error("Please enter a valid amount.")
            else:
                # Automate the current date & timestamp creation
                current_time = datetime.datetime.now()
                
                # Process custom image picker base64 if any (supports JSON array of multiple images)
                saved_image_paths = []
                if image_base64 and image_base64.strip() != "":
                    # Ensure uploads directory exists
                    os.makedirs("uploads", exist_ok=True)
                    
                    # Try to parse as a JSON array of multiple images
                    import json
                    is_json_list = False
                    try:
                        parsed_images = json.loads(image_base64)
                        if isinstance(parsed_images, list):
                            is_json_list = True
                    except Exception:
                        is_json_list = False
                        
                    if is_json_list:
                        for idx, img_info in enumerate(parsed_images):
                            img_b64 = img_info.get("base64", "")
                            if img_b64:
                                try:
                                    header, base64_str = img_b64.split(";base64,")
                                    file_data = base64.b64decode(base64_str)
                                    
                                    file_ext = ".jpg"
                                    if "png" in header:
                                        file_ext = ".png"
                                    elif "jpeg" in header:
                                        file_ext = ".jpg"
                                    elif "gif" in header:
                                        file_ext = ".gif"
                                        
                                    clean_exp_name = "".join(c for c in expenditure if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                                    if not clean_exp_name:
                                        clean_exp_name = "receipt"
                                        
                                    filename = f"{current_time.strftime('%Y%m%d_%H%M%S')}_{clean_exp_name}_{idx}{file_ext}"
                                    saved_path = os.path.join("uploads", filename)
                                    
                                    with open(saved_path, "wb") as f:
                                        f.write(file_data)
                                    saved_image_paths.append(saved_path)
                                except Exception as e:
                                    st.error(f"Error processing image {idx+1}: {e}")
                    else:
                        # Legacy single base64 string
                        try:
                            header, base64_str = image_base64.split(";base64,")
                            file_data = base64.b64decode(base64_str)
                            
                            file_ext = ".jpg"
                            if "png" in header:
                                file_ext = ".png"
                            elif "jpeg" in header:
                                file_ext = ".jpg"
                            elif "gif" in header:
                                file_ext = ".gif"
                                
                            clean_exp_name = "".join(c for c in expenditure if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                            if not clean_exp_name:
                                clean_exp_name = "receipt"
                                
                            filename = f"{current_time.strftime('%Y%m%d_%H%M%S')}_{clean_exp_name}{file_ext}"
                            saved_path = os.path.join("uploads", filename)
                            
                            with open(saved_path, "wb") as f:
                                f.write(file_data)
                            saved_image_paths.append(saved_path)
                        except Exception as e:
                            st.error(f"Error processing captured photo: {e}")
                            
                saved_image_path = ", ".join(saved_image_paths) if saved_image_paths else ""
                
                new_entry = pd.DataFrame([{
                    "Timestamp": current_time,
                    "Date": current_time.date(),
                    "Amount": amount,
                    "Expenditure": expenditure.strip(),
                    "Receipt_Image": saved_image_path
                }])
                
                df_expenses = pd.concat([df_expenses, new_entry], ignore_index=True)
                if save_expenses(df_expenses):
                    # Set elegant toast message and trigger rerun
                    st.session_state.show_toast = f"Logged successfully: ₹{amount:,.2f} for \"{expenditure.strip()}\""
                    st.rerun()
    st.caption("🔒 Analytics and history records are restricted to Admins. Click the 'Admin' button above to log in.")

# Footer
st.markdown("""
    <div class="footer-text">
        FinTrack Expense App • Made with Streamlit
    </div>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# Invisible JavaScript styling bridge for Streamlit buttons
# ----------------------------------------------------
components.html("""
<script>
    const styleButtons = () => {
        const doc = window.parent.document;
        if (!doc) return;
        
        const buttons = doc.querySelectorAll('button');
        buttons.forEach(btn => {
            const text = btn.textContent || '';
            
            // Check for Logout button
            if (text.includes('Logout')) {
                if (!btn.classList.contains('logout-btn-custom')) {
                    btn.classList.add('logout-btn-custom');
                }
            }
            // Check for Expenses button
            else if (text.includes('Expenses')) {
                if (!btn.classList.contains('expenses-btn-custom')) {
                    btn.classList.add('expenses-btn-custom');
                }
            }
            // Check for Admin button
            else if (text.includes('Admin')) {
                if (!btn.classList.contains('admin-btn-custom')) {
                    btn.classList.add('admin-btn-custom');
                }
            }
            // Check for WhatsApp button
            else if (text.includes('WhatsApp')) {
                if (!btn.classList.contains('whatsapp-btn-custom')) {
                    btn.classList.add('whatsapp-btn-custom');
                }
            }
            // Check for Download button
            else if (text.includes('Download')) {
                if (!btn.classList.contains('download-btn-custom')) {
                    btn.classList.add('download-btn-custom');
                }
            }
            // Check for Delete button
            else if (text.includes('Delete')) {
                if (!btn.classList.contains('danger-btn-custom')) {
                    btn.classList.add('danger-btn-custom');
                }
            }
            // Check for Verify button
            else if (text.includes('Verify')) {
                if (!btn.classList.contains('verify-btn-custom')) {
                    btn.classList.add('verify-btn-custom');
                }
            }
            // Check for Submit button
            else if (text.includes('Submit')) {
                if (!btn.classList.contains('submit-btn-custom')) {
                    btn.classList.add('submit-btn-custom');
                }
            }
        });
    };
    
    // Execute immediately
    styleButtons();
    
    // Run periodically to catch Streamlit state changes and tab switches
    if (!window.buttonSpacerInterval) {
        window.buttonSpacerInterval = setInterval(styleButtons, 200);
    }

    // --- React controlled input setter bypass ---
    const setReactInputValue = (inputElement, value) => {
        if (!inputElement) return;
        const valueSetter = Object.getOwnPropertyDescriptor(inputElement, '__proto__', 'value') || 
                            Object.getOwnPropertyDescriptor(inputElement, 'value');
        const prototype = Object.getPrototypeOf(inputElement);
        const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value');
        
        if (prototypeValueSetter && prototypeValueSetter.set) {
            prototypeValueSetter.set.call(inputElement, value);
        } else if (valueSetter && valueSetter.set) {
            valueSetter.set.call(inputElement, value);
        } else {
            inputElement.value = value;
        }
        inputElement.dispatchEvent(new Event('input', { bubbles: true }));
        inputElement.dispatchEvent(new Event('change', { bubbles: true }));
    };

    // Listen for messages from the voice component or custom image-picker on the PARENT window
    window.parent.addEventListener('message', (event) => {
        if (!event.data) return;
        
        if (event.data.type === 'voice_input') {
            const data = event.data;
            const doc = window.parent.document;
            if (!doc) return;
            
            // Find expenditure input and amount input
            const inputs = doc.querySelectorAll('input');
            let expInput = null;
            let amtInput = null;
            
            inputs.forEach(input => {
                const placeholder = input.getAttribute('placeholder') || '';
                if (placeholder.includes('Tractor fuel') || placeholder.includes('seeds')) {
                    expInput = input;
                } else if (placeholder.includes('0.00') || input.getAttribute('type') === 'number') {
                    amtInput = input;
                }
            });
            
            // Fallbacks
            if (!expInput) {
                const textInputs = doc.querySelectorAll('div[data-testid="stTextInput"] input');
                if (textInputs.length > 0) expInput = textInputs[0];
            }
            if (!amtInput) {
                const numInputs = doc.querySelectorAll('div[data-testid="stNumberInput"] input');
                if (numInputs.length > 0) amtInput = numInputs[0];
            }
            
            // Set the values
            if (expInput && data.expenditure) {
                setReactInputValue(expInput, data.expenditure);
            }
            
            if (amtInput && data.amount !== null) {
                setReactInputValue(amtInput, data.amount);
            }
        }
        else if (event.data.type === 'image_input') {
            const data = event.data;
            const doc = window.parent.document;
            if (!doc) return;
            
            const hiddenContainer = doc.querySelector('.hidden-input-container');
            if (hiddenContainer) {
                const base64Area = hiddenContainer.querySelector('textarea');
                const filenameInput = hiddenContainer.querySelector('input');
                
                if (base64Area) {
                    const val = data.images ? data.images : data.base64;
                    setReactInputValue(base64Area, val);
                }
                if (filenameInput) {
                    const fname = data.images ? "multi_upload.json" : data.filename;
                    setReactInputValue(filenameInput, fname);
                }
            }
        }
    });
</script>
""", height=0, width=0)

import streamlit as st
import pandas as pd
import datetime
import os
import json
import base64
import urllib.parse
import plotly.express as px
import streamlit.components.v1 as components
import shutil

# Copy generated circular farm graphic to workspace if not present
src_img = r"C:\Users\KhanushM\.gemini\antigravity\brain\e8db8cce-3075-4503-a0a9-ecd600b118a1\bunny_farm_login_graphic_1782467935691.png"
dst_img = "bunny_farm_login_graphic.png"
if os.path.exists(src_img) and not os.path.exists(dst_img):
    try:
        shutil.copy(src_img, dst_img)
    except Exception:
        pass


# ----------------------------------------------------
# Page Configuration
# ----------------------------------------------------
st.set_page_config(
    page_title="Bunny's Farm - Expense Tracker",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="auto"
)

# Settings Persistence Helpers
SETTINGS_FILE = "settings.json"

def load_settings():
    default_settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
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
if "show_invoice_preview" not in st.session_state:
    st.session_state.show_invoice_preview = False

# Show premium, auto-dismissing toast notification upon successful submission
if st.session_state.show_toast:
    st.toast(st.session_state.show_toast, icon="🎉")
    st.session_state.show_toast = None

# Load persistent settings
app_settings = load_settings()

# ----------------------------------------------------
# Custom Premium Styling
# ----------------------------------------------------
# Load custom styling from style.css (resolved relative to script directory)
style_css_path = os.path.join(os.path.dirname(__file__), "style.css")
if os.path.exists(style_css_path):
    with open(style_css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.warning("style.css not found. Please ensure it is present in the application directory.")

# ----------------------------------------------------
# Data Storage Functions (Excel backend)
# ----------------------------------------------------
EXCEL_FILE = "expenses.xlsx"

def num_to_words(number):
    """Converts a float amount to words using the Indian numbering system (Lakhs, Crores)."""
    if number == 0:
        return "Zero Rupees Only"
        
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", 
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def helper(n):
        if n < 20:
            return units[n]
        elif n < 100:
            return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
        elif n < 1000:
            return units[n // 100] + " Hundred" + (" and " + helper(n % 100) if n % 100 != 0 else "")
        return ""
        
    num_int = int(number)
    num_dec = int(round((number - num_int) * 100))
    
    words = ""
    
    # Crores (1,00,00,000)
    if num_int >= 10000000:
        words += helper(num_int // 10000000) + " Crore "
        num_int %= 10000000
        
    # Lakhs (1,00,000)
    if num_int >= 100000:
        words += helper(num_int // 100000) + " Lakh "
        num_int %= 100000
        
    # Thousands (1,000)
    if num_int >= 1000:
        words += helper(num_int // 1000) + " Thousand "
        num_int %= 1000
        
    # Hundreds & below
    if num_int > 0:
        words += helper(num_int)
        
    words = words.strip() + " Rupees"
    
    if num_dec > 0:
        words += " and " + helper(num_dec) + " Paise"
        
    return words + " Only"

def generate_invoice_html(df, date_label, invoice_no, po_no, bank_info):
    """Generates a pixel-perfect, print-ready HTML/CSS billing invoice matching the user's reference mockup."""
    # Calculate totals
    total = df['Amount'].sum()
    total_words = num_to_words(total)
    
    # Generate rows
    rows_html = ""
    for idx, row in df.reset_index(drop=True).iterrows():
        desc = row['Expenditure']
        amount = row['Amount']
        
        # Format the date of the expense beautifully
        date_str = ""
        if 'Date' in row and not pd.isna(row['Date']):
            if hasattr(row['Date'], 'strftime'):
                date_str = row['Date'].strftime('%d-%b-%Y')
            else:
                date_str = str(row['Date'])
                
        rows_html += f"""
        <tr>
            <td style="text-align: center;">{idx + 1}</td>
            <td style="text-align: center; color: #475569; font-size: 11px;">{date_str}</td>
            <td>{desc}</td>
            <td style="text-align: center;">1</td>
            <td style="text-align: right;">₹{amount:,.2f}</td>
            <td style="text-align: right; font-weight: 500;">₹{amount:,.2f}</td>
        </tr>
        """
        
    # Prefill empty rows if less than 4 to keep the structure beautiful
    remaining_rows = 4 - len(df)
    if remaining_rows > 0:
        for i in range(remaining_rows):
            rows_html += """
            <tr style="height: 35px;">
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            """
            
    # Bank info
    online_txn = bank_info.get("online_txn", "7842339268")
    bank_name = bank_info.get("bank_name", "BANK OF BARODA")
    acc_name = bank_info.get("acc_name", "MYLU KHANUSH")
    acc_num = bank_info.get("acc_num", "55250100012962")
    ifsc = bank_info.get("ifsc", "BARB0DARGAM")
    branch = bank_info.get("branch", "Dargamitta, NELLORE")
    
    # Date formatting
    invoice_date = datetime.date.today().strftime("%d %B %Y")
    due_date = (datetime.date.today() + datetime.timedelta(days=15)).strftime("%d %B %Y")
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Invoice {invoice_no}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Great+Vibes&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                color: #1e293b;
                margin: 0;
                padding: 0;
                background-color: #f1f5f9;
                -webkit-print-color-adjust: exact;
            }}
            .invoice-card {{
                background: #ffffff;
                max-width: 850px;
                margin: 20px auto;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.05);
                box-sizing: border-box;
                border: 1px solid #e2e8f0;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                border-bottom: 2px solid #f1f5f9;
                padding-bottom: 25px;
                margin-bottom: 25px;
            }}
            .logo-area {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .logo-icon {{
                background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                color: white;
                width: 45px;
                height: 45px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: 'Outfit', sans-serif;
                font-size: 24px;
                font-weight: 800;
            }}
            .logo-text {{
                font-family: 'Outfit', sans-serif;
            }}
            .logo-title {{
                font-size: 20px;
                font-weight: 800;
                color: #0f172a;
                margin: 0;
                letter-spacing: 0.5px;
            }}
            .logo-subtitle {{
                font-size: 11px;
                color: #64748b;
                margin: 2px 0 0 0;
                font-weight: 500;
            }}
            .invoice-title-area {{
                text-align: right;
            }}
            .invoice-title {{
                font-family: 'Outfit', sans-serif;
                font-size: 32px;
                font-weight: 800;
                color: #1e3a8a;
                margin: 0;
                letter-spacing: 1px;
            }}
            .invoice-num {{
                font-size: 14px;
                color: #475569;
                font-weight: 600;
                margin: 5px 0 0 0;
            }}
            .details-grid {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
                font-size: 12px;
                line-height: 1.6;
            }}
            .section-label {{
                font-size: 11px;
                font-weight: 700;
                color: #2563eb;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                margin-bottom: 8px;
            }}
            .company-name {{
                font-size: 13px;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 4px;
            }}
            .address-text {{
                color: #475569;
            }}
            .tax-info {{
                margin-top: 6px;
                font-weight: 500;
                color: #334155;
            }}
            .invoice-meta {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 10px;
                padding-left: 10px;
                border-left: 2px solid #f1f5f9;
            }}
            .meta-item {{
                margin-bottom: 2px;
            }}
            .meta-label {{
                font-weight: 700;
                color: #1e3a8a;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .meta-val {{
                color: #334155;
                font-size: 13px;
                font-weight: 500;
                margin-top: 2px;
            }}
            .table-container {{
                margin-bottom: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }}
            th {{
                background-color: #1e3a8a;
                color: white;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.5px;
                padding: 10px 12px;
                border: 1px solid #1e3a8a;
            }}
            th:first-child {{
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
            }}
            th:last-child {{
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #e2e8f0;
                color: #334155;
            }}
            tr:nth-child(even) td {{
                background-color: #f8fafc;
            }}
            .totals-container {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-top: 20px;
            }}
            .totals-left {{
                flex: 1.2;
                margin-right: 40px;
            }}
            .totals-right {{
                flex: 1;
                font-size: 12px;
            }}
            .word-amount {{
                background-color: #f8fafc;
                border: 1px dashed #cbd5e1;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 20px;
            }}
            .word-title {{
                font-weight: 700;
                color: #1e3a8a;
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }}
            .word-val {{
                font-weight: 500;
                color: #475569;
                line-height: 1.4;
            }}
            .bank-details {{
                border-left: 3px solid #2563eb;
                padding-left: 12px;
            }}
            .bank-title {{
                font-weight: 700;
                color: #1e3a8a;
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 6px;
            }}
            .bank-row {{
                margin-bottom: 3px;
                color: #475569;
            }}
            .bank-label {{
                font-weight: 600;
                color: #334155;
                display: inline-block;
                width: 90px;
            }}
            .totals-table {{
                width: 100%;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                border-collapse: separate;
                border-spacing: 0;
                overflow: hidden;
            }}
            .totals-table td {{
                border-bottom: 1px solid #cbd5e1;
                padding: 10px 14px;
            }}
            .totals-table tr:last-child td {{
                border-bottom: none;
                background-color: #1e3a8a;
                color: white;
                font-weight: 700;
                font-size: 14px;
            }}
            .sign-area {{
                margin-top: 40px;
                display: flex;
                justify-content: flex-end;
            }}
            .sign-box {{
                text-align: center;
                width: 180px;
            }}
            .sign-label {{
                font-size: 10px;
                font-weight: 700;
                color: #2563eb;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                margin-bottom: 5px;
            }}
            .signature {{
                font-family: 'Great Vibes', cursive;
                font-size: 28px;
                color: #0f172a;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-bottom: 1px solid #cbd5e1;
                margin-bottom: 5px;
                user-select: none;
            }}
            .sign-name {{
                font-size: 11px;
                font-weight: 700;
                color: #0f172a;
            }}
            .sign-role {{
                font-size: 10px;
                color: #64748b;
                margin-top: 2px;
            }}
            .print-btn-container {{
                max-width: 850px;
                margin: 15px auto;
                display: flex;
                justify-content: flex-end;
                gap: 12px;
            }}
            .btn {{
                background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                cursor: pointer;
                box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .btn:hover {{
                transform: translateY(-1px);
                box-shadow: 0 6px 14px rgba(37, 99, 235, 0.3);
                filter: brightness(1.05);
            }}
            .btn-secondary {{
                background: #ffffff;
                color: #334155;
                border: 1px solid #cbd5e1;
                box-shadow: none;
            }}
            .btn-secondary:hover {{
                background: #f8fafc;
                box-shadow: none;
                transform: none;
            }}
            
            /* Print Specific Styles */
            @media print {{
                body {{
                    background-color: #ffffff;
                }}
                .invoice-card {{
                    margin: 0;
                    padding: 0;
                    border: none;
                    box-shadow: none;
                    width: 100%;
                    max-width: 100%;
                }}
                .print-btn-container {{
                    display: none !important;
                }}
            }}
           </style>
       </head>
       <body>
           <div class="print-btn-container">
               <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
           </div>
           
           <div class="invoice-card">
               <!-- Header -->
               <div class="header">
                   <div class="logo-area">
                       <div class="logo-icon">B</div>
                       <div class="logo-text">
                           <h1 class="logo-title">BUNNY'S FARM</h1>
                           <p class="logo-subtitle">Fresh & Organic Farm Products</p>
                       </div>
                   </div>
                   <div class="invoice-title-area">
                       <h2 class="invoice-title">INVOICE</h2>
                       <p class="invoice-num"># {invoice_no}</p>
                   </div>
               </div>
               
               <!-- Details Grid -->
               <div class="details-grid">
                   <div>
                       <div class="section-label">Bill From:</div>
                       <div class="company-name">Bunny's Farm Pvt. Ltd.</div>
                       <div class="address-text">
                           Inamadugu, veguru, subareddypuram,<br>
                           NELLORE, Andhra Pradesh - 524137<br>
                           Phone: +91 7842339368
                       </div>
                       <div class="tax-info">
                           GSTIN: 36AABCB1234C1Z5<br>
                           PAN: AABCB1234C
                       </div>
                   </div>
                   <div class="invoice-meta">
                       <div class="meta-item">
                           <div class="meta-label">Invoice Date:</div>
                           <div class="meta-val">{invoice_date}</div>
                       </div>
                       <div class="meta-item">
                           <div class="meta-label">Due Date:</div>
                           <div class="meta-val">{due_date}</div>
                       </div>
                       <div class="meta-item">
                           <div class="meta-label">PO Number:</div>
                           <div class="meta-val">{po_no}</div>
                       </div>
                   </div>
               </div>
               
               <!-- Table -->
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 5%; text-align: center;">#</th>
                                <th style="width: 15%; text-align: center;">Date</th>
                                <th style="width: 50%; text-align: left;">Description</th>
                                <th style="width: 10%; text-align: center;">Qty</th>
                                <th style="width: 10%; text-align: right;">Unit Price (INR)</th>
                                <th style="width: 10%; text-align: right;">Amount (INR)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
                
                <!-- Totals -->
                <div class="totals-container">
                    <div class="totals-left">
                        <div class="word-amount">
                            <div class="word-title">Amount in Words:</div>
                            <div class="word-val">{total_words}</div>
                        </div>
                        <div class="bank-details">
                           <div class="bank-title">Payment Details:</div>
                           <div class="bank-row"><span class="bank-label">Online UPI/Mobile:</span> {online_txn}</div>
                           <div class="bank-row"><span class="bank-label">Bank Name:</span> {bank_name}</div>
                           <div class="bank-row"><span class="bank-label">Account Name:</span> {acc_name}</div>
                           <div class="bank-row"><span class="bank-label">Account Num:</span> {acc_num}</div>
                           <div class="bank-row"><span class="bank-label">IFSC Code:</span> {ifsc}</div>
                           <div class="bank-row"><span class="bank-label">Branch:</span> {branch}</div>
                        </div>
                    </div>
                    <div class="totals-right">
                        <table class="totals-table">
                            <tr>
                                <td>TOTAL AMOUNT (INR)</td>
                                <td style="text-align: right;">₹{total:,.2f}</td>
                            </tr>
                        </table>
                   </div>
               </div>
               
               <!-- Signature Area -->
               <div class="sign-area">
                   <div class="sign-box">
                       <div class="sign-label">Authorized Signatory</div>
                       <div style="height: 55px; border-bottom: 1px solid #cbd5e1; margin-bottom: 5px;"></div>
                   </div>
               </div>
           </div>
       </body>
       </html>
       """
    return html_code

def load_expenses():
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name="Expenses_Log")
            
            # Drop unwanted legacy columns if they exist
            cols_to_drop = ['Category', 'Description']
            df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')
            
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            if 'Receipt_Image' not in df.columns:
                df['Receipt_Image'] = ""
            df['Receipt_Image'] = df['Receipt_Image'].fillna("")
            
            # Save it back once to clean columns and auto-adjust widths on disk immediately
            save_expenses(df)
            
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
    save_expenses(default_entry)
    return default_entry

def save_expenses(df):
    try:
        # Clean up unwanted legacy columns from the dataframe
        cols_to_drop = ['Category', 'Description']
        df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')
        
        daily_summary = df.groupby('Date').agg(
            Total_Spent=('Amount', 'sum'),
            Entries_Count=('Amount', 'count')
        ).reset_index()
        
        df = df.sort_values(by="Timestamp", ascending=False)
        daily_summary = daily_summary.sort_values(by="Date", ascending=False)
        
        from openpyxl.utils import get_column_letter
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Expenses_Log", index=False)
            daily_summary.to_excel(writer, sheet_name="Daily_Summaries", index=False)
            
            # Auto-adjust column widths so no ### is shown in Excel
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for col in worksheet.columns:
                    max_len = 0
                    col_letter = get_column_letter(col[0].column)
                    for cell in col:
                        val = cell.value
                        if val is not None:
                            # Format datetimes nicely for string length calculation
                            if hasattr(val, 'strftime'):
                                val_str = val.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                val_str = str(val)
                            max_len = max(max_len, len(val_str))
                    # Add a padding of 4 spaces
                    worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
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
if not st.session_state.is_admin:
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
        if st.session_state.show_admin_login:
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
    # Scope-inject CSS to match the reference image exactly (material underline inputs, full-width button, no boxes)
    st.markdown("""
        <style>
            /* Reset the Streamlit form card background & border */
            div[data-testid="stForm"] {
                border: none !important;
                background: transparent !important;
                box-shadow: none !important;
                padding: 0 !important;
            }
            
            /* Material Design Underline Inputs */
            div[data-testid="stForm"] input[type="text"],
            div[data-testid="stForm"] input[type="password"] {
                border: none !important;
                border-bottom: 1.5px solid #cbd5e1 !important;
                border-radius: 0 !important;
                background: transparent !important;
                padding: 12px 0 6px 0 !important;
                font-size: 1.05rem !important;
                color: #1e293b !important;
                box-shadow: none !important;
                transition: border-color 0.2s ease !important;
                width: 100% !important;
            }
            div[data-testid="stForm"] input[type="text"]:focus,
            div[data-testid="stForm"] input[type="password"]:focus {
                border-bottom: 2.5px solid #3b82f6 !important;
            }
            
            /* Custom blue full-width submit button matching reference image */
            div[data-testid="stFormSubmitButton"] button {
                background-color: #3b82f6 !important;
                color: white !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                font-size: 0.9rem !important;
                letter-spacing: 1.2px !important;
                border-radius: 6px !important;
                padding: 12px 20px !important;
                border: none !important;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2) !important;
                transition: all 0.2s ease !important;
                width: 100% !important;
                margin-top: 15px !important;
            }
            div[data-testid="stFormSubmitButton"] button:hover {
                background-color: #2563eb !important;
                transform: translateY(-1px) !important;
                box-shadow: 0 6px 18px rgba(59, 130, 246, 0.3) !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2-Column Split Layout matching the reference image
    col_graphic, col_login = st.columns([1.2, 1], gap="large")
    
    with col_graphic:
        st.markdown('<div class="login-graphic-marker"></div>', unsafe_allow_html=True)
        # Render the custom generated circular logo graphic
        if os.path.exists("bunny_farm_login_graphic.png"):
            st.image("bunny_farm_login_graphic.png", use_container_width=True)
        else:
            # Fallback if graphic is copying
            st.markdown("""
                <div style="display: flex; align-items: center; justify-content: center; height: 350px; background: #f8fafc; border-radius: 20px; border: 2px dashed #cbd5e1;">
                    <div style="text-align: center; color: #64748b;">
                        <div style="font-size: 3rem;">🌱</div>
                        <div style="font-weight: 700; margin-top: 10px;">Bunny's Farm</div>
                        <div style="font-size: 0.8rem;">Loading Illustration Graphic...</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
    with col_login:
        with st.form("admin_login_form"):
            st.markdown("""
                <div style="margin-top: 25px; margin-bottom: 25px;">
                    <span style="color: #3b82f6; font-size: 0.75rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; font-family: 'Outfit', sans-serif;">ADMIN PORTAL</span>
                    <h2 style="font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.8rem; color: #0f172a; margin: 5px 0 0 0;">Secure Sign In</h2>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<label style="color: #64748b; font-size: 0.85rem; font-weight: 600; display: block; margin-top: 20px; font-family: \'Outfit\', sans-serif;">Username *</label>', unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter admin username", label_visibility="collapsed", key="admin_username_input")
            
            st.markdown('<label style="color: #64748b; font-size: 0.85rem; font-weight: 600; display: block; margin-top: 20px; font-family: \'Outfit\', sans-serif;">Password *</label>', unsafe_allow_html=True)
            password = st.text_input("Password", type="password", placeholder="Enter admin password", label_visibility="collapsed", key="admin_password_input")
            
            # Checkbox exactly matching "Login with otp" style
            st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
            remember_me = st.checkbox("Keep me logged in", key="login_remember_check")
            
            # The submit button
            login_submitted = st.form_submit_button("LOGIN")
            
            # Decorative disclaimer matching reference image
            st.markdown("""
                <div style="margin-top: 40px; color: #94a3b8; font-size: 0.72rem; line-height: 1.4; border-top: 1px solid #f1f5f9; padding-top: 15px; font-family: 'Inter', sans-serif;">
                    By proceeding you are agreeing to our <a href="#" style="color: #3b82f6; text-decoration: underline; font-weight: 500;">Terms and Conditions</a>
                </div>
            """, unsafe_allow_html=True)
            
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
    # ------------------ ADMIN SIDEBAR NAVIGATION ------------------
    st.sidebar.markdown("""
        <div class="sidebar-brand-panel">
            <span class="sidebar-brand-icon">🌱</span>
            <div class="sidebar-brand-details">
                <span class="sidebar-brand-name">Bunny's Farm</span>
                <span class="sidebar-brand-badge">ADMIN MODE</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("""
        <div class="sidebar-profile-card">
            <div class="profile-avatar">👑</div>
            <div class="profile-info">
                <div class="profile-name">Mylu Khanush</div>
                <div class="profile-role">Administrator</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Left Navigation Menu styled as vertical pills in CSS
    nav_selection = st.sidebar.radio(
        "Navigation Menu",
        ["📊 Dashboard", "📋 View All Data", "📄 Generate Invoice", "⚙️ Export & Management"],
        key="admin_sidebar_nav"
    )
    
    # Small spacing before the logout container (removed duplicate borders and huge spacer padding to make it fit perfectly!)
    st.sidebar.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-logout-container">', unsafe_allow_html=True)
    if st.sidebar.button("📝 Exit Admin Console", use_container_width=True, key="sidebar_logout_btn"):
        st.session_state.is_admin = False
        st.session_state.show_admin_login = False
        st.rerun()
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # ------------------ ADMIN MAIN CONTENT AREA ------------------
    # Render active section based on sidebar nav selection
    if nav_selection == "📊 Dashboard":
        st.markdown("""
            <div class="admin-header">
                <div class="admin-badge">Bunny's Farm • ADMIN</div>
                <h2 class="admin-title">Financial Command Center</h2>
                <p class="admin-subtitle">Real-time expense monitoring and database management</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Control Bar with Date Selector
        st.markdown('<div class="dashboard-header-marker"></div>', unsafe_allow_html=True)
        col_header, col_date = st.columns([2, 1])
        with col_header:
            st.markdown(f"""
                <div style="padding-top: 12px; display: flex; align-items: center; gap: 8px;">
                    <span class="status-indicator"></span>
                    <span style="color: #475569; font-weight: 600; font-size: 0.82rem; letter-spacing: 0.06em;">ACTIVE LEDGER FILTER</span>
                </div>
            """, unsafe_allow_html=True)
        with col_date:
            filter_date = st.date_input("Select Date", datetime.date.today(), max_value=datetime.date.today(), label_visibility="collapsed", key="dash_filter_date")

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

    elif nav_selection == "📋 View All Data":
        st.markdown('<div class="ledger-header-marker"></div>', unsafe_allow_html=True)
        col_logs_header, col_logs_actions = st.columns([2, 1.5])
        with col_logs_header:
            st.markdown("""
                <div class="section-header" style="margin-bottom: 10px;">
                    <div>
                        <h3 class="section-title">Ledger Transactions</h3>
                        <p class="section-subtitle">A list of recorded expenses for the selected date, sorted by time</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_logs_actions:
            st.markdown('<div class="ledger-header-marker"></div>', unsafe_allow_html=True)
            col_ref, col_dt = st.columns([1, 1.2])
            with col_ref:
                st.markdown('<div style="padding-top: 5px;"></div>', unsafe_allow_html=True)
                if st.button("🔄 Refresh", use_container_width=True, key="logs_refresh_btn"):
                    st.rerun()
            with col_dt:
                st.markdown('<div style="padding-top: 5px;"></div>', unsafe_allow_html=True)
                filter_date = st.date_input("Select Date", datetime.date.today(), max_value=datetime.date.today(), label_visibility="collapsed", key="ledger_filter_date")

        # Filter expenses for the selected date
        df_filtered = df_expenses[df_expenses['Date'] == filter_date]
        if not df_filtered.empty:
            display_df = df_filtered.copy().sort_values(by="Timestamp", ascending=False)
            display_df['Formatted Time'] = display_df['Timestamp'].dt.strftime('%d-%b-%Y %I:%M %p')
            
            # Select columns and reset index for sequential row styling
            ledger_table_df = display_df[['Formatted Time', 'Expenditure', 'Amount']].reset_index(drop=True)
            # Apply professional alternating row shading
            styled_ledger_df = ledger_table_df.style.apply(
                lambda row: ['background-color: #f8fafc' if row.name % 2 == 1 else 'background-color: #ffffff' for _ in row],
                axis=1
            )
            
            st.dataframe(
                styled_ledger_df,
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
            
            # Select columns and reset index for sequential row styling
            recent_table_df = recent_df[['Formatted Time', 'Expenditure', 'Amount']].reset_index(drop=True)
            # Apply professional alternating row shading
            styled_recent_df = recent_table_df.style.apply(
                lambda row: ['background-color: #f8fafc' if row.name % 2 == 1 else 'background-color: #ffffff' for _ in row],
                axis=1
            )
            
            st.dataframe(
                styled_recent_df,
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
            

            
    elif nav_selection == "📄 Generate Invoice":
        st.markdown("""
            <div class="section-header">
                <div>
                    <h3 class="section-title">📄 Premium Invoice Generator</h3>
                    <p class="section-subtitle">Generate and download professional, print-ready daily and monthly billing invoices</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Grid for invoice selection options
        col_inv_type, col_inv_date = st.columns([1, 1])
        
        with col_inv_type:
            inv_type = st.radio(
                "Select Invoice Duration",
                ["📅 Daily Invoice (Single Date)", "📆 Custom Range Invoice"],
                horizontal=True,
                key="inv_duration_radio"
            )
            
        with col_inv_date:
            if "Daily" in inv_type:
                selected_date = st.date_input("Select Date", datetime.date.today(), key="inv_single_date")
                df_filtered = df_expenses[df_expenses['Date'] == selected_date]
                date_label = selected_date.strftime('%d-%b-%Y')
                invoice_no = f"INV-{selected_date.strftime('%Y%m%d')}-001"
            else:
                range_dates = st.date_input(
                    "Select Date Range",
                    [datetime.date.today().replace(day=1), datetime.date.today()],
                    key="inv_range_dates"
                )
                if isinstance(range_dates, (list, tuple)) and len(range_dates) == 2:
                    start_date, end_date = range_dates
                    df_filtered = df_expenses[(df_expenses['Date'] >= start_date) & (df_expenses['Date'] <= end_date)]
                    date_label = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
                    invoice_no = f"INV-{start_date.strftime('%Y%m')}-{end_date.strftime('%d')}"
                else:
                    df_filtered = pd.DataFrame()
                    date_label = ""
                    invoice_no = "INV-TEMP"
                    
        # Generate and render
        if not df_filtered.empty:
            st.markdown(f"""
                <div class="premium-alert success">
                    <div class="alert-icon">✨</div>
                    <div class="alert-content">
                        <h4 class="alert-title">Transactions Located</h4>
                        <p class="alert-desc">Found <strong>{len(df_filtered)}</strong> expense transactions for the selected duration (Total: <strong>₹{df_filtered['Amount'].sum():,.2f}</strong>). You can now preview or download your invoice below.</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            bank_info = {
                "online_txn": "7842339268",
                "bank_name": "BANK OF BARODA",
                "acc_name": "MYLU KHANUSH",
                "acc_num": "55250100012962",
                "ifsc": "BARB0DARGAM",
                "branch": "Dargamitta, NELLORE"
            }
            
            invoice_html_content = generate_invoice_html(
                df=df_filtered,
                date_label=date_label,
                invoice_no=invoice_no,
                po_no="PO-7843-2026",
                bank_info=bank_info
            )
            
            # Action Buttons: Preview vs Download HTML
            col_act1, col_act2 = st.columns([1, 1])
            with col_act1:
                if st.button("👁️ Preview Invoice in App", use_container_width=True, key="preview_invoice_btn"):
                    st.session_state.show_invoice_preview = True
            with col_act2:
                # Provide direct download button of the HTML file
                st.download_button(
                    label="📥 Download HTML Invoice (Print Ready)",
                    data=invoice_html_content,
                    file_name=f"Invoice_{invoice_no}.html",
                    mime="text/html",
                    use_container_width=True,
                    key="download_invoice_html_btn"
                )
                
            # If show preview, render in a neat iframe wrapped in a browser frame
            if st.session_state.get("show_invoice_preview", False):
                st.markdown("<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;'/>", unsafe_allow_html=True)
                st.markdown(f"""
                    <div class="mock-browser-header-only">
                        <div class="browser-dots">
                            <div class="browser-dot red"></div>
                            <div class="browser-dot yellow"></div>
                            <div class="browser-dot green"></div>
                        </div>
                        <div class="browser-url-bar">invoice-preview.fintrack.local/{invoice_no}.html</div>
                    </div>
                """, unsafe_allow_html=True)
                st.components.v1.html(invoice_html_content, height=800, scrolling=True)
        else:
            st.markdown(f"""
                <div class="premium-alert warning">
                    <div class="alert-icon">⚠️</div>
                    <div class="alert-content">
                        <h4 class="alert-title">No Transactions Recorded</h4>
                        <p class="alert-desc">No expense transactions recorded for the selected duration (<strong>{date_label}</strong>). Select another date to generate an invoice.</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
    elif nav_selection == "⚙️ Export & Management":
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
        
        st.markdown('<div class="maint-header-marker"></div>', unsafe_allow_html=True)
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

elif not st.session_state.show_admin_login:
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
        submit_clicked = st.form_submit_button("Submit Transaction", use_container_width=False)
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

    // Advanced dynamic hiding of parent containers for hidden inputs to remove whitespace
    const hideHiddenInputs = () => {
        const doc = window.parent.document;
        if (!doc) return;
        
        // Find textareas and hide their parent element containers
        const textareas = doc.querySelectorAll('textarea');
        textareas.forEach(ta => {
            const label = ta.closest('div[data-testid="stTextArea"]')?.querySelector('label');
            if ((label && label.textContent.includes('Image Base64')) || ta.getAttribute('aria-label') === 'Image Base64') {
                const container = ta.closest('div[data-testid="element-container"]');
                if (container && container.style.display !== 'none') {
                    container.style.setProperty('display', 'none', 'important');
                    container.style.setProperty('height', '0px', 'important');
                    container.style.setProperty('margin', '0px', 'important');
                    container.style.setProperty('padding', '0px', 'important');
                    container.style.setProperty('overflow', 'hidden', 'important');
                }
            }
        });
        
        // Find inputs and hide their parent element containers
        const inputs = doc.querySelectorAll('input');
        inputs.forEach(inp => {
            const label = inp.closest('div[data-testid="stTextInput"]')?.querySelector('label');
            if ((label && label.textContent.includes('Image Filename')) || inp.getAttribute('aria-label') === 'Image Filename') {
                const container = inp.closest('div[data-testid="element-container"]');
                if (container && container.style.display !== 'none') {
                    container.style.setProperty('display', 'none', 'important');
                    container.style.setProperty('height', '0px', 'important');
                    container.style.setProperty('margin', '0px', 'important');
                    container.style.setProperty('padding', '0px', 'important');
                    container.style.setProperty('overflow', 'hidden', 'important');
                }
            }
        });
    };
    
    // Execute immediately
    styleButtons();
    hideHiddenInputs();
    
    // Run periodically to catch Streamlit state changes, page reruns, and tab switches
    if (!window.buttonSpacerInterval) {
        window.buttonSpacerInterval = setInterval(() => {
            styleButtons();
            hideHiddenInputs();
        }, 100);
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
            
            let base64Area = null;
            let filenameInput = null;
            
            const textareas = doc.querySelectorAll('textarea');
            textareas.forEach(ta => {
                const label = ta.closest('div[data-testid="stTextArea"]')?.querySelector('label');
                if ((label && label.textContent.includes('Image Base64')) || ta.getAttribute('aria-label') === 'Image Base64') {
                    base64Area = ta;
                }
            });
            
            const inputs = doc.querySelectorAll('input');
            inputs.forEach(inp => {
                const label = inp.closest('div[data-testid="stTextInput"]')?.querySelector('label');
                if ((label && label.textContent.includes('Image Filename')) || inp.getAttribute('aria-label') === 'Image Filename') {
                    filenameInput = inp;
                }
            });
            
            if (base64Area) {
                const val = data.images ? data.images : data.base64;
                setReactInputValue(base64Area, val);
            }
            if (filenameInput) {
                const fname = data.images ? "multi_upload.json" : data.filename;
                setReactInputValue(filenameInput, fname);
            }
        }
    });
</script>
""", height=0, width=0)

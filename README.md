# FinTrack - Smart Expense Tracker

FinTrack is a mobile-responsive, premium data entry and visualization application built with Streamlit and backed by Excel spreadsheet storage. It is designed for quick, convenient daily expense tracking on both mobile and desktop screens.

---

## Features

- **📱 Mobile-First Responsive Design**: Dynamic layout tailored to work beautifully on mobile phones, tablets, and desktops.
- **⚡ Fast Data Entry**: Quick forms to log amount, category, and purpose with automatic timestamps.
- **📂 Excel File Backend (`expenses.xlsx`)**: 
  - `Expenses_Log` sheet: Stores raw transaction histories.
  - `Daily_Summaries` sheet: Automatically compiles and updates end-of-day spend totals.
- **📊 Interactive Analytics**: High-quality Plotly-powered category distribution chart (Donut) and a 15-day daily spending history bar chart.
- **⚙️ Transaction Management**: Direct download button for the Excel sheet and a utility to select and delete erroneous entries.

---

## Technical Stack

- **Framework**: Streamlit
- **Data Handling**: Pandas & Openpyxl
- **Visualizations**: Plotly Express
- **Storage**: Microsoft Excel Workbook (`expenses.xlsx`)

---

## Getting Started

### 1. Setup Virtual Environment
If you haven't already, activate your environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
Ensure you have the required packages installed:
```powershell
pip install -r requirements.txt
```

### 3. Launch the Application
Start the Streamlit server locally:
```powershell
streamlit run app.py
```
The app will automatically open in your default browser (usually at `http://localhost:8501`).

---

## Project Structure

```text
├── .venv/                # Python Virtual Environment
├── app.py                # Main Streamlit application file
├── requirements.txt      # Python dependencies
├── expenses.xlsx         # Generated Excel spreadsheet containing logs and summaries
└── README.md             # This documentation file
```

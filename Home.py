import streamlit as st
import os
from utils.auth import require_login, logout_button
from utils.ui import inject_css, page_header

st.set_page_config(
    page_title="SilverWatch",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Silversea logo above sidebar menu
if os.path.exists("logo.png"):
    st.logo("logo.png", size="large")

require_login()
logout_button()
page_header("SilverWatch — Luxury Cruise Intelligence",
    "Select a page from the sidebar to begin.")

st.markdown("""
| Module | Description |
|--------|-------------|
| **1 · Capacity Map** | ABD by company, area, ship and arrival month |
| **2 · Blockout View** | Voyage list and ship deployment timeline |
| **3 · Capacity Movement** | How ABD shifted between observation snapshots |
| **4 · Pricing** | Entry PPD — from high-level averages to cruise level |
| **5 · User Guide** | How to use this dashboard |
| **6 · Control Panel** | Data quality checks and file refresh *(admin only)* |

Use the **sidebar** for global filters. All prices default to **USD**.
""")

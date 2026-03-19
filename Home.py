import streamlit as st
import os
from utils.auth import require_login, logout_button

st.set_page_config(
    page_title="SilverWatch",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_login()
logout_button()

# Logo above title, left-aligned, same width as content
logo_path = "logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=180)

st.title("SilverWatch — Luxury Cruise Intelligence")
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

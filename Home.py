import streamlit as st
import os
from utils.ui import inject_css

st.set_page_config(page_title="SilverWatch", page_icon="🛳️", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()

logo_path = "logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=110)

st.title("SilverWatch — Luxury Cruise Intelligence")
st.markdown("""
| Module | Description |
|--------|-------------|
| **1 · Capacity Map** | ABD by company, area, ship and arrival month |
| **2 · Blockout View** | Voyage list and ship deployment timeline |
| **3 · Capacity Movement** | How ABD shifted between observation snapshots |
| **4 · Pricing** | Entry PPD — from high-level averages to cruise level |
| **5 · User Guide** | How to use this dashboard |
| **6 · Control Panel** | Data quality checks and file refresh |

Use the **sidebar** for global filters (company, market, dates). Each page also has **quick filters** at the top for the most common selections. All prices default to **USD**.
""")

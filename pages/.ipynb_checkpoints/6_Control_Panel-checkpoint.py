import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.data_loader import load_data, PPD_OUTLIER_THRESHOLD
from utils.ui import inject_css, page_header, bordered_chart, bordered_dataframe
from utils.auth import require_login, logout_button, is_admin

st.set_page_config(page_title="Control Panel", layout="wide")
inject_css()
require_login()
logout_button()

if not is_admin():
    st.error("🔒 Access denied. This page is only available to administrators.")
    st.info("If you need access, please contact the dashboard administrator.")
    st.stop()

page_header("Control Panel", "Data quality checks, file refresh and user management. Admin only.")

import os
if os.path.exists("logo.png"):
    st.logo("logo.png", size="large")

DATA_PATH = "SilverWatch_PowerBi_input_ALL_MARKETS.xlsx"

tab_data, tab_qc, tab_users = st.tabs(["Data & File", "Quality Checks", "User Management"])

# ── Tab: Data & File ──────────────────────────────────────────────────────────
with tab_data:
    c1, c2 = st.columns([2,1])
    with c1:
        uploaded = st.file_uploader("Upload updated data file (.xlsx)", type=["xlsx"])
        if uploaded:
            with open(DATA_PATH, "wb") as f: f.write(uploaded.read())
            st.cache_data.clear()
            st.success("✅ File updated — all pages will reload with new data.")
    with c2:
        st.info(f"**Current file:** `{DATA_PATH}`\n\nPlace `logo.png` in the root folder to show your logo.")

    df_raw = load_data(DATA_PATH)
    total_raw   = len(df_raw)
    master_rows = len(df_raw[df_raw["Segment_Criteria"]=="MASTER"])
    combo_rows  = len(df_raw[df_raw["Segment_Criteria"]=="COMBO"])

    st.divider()
    st.markdown("#### Dataset overview")
    mc = st.columns(6)
    mc[0].metric("Total rows (raw)",      f"{total_raw:,}")
    mc[1].metric("MASTER rows",           f"{master_rows:,}")
    mc[2].metric("COMBO rows (excluded)", f"{combo_rows:,}")
    mc[3].metric("Observation dates",     df_raw["ObsDate"].nunique())
    mc[4].metric("Companies",             df_raw["Company"].nunique())
    mc[5].metric("Ships",                 df_raw["ShipName"].nunique())

    obs_tbl = df_raw.groupby(["ObsDate","ObsDateLabel"]).size().reset_index(name="Rows")
    st.dataframe(obs_tbl[["ObsDateLabel","Rows"]].rename(columns={"ObsDateLabel":"Date"}),
                 use_container_width=False, hide_index=True)

# ── Tab: Quality Checks ───────────────────────────────────────────────────────
with tab_qc:
    df_raw = load_data(DATA_PATH)
    df = df_raw[df_raw["Segment_Criteria"]=="MASTER"].copy()

    st.markdown("#### QC 1 — Missing values in key columns")
    key_cols = ["Market","AsDate","Curr","Company","CruiseType","Area","Itinerary",
                "Voyage_Start_Year","Voyage_Start_Month","Voyage","SubArea","ShipName",
                "CruiseNights","CruiseNightsInterval","Segment_Criteria","Suite_Category",
                "ABD","Entry_Ad_Fare","Entry_Ad_PPD"]
    missing = pd.DataFrame({
        "Column":        key_cols,
        "Missing count": [df[c].isna().sum() for c in key_cols],
        "Missing %":     [(df[c].isna().sum()/len(df)*100).round(2) for c in key_cols],
        "Status":        ["✅" if df[c].isna().sum()==0 else "⚠️" for c in key_cols],
    })
    def hl(row):
        return ["background-color:#fff3cd"]*len(row) if row["Missing count"]>0 else [""]*len(row)
    st.dataframe(missing.style.apply(hl,axis=1).format({"Missing %":"{:.2f}%"}),
                 use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### QC 2 — Missing price when Availability = Available")
    df_av = df[df["Availability_tag"]=="Available"]
    mp, mf = df_av["Entry_Ad_PPD"].isna().sum(), df_av["Entry_Ad_Fare"].isna().sum()
    q2 = st.columns(3)
    q2[0].metric("Available rows", f"{len(df_av):,}")
    q2[1].metric("Missing PPD",  f"{mp:,}", delta=f"{mp/len(df_av)*100:.1f}%" if len(df_av) else "0%", delta_color="inverse")
    q2[2].metric("Missing Fare", f"{mf:,}", delta=f"{mf/len(df_av)*100:.1f}%" if len(df_av) else "0%", delta_color="inverse")

    st.divider()
    st.markdown(f"#### QC 3 — PPD outliers")
    df_out = df[df["PPD_outlier"]]
    q3 = st.columns(4)
    q3[0].metric("Outlier rows", f"{len(df_out):,}", delta=f"{len(df_out)/len(df)*100:.1f}%", delta_color="inverse")
    q3[1].metric("PPD = 0",     f"{(df['Entry_Ad_PPD']==0).sum():,}")
    q3[2].metric(f"PPD > {PPD_OUTLIER_THRESHOLD:,}", f"{(df['Entry_Ad_PPD']>PPD_OUTLIER_THRESHOLD).sum():,}")
    q3[3].metric("Max PPD",     f"{df['Entry_Ad_PPD'].max():,.0f}" if df["Entry_Ad_PPD"].notna().any() else "N/A")

    st.divider()
    st.markdown("#### QC 4 — Voyage date parsing")
    bad = df["DepartureDate"].isna().sum()
    q4 = st.columns(2)
    q4[0].metric("Unparseable departure dates", f"{bad:,}")
    q4[1].metric("Departure date range",
                 f"{df['DepartureDate'].min().date()} → {df['DepartureDate'].max().date()}"
                 if bad < len(df) else "N/A")

# ── Tab: User Management ──────────────────────────────────────────────────────
with tab_users:
    st.markdown("#### Manage users")
    st.info("""
Users and passwords are managed in **Streamlit Cloud → App Settings → Secrets**.

To add or change a user, update the Secrets section with this format:

```toml
[users.username]
password = "their_password"
role     = "viewer"

[users.admin]
password = "your_admin_password"
role     = "admin"
```

Changes take effect immediately — no redeployment needed.
""")

    st.markdown("#### Currently configured users")
    try:
        users = st.secrets["users"]
        rows = [{"Username": u, "Role": info["role"]} for u, info in users.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=False)
    except Exception:
        st.warning("Running locally — user list is defined in `utils/auth.py`.")

    st.divider()
    st.markdown("#### Active sessions")
    st.write(f"You are logged in as **{st.session_state.get('username','')}** "
             f"(role: {st.session_state.get('role','')})")
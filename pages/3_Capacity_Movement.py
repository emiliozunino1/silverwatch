from utils.auth import require_login, logout_button
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES,
                                COMPANY_COLORS, AREA_COLORS,
                                get_two_latest_obs, safe_abd_delta)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header, style_numeric_heatmap, style_pct_heatmap

st.set_page_config(page_title="Capacity Movement", layout="wide")
inject_css()
require_login()
logout_button()

DATA_PATH = "SilverWatch_PowerBi_input_ALL_MARKETS.xlsx"
df_full   = load_data(DATA_PATH)
filters   = render_sidebar(df_full)

df = apply_filters(
    df_full, companies=filters["companies"], areas=filters["areas"],
    markets=filters["markets"], cruise_types=filters["cruise_types"],
    years=filters["years"], months=filters["months"],
    obs_dates=filters["obs_dates"], suite_cats=filters["suite_cats"],
    exclude_outliers=filters["exclude_outliers"],
    future_only=filters["future_only"], last_obs_date=filters["last_obs_date"],
)

obs_prev, obs_last = get_two_latest_obs(df)
all_obs   = sorted(df["ObsDate"].dropna().unique())
all_years = sorted(df["ArrivalYear"].dropna().unique().astype(int))

page_header("Capacity Movement",
    "How ABD shifted between observation snapshots — identify area/itinerary changes per voyage.")

tab1, tab2 = st.tabs(["ABD by area over time", "Ship redeployment matrix"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    sel_yr_am  = fc1.multiselect("Arrival year",  all_years, default=all_years, key="am_yr")
    sel_mon_am = fc2.multiselect("Arrival month", list(range(1,13)),
                                  format_func=lambda x: MONTH_NAMES[x],
                                  default=list(range(1,13)), key="am_mon")
    sel_ar_am  = fc3.multiselect("Area", sorted(df["AreaLabel"].unique()),
                                  default=sorted(df["AreaLabel"].unique()), key="am_area")

    df_am = df.copy()
    if sel_yr_am:  df_am = df_am[df_am["ArrivalYear"].isin(sel_yr_am)]
    if sel_mon_am: df_am = df_am[df_am["ArrivalMonth"].isin(sel_mon_am)]
    if sel_ar_am:  df_am = df_am[df_am["AreaLabel"].isin(sel_ar_am)]

    grp = (df_am.drop_duplicates(subset=["Company","Voyage","Suite_Category","ObsDate"])
           .groupby(["Company","ObsDate"], as_index=False)["ABD"].sum())
    pivot_abd = grp.pivot_table(index="Company", columns="ObsDate",
                                values="ABD", aggfunc="sum", fill_value=0)
    pivot_abd.columns = [str(c) for c in pivot_abd.columns]

    obs_cols = pivot_abd.columns.tolist()
    pivot_pct = pd.DataFrame(index=pivot_abd.index, columns=obs_cols, dtype=float)
    for i, col in enumerate(obs_cols):
        if i == 0:
            pivot_pct[col] = np.nan
        else:
            prev = obs_cols[i-1]
            pivot_pct[col] = ((pivot_abd[col] - pivot_abd[prev]) /
                               pivot_abd[prev].replace(0, np.nan) * 100).round(1)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**ABD by company and observation date**")
        st.dataframe(style_numeric_heatmap(pivot_abd.astype(float)),
                     use_container_width=True)
    with col_b:
        st.markdown("**% change vs previous observation date**")
        st.dataframe(style_pct_heatmap(pivot_pct), use_container_width=True)

    st.markdown("---")
    st.markdown(f"**ABD delta: {obs_prev} → {obs_last}**")
    delta = safe_abd_delta(df_am, "AreaLabel", obs_prev, obs_last)
    delta = delta.sort_values("Delta", ascending=False)
    fig_d = px.bar(delta, x="AreaLabel", y="Delta", color="Delta",
                   color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                   text=delta["Delta"].map(lambda v: f"{v:+,.0f}"),
                   labels={"AreaLabel":"Area","Delta":"ABD change"})
    fig_d.update_traces(textposition="outside")
    fig_d.update_layout(height=300, coloraxis_showscale=False,
                        margin=dict(t=10,b=60,l=40,r=10), paper_bgcolor="white")
    st.plotly_chart(fig_d, use_container_width=True)

# ── Tab 2: Ship redeployment matrix ──────────────────────────────────────────
with tab2:
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    sel_co_sr  = fc1.multiselect("Companies", sorted(df["Company"].unique()),
                                  default=sorted(df["Company"].unique())[:3], key="sr_co")
    sel_yr_sr  = fc2.multiselect("Arrival year", all_years, default=all_years, key="sr_yr")
    sel_mon_sr = fc3.multiselect("Arrival month", list(range(1,13)),
                                  format_func=lambda x: MONTH_NAMES[x],
                                  default=list(range(1,13)), key="sr_mon")

    df_sr = df.copy()
    if sel_co_sr:  df_sr = df_sr[df_sr["Company"].isin(sel_co_sr)]
    if sel_yr_sr:  df_sr = df_sr[df_sr["ArrivalYear"].isin(sel_yr_sr)]
    if sel_mon_sr: df_sr = df_sr[df_sr["ArrivalMonth"].isin(sel_mon_sr)]

    st.caption(
        f"Left table: voyages present in **{obs_prev}** and **{obs_last}** — "
        f"colored by area. Right table: changes between those two snapshots "
        f"(🟢 new voyage, 🔴 removed, 🟡 area/itinerary changed, ✅ unchanged).")

    def area_cell_style(val):
        """Color a cell by the area embedded in 'Voyage · Area · Itinerary'."""
        if not isinstance(val, str) or not val.strip():
            return "color:#bbbbbb; font-size:0.70rem"
        parts = val.split(" · ")
        area  = parts[1] if len(parts) > 1 else ""
        bg    = AREA_COLORS.get(area, "#f0f0f0")
        r,g,b = int(bg[1:3],16), int(bg[3:5],16), int(bg[5:7],16)
        fg    = "#ffffff" if 0.299*r+0.587*g+0.114*b < 140 else "#111111"
        return f"background-color:{bg}; color:{fg}; font-size:0.70rem; white-space:pre-wrap"

    def diff_cell_style(val):
        """Color diff cells: green=new, red=removed, yellow=changed, white=same."""
        if not isinstance(val, str) or not val.strip():
            return ""
        if val.startswith("🟢"):
            return "background-color:#d4edda; color:#155724; font-size:0.70rem"
        if val.startswith("🔴"):
            return "background-color:#f8d7da; color:#721c24; font-size:0.70rem"
        if val.startswith("🟡"):
            return "background-color:#fff3cd; color:#856404; font-size:0.70rem"
        if val.startswith("✅"):
            return "background-color:#f0f0f0; color:#444444; font-size:0.70rem"
        return "font-size:0.70rem"

    for co in (sel_co_sr or sorted(df_sr["Company"].unique())):
        df_co = df_sr[df_sr["Company"] == co].copy()
        if df_co.empty:
            continue

        # For each (Ship, ArrivalMonth, ObsDate) → all voyage codes with area+itinerary
        df_co["ShipShort"]  = df_co["ShipName"].str.split().str[-1]
        df_co["MonthName"]  = df_co["ArrivalMonth"].map(MONTH_NAMES)
        df_co["MonthNum"]   = df_co["ArrivalMonth"].astype(int)
        df_co["VoyCell"]    = (df_co["Voyage"] + " · " +
                               df_co["AreaLabel"] + " · " +
                               df_co["Itinerary"])

        # Keep only last two obs dates
        two_obs = [obs_prev, obs_last]
        df_two  = df_co[df_co["ObsDate"].isin(two_obs)].copy()
        if df_two.empty:
            st.markdown(f"##### {co} — no data for last two snapshots")
            continue

        # One row per (Ship, ArrivalMonth) × ObsDate → concatenate all voyages
        def concat_voyages(x):
            return "\n".join(sorted(x.unique()))

        grp = (df_two.drop_duplicates(subset=["ShipShort","MonthNum","Voyage","ObsDate"])
               .groupby(["ShipShort","MonthNum","MonthName","ObsDate"], as_index=False)
               .agg(Voyages=("VoyCell", concat_voyages)))

        pivot = grp.pivot_table(index=["ShipShort","MonthNum","MonthName"],
                                 columns="ObsDate", values="Voyages",
                                 aggfunc="first")
        pivot.columns = [str(c) for c in pivot.columns]
        pivot = pivot.reset_index().sort_values(["ShipShort","MonthNum"])

        # Build display index
        pivot["RowLabel"] = pivot["ShipShort"] + " · " + pivot["MonthName"]

        obs_present = [c for c in two_obs if c in pivot.columns]
        display = pivot[["RowLabel"] + obs_present].set_index("RowLabel")

        # Ensure unique index
        if display.index.duplicated().any():
            counts = {}
            new_idx = []
            for v in display.index:
                counts[v] = counts.get(v, 0) + 1
                new_idx.append(f"{v} ({counts[v]})" if counts[v] > 1 else v)
            display.index = new_idx

        # Build diff table
        diff_display = pd.DataFrame(index=display.index, columns=[f"Change ({obs_prev}→{obs_last})"])

        if len(obs_present) == 2:
            col_prev, col_last = obs_present[0], obs_present[1]
            for row in display.index:
                prev_val = display.loc[row, col_prev] if col_prev in display.columns else ""
                last_val = display.loc[row, col_last] if col_last in display.columns else ""
                prev_set = set(str(prev_val).split("\n")) if isinstance(prev_val, str) and prev_val.strip() else set()
                last_set = set(str(last_val).split("\n")) if isinstance(last_val, str) and last_val.strip() else set()

                # Extract voyage codes only (first part before " · ")
                def voy_codes(s): return {v.split(" · ")[0] for v in s if v.strip()}
                def area_of(s, code):
                    for v in s:
                        if v.startswith(code): return v
                    return ""

                prev_codes = voy_codes(prev_set)
                last_codes = voy_codes(last_set)
                new_codes  = last_codes - prev_codes
                rem_codes  = prev_codes - last_codes
                same_codes = prev_codes & last_codes

                changed = []
                for code in same_codes:
                    p = area_of(prev_set, code); l = area_of(last_set, code)
                    if p != l:
                        changed.append(code)

                parts = []
                for c in sorted(new_codes):
                    parts.append(f"🟢 {area_of(last_set, c)}")
                for c in sorted(rem_codes):
                    parts.append(f"🔴 {area_of(prev_set, c)}")
                for c in sorted(changed):
                    parts.append(f"🟡 {area_of(last_set, c)}")
                for c in sorted(same_codes - set(changed)):
                    parts.append(f"✅ {area_of(last_set, c)}")

                diff_display.loc[row, f"Change ({obs_prev}→{obs_last})"] = (
                    "\n".join(parts) if parts else "—")

        st.markdown(f"##### {co}")
        h = min(700, max(200, len(display)*36+60))
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption(f"{obs_prev} | {obs_last}")
            st.dataframe(display.style.applymap(area_cell_style),
                         use_container_width=True, height=h)
        with col_b:
            st.caption("Changes between snapshots")
            st.dataframe(diff_display.style.applymap(diff_cell_style),
                         use_container_width=True, height=h)

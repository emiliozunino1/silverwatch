from utils.auth import require_login, logout_button
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES,
                                COMPANY_COLORS, AREA_COLORS,
                                get_two_latest_obs, safe_abd_delta)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header, bordered_chart, bordered_dataframe, style_numeric_heatmap, style_pct_heatmap

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
    c1, c2, c3 = st.columns(3)
    sel_yr_am  = c1.multiselect("Arrival year",  all_years, default=all_years, key="am_yr")
    sel_mon_am = c2.multiselect("Arrival month", list(range(1,13)),
                                 format_func=lambda x: MONTH_NAMES[x],
                                 default=list(range(1,13)), key="am_mon")
    sel_ar_am  = c3.multiselect("Area", sorted(df["AreaLabel"].unique()),
                                 default=sorted(df["AreaLabel"].unique()), key="am_area")

    df_am = df.copy()
    if sel_yr_am:  df_am = df_am[df_am["ArrivalYear"].isin(sel_yr_am)]
    if sel_mon_am: df_am = df_am[df_am["ArrivalMonth"].isin(sel_mon_am)]
    if sel_ar_am:  df_am = df_am[df_am["AreaLabel"].isin(sel_ar_am)]

    grp = (df_am.drop_duplicates(subset=["Company","Voyage","Suite_Category","ObsDate"])
           .groupby(["Company","ObsDate"],as_index=False)["ABD"].sum())
    pivot_abd = grp.pivot_table(index="Company",columns="ObsDate",
                                values="ABD",aggfunc="sum",fill_value=0)
    pivot_abd.columns = [str(c) for c in pivot_abd.columns]

    obs_cols  = pivot_abd.columns.tolist()
    pivot_pct = pd.DataFrame(index=pivot_abd.index, columns=obs_cols, dtype=float)
    for i,col in enumerate(obs_cols):
        if i==0: pivot_pct[col] = np.nan
        else:
            prev = obs_cols[i-1]
            pivot_pct[col] = ((pivot_abd[col]-pivot_abd[prev]) /
                               pivot_abd[prev].replace(0,np.nan)*100).round(1)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**ABD by company and observation date**")
        bordered_dataframe(style_numeric_heatmap(pivot_abd.astype(float)),
                           use_container_width=True)
    with col_b:
        st.markdown("**% change vs previous observation date**")
        bordered_dataframe(style_pct_heatmap(pivot_pct), use_container_width=True)

    st.markdown("---")
    st.markdown(f"**ABD delta: {obs_prev} → {obs_last}**")
    delta = safe_abd_delta(df_am,"AreaLabel",obs_prev,obs_last).sort_values("Delta",ascending=False)
    fig_d = px.bar(delta, x="AreaLabel", y="Delta", color="Delta",
                   color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                   text=delta["Delta"].map(lambda v: f"{v:+,.0f}"),
                   labels={"AreaLabel":"Area","Delta":"ABD change"})
    fig_d.update_traces(textposition="outside")
    fig_d.update_layout(height=300, coloraxis_showscale=False,
                        margin=dict(t=10,b=60,l=40,r=10), paper_bgcolor="white")
    bordered_chart(fig_d, use_container_width=True)

# ── Tab 2: Ship redeployment — single merged table ────────────────────────────
with tab2:
    c1,c2,c3 = st.columns(3)
    sel_co_sr  = c1.multiselect("Companies", sorted(df["Company"].unique()),
                                 default=sorted(df["Company"].unique())[:3], key="sr_co")
    sel_yr_sr  = c2.multiselect("Arrival year", all_years, default=all_years, key="sr_yr")
    sel_mon_sr = c3.multiselect("Arrival month", list(range(1,13)),
                                 format_func=lambda x: MONTH_NAMES[x],
                                 default=list(range(1,13)), key="sr_mon")

    df_sr = df.copy()
    if sel_co_sr:  df_sr = df_sr[df_sr["Company"].isin(sel_co_sr)]
    if sel_yr_sr:  df_sr = df_sr[df_sr["ArrivalYear"].isin(sel_yr_sr)]
    if sel_mon_sr: df_sr = df_sr[df_sr["ArrivalMonth"].isin(sel_mon_sr)]

    two_obs = [obs_prev, obs_last]

    st.caption(f"Columns: **{obs_prev}** | **{obs_last}** | **Change** — "
               f"cells show Voyage · Area (abbrev.) · Itinerary (abbrev.), colored by area. "
               f"Change column: 🟢 new · 🔴 removed · 🟡 modified · ✅ unchanged")

    for co in (sel_co_sr or sorted(df_sr["Company"].unique())):
        df_co = df_sr[df_sr["Company"]==co].copy()
        if df_co.empty: continue

        df_co["ShipShort"]  = df_co["ShipName"].str.split().str[-1]
        df_co["MonthName"]  = df_co["ArrivalMonth"].map(MONTH_NAMES)
        df_co["MonthNum"]   = df_co["ArrivalMonth"].astype(int)
        # Abbreviated cell value: Voyage + short area + short itinerary
        df_co["VoyCell"] = (df_co["Voyage"] + "\n" +
                            df_co["AreaLabel"].str[:8] + "\n" +
                            df_co["Itinerary"].str[:12])

        df_two = df_co[df_co["ObsDate"].isin(two_obs)].copy()
        if df_two.empty: continue

        def concat_voy(x): return "\n\n".join(sorted(x.unique()))

        grp = (df_two.drop_duplicates(subset=["ShipShort","MonthNum","Voyage","ObsDate"])
               .groupby(["ShipShort","MonthNum","MonthName","ObsDate"],as_index=False)
               .agg(Voyages=("VoyCell", concat_voy)))

        pivot = grp.pivot_table(index=["ShipShort","MonthNum","MonthName"],
                                 columns="ObsDate", values="Voyages", aggfunc="first")
        pivot.columns = [str(c) for c in pivot.columns]
        pivot = pivot.reset_index().sort_values(["ShipShort","MonthNum"])
        pivot["RowLabel"] = pivot["ShipShort"] + " · " + pivot["MonthName"]

        obs_p = [c for c in two_obs if c in pivot.columns]
        display = pivot[["RowLabel"]+obs_p].set_index("RowLabel")

        # Add change column
        change_col = f"Change ({obs_prev}→{obs_last})"
        if len(obs_p)==2:
            col_p, col_l = obs_p[0], obs_p[1]
            changes = []
            for row in display.index:
                prev_val = display.loc[row,col_p] if col_p in display.columns else ""
                last_val = display.loc[row,col_l] if col_l in display.columns else ""
                def voy_codes(s):
                    if not isinstance(s,str) or not s.strip(): return set()
                    return {v.split("\n")[0] for v in s.split("\n\n") if v.strip()}
                pc = voy_codes(prev_val); lc = voy_codes(last_val)
                new_c = lc-pc; rem_c = pc-lc; same_c = pc&lc
                parts = []
                for c in sorted(new_c): parts.append(f"🟢 {c}")
                for c in sorted(rem_c): parts.append(f"🔴 {c}")
                # Check if area changed for same voyages
                def area_of(s,code):
                    if not isinstance(s,str): return ""
                    for v in s.split("\n\n"):
                        if v.startswith(code): return v
                    return ""
                for c in sorted(same_c):
                    p = area_of(prev_val,c); l = area_of(last_val,c)
                    parts.append(f"🟡 {c}" if p!=l else f"✅ {c}")
                changes.append("\n".join(parts) if parts else "—")
            display[change_col] = changes

        # Ensure unique index
        if display.index.duplicated().any():
            counts = {}
            new_idx = []
            for v in display.index:
                counts[v] = counts.get(v,0)+1
                new_idx.append(f"{v} ({counts[v]})" if counts[v]>1 else v)
            display.index = new_idx

        st.markdown(f"##### {co}")

        def cell_style(val):
            if not isinstance(val,str) or not val.strip(): return "color:#aaa; font-size:0.68rem; white-space:pre-wrap; text-align:center"
            # Change column — no area color
            if val.startswith(("🟢","🔴","🟡","✅","—")):
                return "font-size:0.68rem; white-space:pre-wrap; text-align:left"
            # Area-colored cells: use first voyage's area
            first_entry = val.split("\n\n")[0]
            parts = first_entry.split("\n")
            area  = parts[1].strip() if len(parts)>1 else ""
            # Find full area label match
            bg = "#f0f0f0"
            for full_area, color in AREA_COLORS.items():
                if full_area.startswith(area) or area.startswith(full_area[:6]):
                    bg = color; break
            r,g,b = int(bg[1:3],16),int(bg[3:5],16),int(bg[5:7],16)
            fg = "#ffffff" if 0.299*r+0.587*g+0.114*b<140 else "#111111"
            return f"background-color:{bg}; color:{fg}; font-size:0.68rem; white-space:pre-wrap; text-align:center"

        bordered_dataframe(
            display.style.applymap(cell_style),
            use_container_width=True,
            height=min(700, max(200, len(display)*56+60)))

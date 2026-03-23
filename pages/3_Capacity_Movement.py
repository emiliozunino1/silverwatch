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

import os
if os.path.exists("logo.png"):
    st.logo("logo.png", size="large")

DATA_PATH = "SilverWatch_PowerBi_input_ALL_MARKETS.xlsx"
df_full = load_data(DATA_PATH)
filters = render_sidebar(df_full)

df = apply_filters(df_full, companies=filters["companies"], areas=filters["areas"],
    markets=filters["markets"], cruise_types=filters["cruise_types"],
    years=filters["years"], months=filters["months"], obs_dates=filters["obs_dates"],
    suite_cats=filters["suite_cats"], exclude_outliers=filters["exclude_outliers"],
    future_only=filters["future_only"], last_obs_date=filters["last_obs_date"])

obs_prev, obs_last = get_two_latest_obs(df)
all_obs   = sorted(df["ObsDate"].dropna().unique())
all_years = sorted(df["ArrivalYear"].dropna().unique().astype(int))
all_areas = sorted(df["AreaLabel"].unique())
all_cos   = sorted(df["Company"].unique())

page_header("Capacity Movement",
    "How ABD shifted between observation snapshots — identify area/itinerary changes per voyage.")

tab1, tab2 = st.tabs(["ABD by area over time", "Ship redeployment matrix"])

with tab1:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(3)
        sel_yr  = f[0].multiselect("Year",  all_years, default=all_years, key="am_yr")
        sel_mon = f[1].multiselect("Month", list(range(1,13)),
                                    format_func=lambda x: MONTH_NAMES[x],
                                    default=list(range(1,13)), key="am_mon")
        sel_ar  = f[2].multiselect("Area",  all_areas, default=all_areas, key="am_area")

    df_am = df.copy()
    if sel_yr:  df_am = df_am[df_am["ArrivalYear"].isin(sel_yr)]
    if sel_mon: df_am = df_am[df_am["ArrivalMonth"].isin(sel_mon)]
    if sel_ar:  df_am = df_am[df_am["AreaLabel"].isin(sel_ar)]

    grp = (df_am.drop_duplicates(subset=["Company","Voyage","Suite_Category","ObsDate"])
           .groupby(["Company","ObsDate"],as_index=False)["ABD"].sum())
    pivot_abd = grp.pivot_table(index="Company",columns="ObsDate",
                                values="ABD",aggfunc="sum",fill_value=0)
    pivot_abd.columns = [str(c) for c in pivot_abd.columns]

    obs_cols = pivot_abd.columns.tolist()
    pivot_pct = pd.DataFrame(index=pivot_abd.index,columns=obs_cols,dtype=float)
    for i,col in enumerate(obs_cols):
        if i==0: pivot_pct[col] = np.nan
        else:
            prev = obs_cols[i-1]
            pivot_pct[col] = ((pivot_abd[col]-pivot_abd[prev]) /
                               pivot_abd[prev].replace(0,np.nan)*100).round(1)

    c1,c2 = st.columns(2)
    with c1:
        st.caption("**ABD by company and observation date**")
        bordered_dataframe(style_numeric_heatmap(pivot_abd.astype(float)),
                           use_container_width=True)
    with c2:
        st.caption("**% change vs previous observation date**")
        bordered_dataframe(style_pct_heatmap(pivot_pct), use_container_width=True)

    st.caption(f"ABD delta: **{obs_prev} → {obs_last}**")
    delta = safe_abd_delta(df_am,"AreaLabel",obs_prev,obs_last).sort_values("Delta",ascending=False)
    fig_d = px.bar(delta, x="AreaLabel", y="Delta", color="Delta",
                   color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                   text=delta["Delta"].map(lambda v: f"{v:+,.0f}"),
                   labels={"AreaLabel":"Area","Delta":"ABD change"})
    fig_d.update_traces(textposition="outside")
    fig_d.update_layout(height=280, coloraxis_showscale=False,
                        margin=dict(t=10,b=50,l=40,r=10), paper_bgcolor="white")
    bordered_chart(fig_d, use_container_width=True)

with tab2:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(3)
        sel_co_sr  = f[0].multiselect("Companies", all_cos, default=all_cos[:3], key="sr_co")
        sel_yr_sr  = f[1].multiselect("Year", all_years, default=all_years, key="sr_yr")
        sel_mon_sr = f[2].multiselect("Month", list(range(1,13)),
                                       format_func=lambda x: MONTH_NAMES[x],
                                       default=list(range(1,13)), key="sr_mon")

    df_sr = df.copy()
    if sel_co_sr:  df_sr = df_sr[df_sr["Company"].isin(sel_co_sr)]
    if sel_yr_sr:  df_sr = df_sr[df_sr["ArrivalYear"].isin(sel_yr_sr)]
    if sel_mon_sr: df_sr = df_sr[df_sr["ArrivalMonth"].isin(sel_mon_sr)]

    two_obs = [obs_prev, obs_last]
    st.caption(f"Columns: **{obs_prev}** | **{obs_last}** | **Change** — "
               f"cells: Voyage · Area (abbrev.) · Itinerary (abbrev.) colored by area. "
               f"Change: 🟢 new · 🔴 removed · 🟡 modified · ✅ unchanged")

    for co in (sel_co_sr or all_cos):
        df_co = df_sr[df_sr["Company"]==co].copy()
        if df_co.empty: continue

        df_co["ShipShort"] = df_co["ShipName"].str.split().str[-1]
        df_co["MonthName"] = df_co["ArrivalMonth"].map(MONTH_NAMES)
        df_co["MonthNum"]  = df_co["ArrivalMonth"].astype(int)
        df_co["VoyCell"]   = (df_co["Voyage"] + "\n" +
                              df_co["AreaLabel"].str[:8] + "\n" +
                              df_co["Itinerary"].str[:12])

        df_two = df_co[df_co["ObsDate"].isin(two_obs)].copy()
        if df_two.empty: continue

        def concat_voy(x): return "\n\n".join(sorted(x.unique()))
        grp = (df_two.drop_duplicates(subset=["ShipShort","MonthNum","Voyage","ObsDate"])
               .groupby(["ShipShort","MonthNum","MonthName","ObsDate"],as_index=False)
               .agg(Voyages=("VoyCell",concat_voy)))
        pivot = grp.pivot_table(index=["ShipShort","MonthNum","MonthName"],
                                 columns="ObsDate",values="Voyages",aggfunc="first")
        pivot.columns = [str(c) for c in pivot.columns]
        pivot = pivot.reset_index().sort_values(["ShipShort","MonthNum"])
        pivot["RowLabel"] = pivot["ShipShort"] + " · " + pivot["MonthName"]
        obs_p = [c for c in two_obs if c in pivot.columns]
        display = pivot[["RowLabel"]+obs_p].set_index("RowLabel")

        change_col = f"Change ({obs_prev}→{obs_last})"
        if len(obs_p)==2:
            col_p,col_l = obs_p[0],obs_p[1]
            changes = []
            for row in display.index:
                pv = display.loc[row,col_p] if col_p in display.columns else ""
                lv = display.loc[row,col_l] if col_l in display.columns else ""
                def voy_codes(s):
                    if not isinstance(s,str) or not s.strip(): return set()
                    return {v.split("\n")[0] for v in s.split("\n\n") if v.strip()}
                pc=voy_codes(pv); lc=voy_codes(lv)
                def area_of(s,code):
                    if not isinstance(s,str): return ""
                    for v in s.split("\n\n"):
                        if v.startswith(code): return v
                    return ""
                parts=[]
                for c in sorted(lc-pc): parts.append(f"🟢 {c}")
                for c in sorted(pc-lc): parts.append(f"🔴 {c}")
                for c in sorted(pc&lc):
                    parts.append(f"🟡 {c}" if area_of(pv,c)!=area_of(lv,c) else f"✅ {c}")
                changes.append("\n".join(parts) if parts else "—")
            display[change_col] = changes

        if display.index.duplicated().any():
            counts={}; new_idx=[]
            for v in display.index:
                counts[v]=counts.get(v,0)+1
                new_idx.append(f"{v} ({counts[v]})" if counts[v]>1 else v)
            display.index=new_idx

        st.markdown(f"##### {co}")

        def cell_style(val):
            if not isinstance(val,str) or not val.strip():
                return "color:#aaa;font-size:0.68rem;white-space:pre-wrap;text-align:center"
            if val.startswith(("🟢","🔴","🟡","✅","—")):
                return "font-size:0.68rem;white-space:pre-wrap;text-align:left"
            first = val.split("\n\n")[0]
            parts = first.split("\n")
            area  = parts[1].strip() if len(parts)>1 else ""
            bg="#f0f0f0"
            for fa,color in AREA_COLORS.items():
                if fa.startswith(area) or area.startswith(fa[:6]):
                    bg=color; break
            r,g,b=int(bg[1:3],16),int(bg[3:5],16),int(bg[5:7],16)
            fg="#ffffff" if 0.299*r+0.587*g+0.114*b<140 else "#111"
            return f"background-color:{bg};color:{fg};font-size:0.68rem;white-space:pre-wrap;text-align:center"

        bordered_dataframe(display.style.applymap(cell_style),
                           use_container_width=True,
                           height=min(700,max(180,len(display)*52+50)))

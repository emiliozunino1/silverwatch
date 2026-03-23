from utils.auth import require_login, logout_button
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES,
                                COMPANY_COLORS, AREA_COLORS)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header, bordered_chart, bordered_dataframe

st.set_page_config(page_title="Blockout View", layout="wide")
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

last_obs = sorted(df["ObsDate"].dropna().unique())[-1] if df["ObsDate"].notna().any() else None
df_last  = df[df["ObsDate"]==last_obs] if last_obs else df
all_years= sorted(df_last["ArrivalYear"].dropna().unique().astype(int))
all_cos  = sorted(df_last["Company"].unique())
all_areas= sorted(df_last["AreaLabel"].unique())

page_header("Blockout View",
    "Full voyage listing, ship deployment timeline and cross-company comparison.")

tab1, tab2, tab3 = st.tabs(["Voyage list", "Ship deployment timeline", "Company comparison"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(3)
        sel_co  = f[0].multiselect("Company", all_cos, default=all_cos, key="bv_co")
        sel_ar  = f[1].multiselect("Area", all_areas, default=[], key="bv_area")
        search  = f[2].text_input("Search itinerary / voyage ID", key="bv_search")

    base_cols = ["Company","ShipName","Voyage","AreaLabel","Itinerary"]
    port_cols = [c for c in ["Embarkement_Port_Name","Disembarkement_Port_Name"]
                 if c in df_last.columns and df_last[c].notna().any()]
    extra_cols= ["DepartureDate","ArrivalDate","CruiseNights","CruiseNightsInterval","Availability_tag"]
    tbl = df_last[base_cols+port_cols+extra_cols].drop_duplicates(subset=["Company","Voyage"]).copy()

    if sel_co: tbl = tbl[tbl["Company"].isin(sel_co)]
    if sel_ar: tbl = tbl[tbl["AreaLabel"].isin(sel_ar)]
    if search:
        mask = (tbl["Itinerary"].str.contains(search,case=False,na=False) |
                tbl["Voyage"].str.contains(search,case=False,na=False))
        tbl = tbl[mask]

    tbl = tbl.sort_values(["Company","ShipName","DepartureDate"])
    tbl["DepartureDate"] = tbl["DepartureDate"].dt.strftime("%Y-%m-%d")
    tbl["ArrivalDate"]   = tbl["ArrivalDate"].dt.strftime("%Y-%m-%d")
    tbl = tbl.rename(columns={"AreaLabel":"Area","CruiseNightsInterval":"Duration",
                               "Availability_tag":"Availability"})

    def color_area(val):
        bg = AREA_COLORS.get(val,"#ffffff")
        r,g,b = int(bg[1:3],16),int(bg[3:5],16),int(bg[5:7],16)
        fg = "#ffffff" if 0.299*r+0.587*g+0.114*b<140 else "#222"
        return f"background-color:{bg};color:{fg};font-size:0.75rem"

    bordered_dataframe(tbl.style.applymap(color_area,subset=["Area"])
                                .set_properties(**{"font-size":"0.75rem"}),
                       use_container_width=True, height=480)
    st.caption(f"{len(tbl):,} voyages")
    st.download_button("⬇ Download CSV", tbl.to_csv(index=False).encode(),
                       "blockout.csv","text/csv")

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(4)
        sel_yr_g  = f[0].multiselect("Year", all_years, default=all_years[:2], key="g_yr")
        sel_mon_g = f[1].multiselect("Month", list(range(1,13)),
                                      format_func=lambda x: MONTH_NAMES[x],
                                      default=list(range(1,13)), key="g_mon")
        sel_ar_g  = f[2].multiselect("Area", all_areas, default=all_areas, key="g_area")
        sel_co_g  = f[3].multiselect("Companies", all_cos, default=all_cos, key="g_co")

    df_g = df_last.copy()
    if sel_yr_g:  df_g = df_g[df_g["ArrivalYear"].isin(sel_yr_g)]
    if sel_mon_g: df_g = df_g[df_g["ArrivalMonth"].isin(sel_mon_g)]
    if sel_ar_g:  df_g = df_g[df_g["AreaLabel"].isin(sel_ar_g)]
    if sel_co_g:  df_g = df_g[df_g["Company"].isin(sel_co_g)]
    df_g = df_g.drop_duplicates(subset=["Company","ShipName","Voyage"])
    df_g = df_g.dropna(subset=["DepartureDate","ArrivalDate"])

    if df_g.empty:
        st.info("No voyages for the selected filters.")
    else:
        areas_present = sorted(df_g["AreaLabel"].unique())
        legend_html = "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:4px'>"
        for area in areas_present:
            c = AREA_COLORS.get(area,"#ccc")
            legend_html += (f"<span style='display:inline-flex;align-items:center;gap:3px;"
                            f"font-size:0.72rem'><span style='width:10px;height:10px;"
                            f"border-radius:50%;background:{c};display:inline-block'>"
                            f"</span>{area}</span>")
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

        for co in sorted(df_g["Company"].unique()):
            df_co = df_g[df_g["Company"]==co].sort_values(["ShipName","DepartureDate"])
            ships = df_co["ShipName"].unique().tolist()
            fig = px.timeline(df_co, x_start="DepartureDate", x_end="ArrivalDate",
                              y="ShipName", color="AreaLabel",
                              color_discrete_map=AREA_COLORS,
                              hover_data=["Voyage","Itinerary","CruiseNights"],
                              category_orders={"ShipName":ships},
                              labels={"ShipName":"Ship","AreaLabel":"Area"})
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(title=dict(text=co,font=dict(size=11)),
                              height=max(140,len(ships)*28+60),
                              margin=dict(t=24,b=6,l=120,r=10),
                              paper_bgcolor="white",plot_bgcolor="#fafafa",
                              showlegend=False, xaxis_title=None)
            bordered_chart(fig, use_container_width=True)

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(5)
        comp_a    = f[0].selectbox("Company A", all_cos, index=0, key="cc_a")
        comp_b    = f[1].selectbox("Company B", all_cos, index=min(1,len(all_cos)-1), key="cc_b")
        sel_yr_cc = f[2].multiselect("Year", all_years, default=all_years[:1], key="cc_yr")
        sel_ar_cc = f[3].multiselect("Area", all_areas, default=[], key="cc_area")
        dep_range = f[4].date_input("Departure date range",
                                 value=(df_last["DepartureDate"].min().date(),
                                        df_last["DepartureDate"].max().date()),
                                 key="cc_dep")

    df_cc = df_last[df_last["Company"].isin([comp_a,comp_b])].copy()
    if sel_yr_cc: df_cc = df_cc[df_cc["ArrivalYear"].isin(sel_yr_cc)]
    if sel_ar_cc: df_cc = df_cc[df_cc["AreaLabel"].isin(sel_ar_cc)]
    if len(dep_range)==2:
        df_cc = df_cc[(df_cc["DepartureDate"].dt.date>=dep_range[0]) &
                      (df_cc["DepartureDate"].dt.date<=dep_range[1])]
    df_cc = df_cc.dropna(subset=["ArrivalWeekSunday"])

    def week_summary(co):
        sub = df_cc[df_cc["Company"]==co].drop_duplicates(subset=["Voyage"])
        return (sub.groupby("ArrivalWeekSunday").agg(
            Voyages    =("Voyage","nunique"),
            Ships      =("ShipName", lambda x: ", ".join(sorted(x.unique()))),
            Itineraries=("Itinerary", lambda x:" | ".join(x.unique()[:3])))
            .reset_index().rename(columns={"ArrivalWeekSunday":"Week (Sun)"}))

    col_a, col_b = st.columns(2)
    for col, co in [(col_a,comp_a),(col_b,comp_b)]:
        with col:
            st.markdown(f"**{co}**")
            t = week_summary(co)
            t["Week (Sun)"] = t["Week (Sun)"].dt.strftime("%Y-%m-%d")
            bordered_dataframe(t, use_container_width=True, height=440,
                column_config={"Voyages":st.column_config.NumberColumn(format="%d"),
                               "Itineraries":st.column_config.TextColumn(width="large")})

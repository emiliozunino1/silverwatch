from utils.auth import require_login, logout_button
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES,
                                COMPANY_COLORS, AREA_COLORS)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header

st.set_page_config(page_title="Blockout View", layout="wide")
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
last_obs = sorted(df["ObsDate"].dropna().unique())[-1] if df["ObsDate"].notna().any() else None
df_last  = df[df["ObsDate"] == last_obs] if last_obs else df

# ── Sticky header block ───────────────────────────────────────────────────────
page_header("Blockout View",
    "Full voyage listing, ship deployment timeline and cross-company comparison.")
tab1, tab2, tab3 = st.tabs(
    ["Voyage list", "Ship deployment timeline", "Company comparison"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    fc1, fc2, fc3 = st.columns([2,2,2])
    sel_co_bv  = fc1.multiselect("Company", sorted(df_last["Company"].unique()),
                                  default=sorted(df_last["Company"].unique()), key="bv_co")
    sel_ar_bv  = fc2.multiselect("Area", sorted(df_last["AreaLabel"].unique()),
                                  default=[], key="bv_area")
    search_bv  = fc3.text_input("Search itinerary / voyage ID", key="bv_search")

    cols = ["Company","ShipName","Voyage","AreaLabel","Itinerary",
            "DepartureDate","ArrivalDate","CruiseNights","CruiseNightsInterval","Availability_tag"]
    tbl = df_last[cols].drop_duplicates(subset=["Company","Voyage"]).copy()
    if sel_co_bv:  tbl = tbl[tbl["Company"].isin(sel_co_bv)]
    if sel_ar_bv:  tbl = tbl[tbl["AreaLabel"].isin(sel_ar_bv)]
    if search_bv:
        mask = (tbl["Itinerary"].str.contains(search_bv, case=False, na=False) |
                tbl["Voyage"].str.contains(search_bv, case=False, na=False))
        tbl = tbl[mask]
    tbl = tbl.sort_values(["Company","ShipName","DepartureDate"])
    tbl["DepartureDate"] = tbl["DepartureDate"].dt.strftime("%Y-%m-%d")
    tbl["ArrivalDate"]   = tbl["ArrivalDate"].dt.strftime("%Y-%m-%d")
    tbl = tbl.rename(columns={"AreaLabel":"Area","CruiseNightsInterval":"Duration",
                               "Availability_tag":"Availability"})

    def color_area(val):
        bg = AREA_COLORS.get(val, "#ffffff")
        r,g,b = int(bg[1:3],16), int(bg[3:5],16), int(bg[5:7],16)
        fg = "#ffffff" if 0.299*r+0.587*g+0.114*b < 140 else "#222222"
        return f"background-color:{bg}; color:{fg}; font-size:0.75rem"

    st.dataframe(tbl.style.applymap(color_area, subset=["Area"])
                           .set_properties(**{"font-size":"0.75rem"}),
                 use_container_width=True, height=500)
    st.caption(f"{len(tbl):,} voyages")
    st.download_button("⬇ Download CSV", tbl.to_csv(index=False).encode(),
                       "blockout.csv", "text/csv")

# ── Tab 2: Timeline — one chart per company, shared legend on top ─────────────
with tab2:
    fc1, fc2, fc3, fc4 = st.columns([1,1,2,2])
    sel_yr_g  = fc1.multiselect("Arrival year",
                                 sorted(df_last["ArrivalYear"].dropna().unique().astype(int)),
                                 default=sorted(df_last["ArrivalYear"].dropna().unique().astype(int))[:2],
                                 key="g_yr")
    sel_mon_g = fc2.multiselect("Arrival month", list(range(1,13)),
                                 format_func=lambda x: MONTH_NAMES[x],
                                 default=list(range(1,13)), key="g_mon")
    sel_ar_g  = fc3.multiselect("Area", sorted(df_last["AreaLabel"].unique()),
                                 default=sorted(df_last["AreaLabel"].unique()), key="g_area")
    sel_co_g  = fc4.multiselect("Companies", sorted(df_last["Company"].unique()),
                                 default=sorted(df_last["Company"].unique()), key="g_co")

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
        # Shared legend: one coloured dot per area present
        areas_present = sorted(df_g["AreaLabel"].unique())
        legend_html = "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
        for area in areas_present:
            c = AREA_COLORS.get(area, "#cccccc")
            legend_html += (f"<span style='display:inline-flex;align-items:center;gap:4px;"
                            f"font-size:0.73rem;'>"
                            f"<span style='width:12px;height:12px;border-radius:50%;"
                            f"background:{c};display:inline-block'></span>{area}</span>")
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

        for co in sorted(df_g["Company"].unique()):
            df_co = df_g[df_g["Company"] == co].sort_values(["ShipName","DepartureDate"])
            ships = df_co["ShipName"].unique().tolist()
            fig = px.timeline(
                df_co, x_start="DepartureDate", x_end="ArrivalDate",
                y="ShipName", color="AreaLabel",
                color_discrete_map=AREA_COLORS,
                hover_data=["Voyage","Itinerary","CruiseNights"],
                category_orders={"ShipName": ships},
                labels={"ShipName":"Ship","AreaLabel":"Area"})
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                title=dict(text=co, font=dict(size=12)),
                height=max(160, len(ships)*30+70),
                margin=dict(t=28, b=8, l=130, r=10),
                paper_bgcolor="white",
                plot_bgcolor="#fafafa",
                showlegend=False,   # legend shown once above
                xaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)

# ── Tab 3: Company comparison ─────────────────────────────────────────────────
with tab3:
    fc1, fc2, fc3, fc4, fc5 = st.columns([1,1,1,1,2])
    comp_a    = fc1.selectbox("Company A", sorted(df_last["Company"].unique()), index=0, key="cc_a")
    comp_b    = fc2.selectbox("Company B", sorted(df_last["Company"].unique()), index=1, key="cc_b")
    sel_yr_cc = fc3.multiselect("Arrival year",
                                 sorted(df_last["ArrivalYear"].dropna().unique().astype(int)),
                                 default=sorted(df_last["ArrivalYear"].dropna().unique().astype(int))[:1],
                                 key="cc_yr")
    sel_ar_cc = fc4.multiselect("Area", sorted(df_last["AreaLabel"].unique()),
                                 default=[], key="cc_area")
    dep_range = fc5.date_input("Departure date range",
                                value=(df_last["DepartureDate"].min().date(),
                                       df_last["DepartureDate"].max().date()),
                                key="cc_dep")

    df_cc = df_last[df_last["Company"].isin([comp_a, comp_b])].copy()
    if sel_yr_cc: df_cc = df_cc[df_cc["ArrivalYear"].isin(sel_yr_cc)]
    if sel_ar_cc: df_cc = df_cc[df_cc["AreaLabel"].isin(sel_ar_cc)]
    if len(dep_range) == 2:
        df_cc = df_cc[
            (df_cc["DepartureDate"].dt.date >= dep_range[0]) &
            (df_cc["DepartureDate"].dt.date <= dep_range[1])]
    df_cc = df_cc.dropna(subset=["ArrivalWeekSunday"])

    def week_summary(co):
        sub = df_cc[df_cc["Company"] == co].drop_duplicates(subset=["Voyage"])
        return (sub.groupby("ArrivalWeekSunday").agg(
            Voyages    =("Voyage",    "nunique"),
            Ships      =("ShipName",  lambda x: ", ".join(sorted(x.unique()))),
            Itineraries=("Itinerary", lambda x: " | ".join(x.unique()[:3])))
            .reset_index()
            .rename(columns={"ArrivalWeekSunday":"Week (Sun)"}))

    col_a, col_b = st.columns(2)
    for col, co in [(col_a, comp_a), (col_b, comp_b)]:
        with col:
            st.markdown(f"**{co}**")
            t = week_summary(co)
            t["Week (Sun)"] = t["Week (Sun)"].dt.strftime("%Y-%m-%d")
            st.dataframe(t, use_container_width=True, height=460,
                         column_config={
                             "Voyages":     st.column_config.NumberColumn(format="%d"),
                             "Itineraries": st.column_config.TextColumn(width="large")})

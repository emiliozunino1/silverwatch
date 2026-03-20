from utils.auth import require_login, logout_button
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES,
                                COMPANY_COLORS, AREA_COLORS, SUITE_ORDER)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header, bordered_chart, bordered_dataframe

st.set_page_config(page_title="Capacity Map", layout="wide")
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

last_obs  = sorted(df["ObsDate"].dropna().unique())[-1] if df["ObsDate"].notna().any() else None
df_last   = df[df["ObsDate"]==last_obs] if last_obs else df
all_years = sorted(df_last["ArrivalYear"].dropna().unique().astype(int))

page_header("Capacity Map",
    "ABD across companies, areas and ships — latest snapshot unless otherwise filtered.")

tab1, tab2, tab3, tab4 = st.tabs(
    ["By Area & Company", "By Ship & Area", "ABD Heatmap", "World Map"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    c1, c2, c3 = st.columns([2,2,1])
    sel_co_t1 = c1.multiselect("Companies", sorted(df_last["Company"].unique()),
                                default=sorted(df_last["Company"].unique()), key="t1_co")
    sel_mon_t1= c2.multiselect("Arrival months", list(range(1,13)),
                                format_func=lambda x: MONTH_NAMES[x],
                                default=list(range(1,13)), key="t1_mon")
    chart_type= c3.selectbox("Chart type", ["Stacked","100%","Treemap"], key="t1_chart")

    df_t1 = df_last.copy()
    if sel_co_t1:  df_t1 = df_t1[df_t1["Company"].isin(sel_co_t1)]
    if sel_mon_t1: df_t1 = df_t1[df_t1["ArrivalMonth"].isin(sel_mon_t1)]

    for yr in all_years:
        df_yr = df_t1[df_t1["ArrivalYear"]==yr]
        if df_yr.empty: continue
        grp = (df_yr.drop_duplicates(subset=["Company","Voyage","Area","Suite_Category","ObsDate"])
               .groupby(["AreaLabel","Company"],as_index=False)["ABD"].sum())
        area_order = grp.groupby("AreaLabel")["ABD"].sum().sort_values(ascending=False).index.tolist()
        st.markdown(f"##### Arrival year {yr}")
        if chart_type == "Treemap":
            fig = px.treemap(grp, path=["AreaLabel","Company"], values="ABD",
                             color="Company", color_discrete_map=COMPANY_COLORS)
        else:
            fig = px.bar(grp, x="AreaLabel", y="ABD", color="Company",
                         barmode="relative" if chart_type=="100%" else "stack",
                         category_orders={"AreaLabel":area_order},
                         color_discrete_map=COMPANY_COLORS,
                         labels={"ABD":"ABD","AreaLabel":"Area"})
        fig.update_layout(height=340, margin=dict(t=10,b=50,l=40,r=10),
                          legend_title="Company", paper_bgcolor="white", plot_bgcolor="white")
        fig.update_xaxes(tickangle=30)
        bordered_chart(fig, use_container_width=True)

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    c1, c2, c3 = st.columns([2,2,1])
    sel_co_t2 = c1.multiselect("Companies", sorted(df_last["Company"].unique()),
                                default=sorted(df_last["Company"].unique()), key="t2_co")
    sel_mon_t2= c2.multiselect("Arrival months", list(range(1,13)),
                                format_func=lambda x: MONTH_NAMES[x],
                                default=list(range(1,13)), key="t2_mon")
    row_by    = c3.selectbox("Rows", ["Ship","Area"], key="t2_rows")

    df_t2 = df_last.copy()
    if sel_co_t2:  df_t2 = df_t2[df_t2["Company"].isin(sel_co_t2)]
    if sel_mon_t2: df_t2 = df_t2[df_t2["ArrivalMonth"].isin(sel_mon_t2)]

    for yr in all_years:
        df_yr = df_t2[df_t2["ArrivalYear"]==yr]
        if df_yr.empty: continue
        st.markdown(f"##### Arrival year {yr}")
        for co in sorted(df_yr["Company"].unique()):
            df_co   = df_yr[df_yr["Company"]==co]
            row_fld = "ShipName" if row_by=="Ship" else "AreaLabel"
            pivot   = (df_co.drop_duplicates(subset=[row_fld,"Voyage","ArrivalMonth","Suite_Category"])
                       .groupby([row_fld,"ArrivalMonth"])["ABD"].sum()
                       .reset_index()
                       .pivot_table(index=row_fld, columns="ArrivalMonth",
                                    values="ABD", aggfunc="sum", fill_value=0))
            pivot.columns = [MONTH_NAMES.get(c,c) for c in pivot.columns]
            color = COMPANY_COLORS.get(co,"#1f77b4")
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
                colorscale=[[0,"#ffffff"],[1,color]],
                text=pivot.values, texttemplate="%{text:,.0f}",
                showscale=False, hoverongaps=False))
            fig.update_layout(
                title=dict(text=f"{co} — {yr}", font=dict(size=12)),
                height=max(160, len(pivot.index)*38+80),
                margin=dict(t=30,b=20,l=140,r=10),
                xaxis_title="Arrival month", paper_bgcolor="white")
            bordered_chart(fig, use_container_width=True)

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    c1, c2 = st.columns(2)
    sel_co_t3   = c1.multiselect("Companies", sorted(df_last["Company"].unique()),
                                  default=sorted(df_last["Company"].unique()), key="t3_co")
    sel_area_t3 = c2.multiselect("Areas", sorted(df_last["AreaLabel"].unique()),
                                  default=sorted(df_last["AreaLabel"].unique()), key="t3_area")
    df_t3 = df_last.copy()
    if sel_co_t3:   df_t3 = df_t3[df_t3["Company"].isin(sel_co_t3)]
    if sel_area_t3: df_t3 = df_t3[df_t3["AreaLabel"].isin(sel_area_t3)]

    for yr in all_years:
        df_yr = df_t3[df_t3["ArrivalYear"]==yr]
        if df_yr.empty: continue
        grp   = (df_yr.drop_duplicates(subset=["Company","Voyage","Suite_Category","ObsDate"])
                 .groupby(["Company","ArrivalMonth"],as_index=False)["ABD"].sum())
        pivot = grp.pivot_table(index="Company",columns="ArrivalMonth",
                                values="ABD",aggfunc="sum",fill_value=0)
        pivot.columns = [MONTH_NAMES.get(c,c) for c in pivot.columns]
        st.markdown(f"##### Arrival year {yr}")
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
            colorscale="Blues", text=pivot.values,
            texttemplate="%{text:,.0f}", hoverongaps=False))
        fig.update_layout(height=260+len(pivot)*8,
                          xaxis_title="Arrival month", yaxis_title="Company",
                          margin=dict(t=10,b=20,l=100,r=10), paper_bgcolor="white")
        bordered_chart(fig, use_container_width=True)

# ── Tab 4 ─────────────────────────────────────────────────────────────────────
with tab4:
    c1,c2,c3,c4,c5 = st.columns(5)
    sel_yr_map  = c1.multiselect("Arrival year", all_years, default=all_years, key="map_yr")
    sel_mon_map = c2.multiselect("Arrival month", list(range(1,13)),
                                  format_func=lambda x: MONTH_NAMES[x],
                                  default=list(range(1,13)), key="map_mon")
    sel_area_map= c3.multiselect("Area", sorted(df_last["AreaLabel"].unique()),
                                  default=sorted(df_last["AreaLabel"].unique()), key="map_area")
    map_view    = c4.selectbox("Color by", ["Company","Area"], key="map_view")
    map_geo     = c5.selectbox("Map by", ["Area","Embarkation port"], key="map_geo")

    df_map = df_last.copy()
    if sel_yr_map:   df_map = df_map[df_map["ArrivalYear"].isin(sel_yr_map)]
    if sel_mon_map:  df_map = df_map[df_map["ArrivalMonth"].isin(sel_mon_map)]
    if sel_area_map: df_map = df_map[df_map["AreaLabel"].isin(sel_area_map)]

    has_ports = "Embarkement_Port_Name" in df_map.columns and df_map["EmbLat"].notna().any()

    if map_geo == "Embarkation port" and has_ports:
        grp_map = (df_map.dropna(subset=["EmbLat","EmbLon"])
                   .drop_duplicates(subset=["Company","Voyage","Embarkement_Port_Name","Suite_Category","ObsDate"])
                   .groupby(["Embarkement_Port_Name","Company","EmbLat","EmbLon"],as_index=False)["ABD"].sum())
        lat_col="EmbLat"; lon_col="EmbLon"; hover_col="Embarkement_Port_Name"
        color_col = "Company" if map_view=="Company" else "Embarkement_Port_Name"
        cmap = COMPANY_COLORS if map_view=="Company" else {}
    else:
        grp_map = (df_map.drop_duplicates(subset=["Company","Voyage","Area","Suite_Category","ObsDate"])
                   .groupby(["AreaLabel","Company","AreaLat","AreaLon"],as_index=False)["ABD"].sum())
        lat_col="AreaLat"; lon_col="AreaLon"; hover_col="AreaLabel"
        color_col = "Company" if map_view=="Company" else "AreaLabel"
        cmap = COMPANY_COLORS if map_view=="Company" else AREA_COLORS

    if grp_map.empty:
        st.info("No data for selected filters.")
    elif map_geo == "Embarkation port" and not has_ports:
        st.info("Embarkation port data not available in the current file.")
    else:
        fig_map = px.scatter_geo(
            grp_map, lat=lat_col, lon=lon_col,
            size="ABD", color=color_col,
            color_discrete_map=cmap if cmap else None,
            hover_name=hover_col,
            hover_data={"ABD":":,.0f",lat_col:False,lon_col:False},
            size_max=70, projection="natural earth")
        fig_map.update_layout(
            height=580, margin=dict(t=10,b=0,l=0,r=0), paper_bgcolor="white",
            geo=dict(showframe=False, showcoastlines=True, coastlinecolor="#aaaaaa",
                     showland=True, landcolor="#f5f5f0", showocean=True, oceancolor="#d4eaf7",
                     showcountries=True, countrycolor="#dddddd"))
        bordered_chart(fig_map, use_container_width=True)

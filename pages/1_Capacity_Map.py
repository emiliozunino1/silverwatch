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

last_obs  = sorted(df["ObsDate"].dropna().unique())[-1] if df["ObsDate"].notna().any() else None
df_last   = df[df["ObsDate"]==last_obs] if last_obs else df
all_years = sorted(df_last["ArrivalYear"].dropna().unique().astype(int))
all_months= list(range(1,13))
all_areas = sorted(df_last["AreaLabel"].unique())
all_cos   = sorted(df_last["Company"].unique())

page_header("Capacity Map",
    "ABD across companies, areas and ships — latest snapshot unless otherwise filtered.")

tab1, tab2, tab3, tab4 = st.tabs(
    ["By Area & Company", "By Ship & Area", "ABD Heatmap", "World Map"])

with tab1:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(3)
        sel_co  = f[0].multiselect("Companies", all_cos, default=all_cos, key="t1_co")
        sel_mon = f[1].multiselect("Months", all_months, format_func=lambda x: MONTH_NAMES[x],
                                    default=all_months, key="t1_mon")
        chart_t = f[2].selectbox("Chart type", ["Stacked","100%","Treemap"], key="t1_chart")

    df_t = df_last.copy()
    if sel_co:  df_t = df_t[df_t["Company"].isin(sel_co)]
    if sel_mon: df_t = df_t[df_t["ArrivalMonth"].isin(sel_mon)]

    for yr in all_years:
        df_yr = df_t[df_t["ArrivalYear"]==yr]
        if df_yr.empty: continue
        grp = (df_yr.drop_duplicates(subset=["Company","Voyage","Area","Suite_Category","ObsDate"])
               .groupby(["AreaLabel","Company"],as_index=False)["ABD"].sum())
        order = grp.groupby("AreaLabel")["ABD"].sum().sort_values(ascending=False).index.tolist()
        st.markdown(f"**Arrival year {yr}**")
        if chart_t=="Treemap":
            fig = px.treemap(grp, path=["AreaLabel","Company"], values="ABD",
                             color="Company", color_discrete_map=COMPANY_COLORS)
        else:
            fig = px.bar(grp, x="AreaLabel", y="ABD", color="Company",
                         barmode="relative" if chart_t=="100%" else "stack",
                         category_orders={"AreaLabel":order},
                         color_discrete_map=COMPANY_COLORS,
                         labels={"ABD":"ABD","AreaLabel":"Area"})
        fig.update_layout(height=320, margin=dict(t=10,b=50,l=40,r=10),
                          paper_bgcolor="white", plot_bgcolor="white")
        fig.update_xaxes(tickangle=30)
        bordered_chart(fig, use_container_width=True)

with tab2:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(3)
        sel_co2  = f[0].multiselect("Companies", all_cos, default=all_cos, key="t2_co")
        sel_mon2 = f[1].multiselect("Months", all_months, format_func=lambda x: MONTH_NAMES[x],
                                     default=all_months, key="t2_mon")
        row_by   = f[2].selectbox("Rows", ["Ship","Area"], key="t2_rows")

    df_t2 = df_last.copy()
    if sel_co2:  df_t2 = df_t2[df_t2["Company"].isin(sel_co2)]
    if sel_mon2: df_t2 = df_t2[df_t2["ArrivalMonth"].isin(sel_mon2)]

    for yr in all_years:
        df_yr = df_t2[df_t2["ArrivalYear"]==yr]
        if df_yr.empty: continue
        st.markdown(f"**Arrival year {yr}**")
        for co in sorted(df_yr["Company"].unique()):
            df_co   = df_yr[df_yr["Company"]==co]
            row_fld = "ShipName" if row_by=="Ship" else "AreaLabel"
            pivot   = (df_co.drop_duplicates(subset=[row_fld,"Voyage","ArrivalMonth","Suite_Category"])
                       .groupby([row_fld,"ArrivalMonth"])["ABD"].sum().reset_index()
                       .pivot_table(index=row_fld, columns="ArrivalMonth",
                                    values="ABD", aggfunc="sum", fill_value=0))
            pivot.columns = [MONTH_NAMES.get(c,c) for c in pivot.columns]
            color = COMPANY_COLORS.get(co,"#1f77b4")
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
                colorscale=[[0,"#ffffff"],[1,color]],
                text=pivot.values, texttemplate="%{text:,.0f}",
                showscale=False, hoverongaps=False))
            fig.update_layout(title=dict(text=f"{co} — {yr}", font=dict(size=11)),
                              height=max(150, len(pivot.index)*34+70),
                              margin=dict(t=28,b=15,l=130,r=10), paper_bgcolor="white")
            bordered_chart(fig, use_container_width=True)

with tab3:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(2)
        sel_co3   = f[0].multiselect("Companies", all_cos, default=all_cos, key="t3_co")
        sel_area3 = f[1].multiselect("Areas", all_areas, default=all_areas, key="t3_area")

    df_t3 = df_last.copy()
    if sel_co3:   df_t3 = df_t3[df_t3["Company"].isin(sel_co3)]
    if sel_area3: df_t3 = df_t3[df_t3["AreaLabel"].isin(sel_area3)]

    for yr in all_years:
        df_yr = df_t3[df_t3["ArrivalYear"]==yr]
        if df_yr.empty: continue
        grp   = (df_yr.drop_duplicates(subset=["Company","Voyage","Suite_Category","ObsDate"])
                 .groupby(["Company","ArrivalMonth"],as_index=False)["ABD"].sum())
        pivot = grp.pivot_table(index="Company",columns="ArrivalMonth",
                                values="ABD",aggfunc="sum",fill_value=0)
        pivot.columns = [MONTH_NAMES.get(c,c) for c in pivot.columns]
        st.markdown(f"**Arrival year {yr}**")
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
            colorscale="Blues", text=pivot.values,
            texttemplate="%{text:,.0f}", hoverongaps=False))
        fig.update_layout(height=240+len(pivot)*8, margin=dict(t=10,b=15,l=100,r=10),
                          paper_bgcolor="white")
        bordered_chart(fig, use_container_width=True)

with tab4:
    with st.expander("🔽 Filters", expanded=False):
        f = st.columns(5)
        sel_yr_m  = f[0].multiselect("Year", all_years, default=all_years, key="map_yr")
        sel_mon_m = f[1].multiselect("Month", all_months, format_func=lambda x: MONTH_NAMES[x],
                                      default=all_months, key="map_mon")
        sel_area_m= f[2].multiselect("Area", all_areas, default=all_areas, key="map_area")
        color_by  = f[3].selectbox("Color by", ["Company","Area"], key="map_col")
        map_by    = f[4].selectbox("Map by", ["Area","Embarkation port"], key="map_geo")

    df_m = df_last.copy()
    if sel_yr_m:   df_m = df_m[df_m["ArrivalYear"].isin(sel_yr_m)]
    if sel_mon_m:  df_m = df_m[df_m["ArrivalMonth"].isin(sel_mon_m)]
    if sel_area_m: df_m = df_m[df_m["AreaLabel"].isin(sel_area_m)]

    has_ports = "Embarkement_Port_Name" in df_m.columns and df_m["EmbLat"].notna().any()

    if map_by=="Embarkation port" and has_ports:
        grp = (df_m.dropna(subset=["EmbLat","EmbLon"])
               .drop_duplicates(subset=["Company","Voyage","Embarkement_Port_Name","Suite_Category","ObsDate"])
               .groupby(["Embarkement_Port_Name","Company","EmbLat","EmbLon"],as_index=False)["ABD"].sum())
        lat_c,lon_c,hov_c = "EmbLat","EmbLon","Embarkement_Port_Name"
        col_c = "Company" if color_by=="Company" else "Embarkement_Port_Name"
        cmap  = COMPANY_COLORS if color_by=="Company" else {}
    else:
        grp = (df_m.drop_duplicates(subset=["Company","Voyage","Area","Suite_Category","ObsDate"])
               .groupby(["AreaLabel","Company","AreaLat","AreaLon"],as_index=False)["ABD"].sum())
        lat_c,lon_c,hov_c = "AreaLat","AreaLon","AreaLabel"
        col_c = "Company" if color_by=="Company" else "AreaLabel"
        cmap  = COMPANY_COLORS if color_by=="Company" else AREA_COLORS

    if grp.empty:
        st.info("No data for selected filters.")
    elif map_by=="Embarkation port" and not has_ports:
        st.info("Embarkation port data not available in current file.")
    else:
        fig = px.scatter_geo(grp, lat=lat_c, lon=lon_c, size="ABD",
                             color=col_c, color_discrete_map=cmap if cmap else None,
                             hover_name=hov_c,
                             hover_data={"ABD":":,.0f",lat_c:False,lon_c:False},
                             size_max=70, projection="natural earth")
        fig.update_layout(height=560, margin=dict(t=5,b=0,l=0,r=0), paper_bgcolor="white",
                          geo=dict(showframe=False,showcoastlines=True,coastlinecolor="#aaaaaa",
                                   showland=True,landcolor="#f5f5f0",showocean=True,
                                   oceancolor="#d4eaf7",showcountries=True,countrycolor="#dddddd"))
        bordered_chart(fig, use_container_width=True)

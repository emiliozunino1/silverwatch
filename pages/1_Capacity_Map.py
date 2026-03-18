import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES,
                                COMPANY_COLORS, AREA_COLORS, SUITE_ORDER)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header

st.set_page_config(page_title="Capacity Map", layout="wide")
inject_css()

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
df_last  = df[df["ObsDate"]==last_obs] if last_obs else df
all_years = sorted(df_last["ArrivalYear"].dropna().unique().astype(int))

page_header("Capacity Map",
    "ABD across companies, areas and ships — latest snapshot unless otherwise filtered.")

tab1, tab2, tab3, tab4 = st.tabs(
    ["By Area & Company", "By Ship & Area", "ABD Heatmap", "World Map"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    # Top filters
    fc1, fc2, fc3 = st.columns([2,2,1])
    sel_co_t1 = fc1.multiselect("Companies", sorted(df_last["Company"].unique()),
                                 default=sorted(df_last["Company"].unique()), key="t1_co")
    sel_mon_t1= fc2.multiselect("Arrival months", list(range(1,13)),
                                 format_func=lambda x: MONTH_NAMES[x],
                                 default=list(range(1,13)), key="t1_mon")
    chart_type= fc3.radio("Chart", ["Stacked","100%","Treemap"], key="t1_chart")

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
        st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: By Ship & Area ─────────────────────────────────────────────────────
with tab2:
    fc1, fc2, fc3 = st.columns([2,2,1])
    sel_co_t2 = fc1.multiselect("Companies", sorted(df_last["Company"].unique()),
                                 default=sorted(df_last["Company"].unique()), key="t2_co")
    sel_mon_t2= fc2.multiselect("Arrival months", list(range(1,13)),
                                 format_func=lambda x: MONTH_NAMES[x],
                                 default=list(range(1,13)), key="t2_mon")
    row_by    = fc3.radio("Rows", ["Ship","Area"], key="t2_rows")

    df_t2 = df_last.copy()
    if sel_co_t2:  df_t2 = df_t2[df_t2["Company"].isin(sel_co_t2)]
    if sel_mon_t2: df_t2 = df_t2[df_t2["ArrivalMonth"].isin(sel_mon_t2)]

    for yr in all_years:
        df_yr = df_t2[df_t2["ArrivalYear"]==yr]
        if df_yr.empty: continue
        st.markdown(f"##### Arrival year {yr}")
        companies_yr = sorted(df_yr["Company"].unique())
        for co in companies_yr:
            df_co = df_yr[df_yr["Company"]==co]
            row_field = "ShipName" if row_by=="Ship" else "AreaLabel"
            pivot = (df_co.drop_duplicates(
                        subset=[row_field,"Voyage","ArrivalMonth","Suite_Category"])
                     .groupby([row_field,"ArrivalMonth"])["ABD"].sum()
                     .reset_index()
                     .pivot_table(index=row_field, columns="ArrivalMonth",
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
            st.plotly_chart(fig, use_container_width=True)

# ── Tab 3: ABD Heatmap ────────────────────────────────────────────────────────
with tab3:
    fc1, fc2 = st.columns([2,2])
    sel_co_t3   = fc1.multiselect("Companies", sorted(df_last["Company"].unique()),
                                   default=sorted(df_last["Company"].unique()), key="t3_co")
    sel_area_t3 = fc2.multiselect("Areas", sorted(df_last["AreaLabel"].unique()),
                                   default=sorted(df_last["AreaLabel"].unique()), key="t3_area")
    df_t3 = df_last.copy()
    if sel_co_t3:   df_t3 = df_t3[df_t3["Company"].isin(sel_co_t3)]
    if sel_area_t3: df_t3 = df_t3[df_t3["AreaLabel"].isin(sel_area_t3)]

    for yr in all_years:
        df_yr = df_t3[df_t3["ArrivalYear"]==yr]
        if df_yr.empty: continue
        grp = (df_yr.drop_duplicates(subset=["Company","Voyage","Suite_Category","ObsDate"])
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
        st.plotly_chart(fig, use_container_width=True)

# ── Tab 4: World Map ──────────────────────────────────────────────────────────
with tab4:
    fc1, fc2, fc3, fc4 = st.columns(4)
    sel_yr_map  = fc1.multiselect("Arrival year", all_years, default=all_years, key="map_yr")
    sel_mon_map = fc2.multiselect("Arrival month", list(range(1,13)),
                                   format_func=lambda x: MONTH_NAMES[x],
                                   default=list(range(1,13)), key="map_mon")
    sel_area_map= fc3.multiselect("Area", sorted(df_last["AreaLabel"].unique()),
                                   default=sorted(df_last["AreaLabel"].unique()), key="map_area")
    map_view    = fc4.radio("Color by", ["Company","Area"], key="map_view")

    df_map = df_last.copy()
    if sel_yr_map:   df_map = df_map[df_map["ArrivalYear"].isin(sel_yr_map)]
    if sel_mon_map:  df_map = df_map[df_map["ArrivalMonth"].isin(sel_mon_map)]
    if sel_area_map: df_map = df_map[df_map["AreaLabel"].isin(sel_area_map)]

    grp_map = (df_map.drop_duplicates(subset=["Company","Voyage","Area","Suite_Category","ObsDate"])
               .groupby(["AreaLabel","Company","AreaLat","AreaLon"],as_index=False)["ABD"].sum())

    if grp_map.empty:
        st.info("No data for selected filters.")
    else:
        color_col = "Company" if map_view=="Company" else "AreaLabel"
        cmap      = COMPANY_COLORS if map_view=="Company" else AREA_COLORS
        fig_map = px.scatter_geo(
            grp_map, lat="AreaLat", lon="AreaLon",
            size="ABD", color=color_col, color_discrete_map=cmap,
            hover_name="AreaLabel",
            hover_data={"ABD":":,.0f","AreaLat":False,"AreaLon":False},
            size_max=70, projection="natural earth",
            labels={"AreaLabel":"Area"})
        fig_map.update_layout(
            height=580, margin=dict(t=10,b=0,l=0,r=0),
            paper_bgcolor="white",
            geo=dict(showframe=False, showcoastlines=True,
                     coastlinecolor="#aaaaaa", showland=True,
                     landcolor="#f5f5f0", showocean=True, oceancolor="#d4eaf7",
                     showlakes=True, lakecolor="#d4eaf7",
                     showcountries=True, countrycolor="#dddddd"))
        st.plotly_chart(fig_map, use_container_width=True)

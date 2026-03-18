import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES, SUITE_ORDER,
                                COMPANY_COLORS, AREA_COLORS,
                                convert_ppd, wavg_ppd, get_two_latest_obs)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header, style_pct_heatmap, style_numeric_heatmap

st.set_page_config(page_title="Pricing", layout="wide")
inject_css()

DATA_PATH = "SilverWatch_PowerBi_input_ALL_MARKETS.xlsx"
df_full   = load_data(DATA_PATH)
filters   = render_sidebar(df_full)

df_base = apply_filters(
    df_full, companies=filters["companies"], areas=filters["areas"],
    markets=filters["markets"], cruise_types=filters["cruise_types"],
    years=filters["years"], months=filters["months"],
    obs_dates=filters["obs_dates"], suite_cats=filters["suite_cats"],
    exclude_outliers=filters["exclude_outliers"],
    future_only=filters["future_only"], last_obs_date=filters["last_obs_date"],
    available_only=True,
)

cur = filters["currency"]
fx  = filters["fx_rates"]
CUR_SYM = {"USD":"$","EUR":"€","GBP":"£","AUD":"A$"}
sym = CUR_SYM.get(cur, cur+" ")

df_base = df_base.copy()
df_base["PPD_conv"] = convert_ppd(df_base, cur, fx)

last_obs  = sorted(df_base["ObsDate"].dropna().unique())[-1] if df_base["ObsDate"].notna().any() else None
df_last   = df_base[df_base["ObsDate"] == last_obs] if last_obs else df_base
obs_prev, obs_last2 = get_two_latest_obs(df_base)
all_years = sorted(df_base["ArrivalYear"].dropna().unique().astype(int))
all_obs   = sorted(df_base["ObsDate"].dropna().unique())
CHART_STYLE = dict(paper_bgcolor="white", plot_bgcolor="#fafafa")

# ── Sticky header block ───────────────────────────────────────────────────────
page_header("Pricing",
    "Entry PPD analysis — Available bookings only, ABD-weighted averages.")

# Shared top filters
fc1,fc2,fc3,fc4,fc5,fc6 = st.columns([1,1,1,2,2,1])
sel_yr_p   = fc1.multiselect("Arrival year",  all_years, default=all_years, key="p_yr")
sel_mon_p  = fc2.multiselect("Month", list(range(1,13)),
                              format_func=lambda x: MONTH_NAMES[x],
                              default=list(range(1,13)), key="p_mon")
sel_ct_p   = fc3.multiselect("Cruise type", ["Classic","Expedition"],
                              default=["Classic","Expedition"], key="p_ct")
sel_co_p   = fc4.multiselect("Companies", sorted(df_last["Company"].unique()),
                              default=sorted(df_last["Company"].unique()), key="p_co")
sel_ar_p   = fc5.multiselect("Area", sorted(df_last["AreaLabel"].unique()),
                              default=sorted(df_last["AreaLabel"].unique()), key="p_area")
sel_suite_p= fc6.multiselect("Suites", SUITE_ORDER, default=["Veranda Suite"], key="p_suite")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "By destination & month", "Over time", "Cruise drill-down"])

def top_filter(df):
    m = pd.Series(True, index=df.index)
    if sel_yr_p:    m &= df["ArrivalYear"].isin(sel_yr_p)
    if sel_mon_p:   m &= df["ArrivalMonth"].isin(sel_mon_p)
    if sel_ct_p:    m &= df["CruiseType"].isin(sel_ct_p)
    if sel_co_p:    m &= df["Company"].isin(sel_co_p)
    if sel_ar_p:    m &= df["AreaLabel"].isin(sel_ar_p)
    if sel_suite_p: m &= df["Suite_Category"].isin(sel_suite_p)
    return df[m]

df_f      = top_filter(df_base)
df_f_last = top_filter(df_last)

# ── Tab 1: Overview ───────────────────────────────────────────────────────────
with tab1:
    companies_shown = sel_co_p or sorted(df_f_last["Company"].unique())
    kpi_cols = st.columns(min(len(companies_shown), 8))
    for i, co in enumerate(companies_shown):
        v = wavg_ppd(df_f_last[df_f_last["Company"] == co])
        kpi_cols[i].metric(co, f"{sym}{v:,.0f}" if pd.notna(v) else "N/A")
    st.divider()

    c1, c2 = st.columns([3,1])
    with c2:
        chart_mode = st.radio("Chart", ["Bar","Box"], key="ov_chart")
    with c1:
        if chart_mode == "Bar":
            grp = df_f_last.groupby("Company").apply(wavg_ppd).reset_index()
            grp.columns = ["Company","PPD"]
            fig = px.bar(grp.sort_values("PPD", ascending=False),
                         x="Company", y="PPD", color="Company",
                         color_discrete_map=COMPANY_COLORS, text_auto=".0f",
                         labels={"PPD": f"Avg PPD ({cur})"})
            fig.update_traces(textposition="outside")
        else:
            fig = px.box(df_f_last, x="Company", y="PPD_conv", color="Company",
                         color_discrete_map=COMPANY_COLORS,
                         labels={"PPD_conv": f"PPD ({cur})"})
        fig.update_layout(height=340, showlegend=False,
                          margin=dict(t=10,b=40,l=40,r=10), **CHART_STYLE)
        st.plotly_chart(fig, use_container_width=True)

    # Suite breakdown bar
    grp2 = df_f_last.groupby(["Company","Suite_Category"]).apply(wavg_ppd).reset_index()
    grp2.columns = ["Company","Suite_Category","PPD"]
    grp2["Suite_Category"] = pd.Categorical(grp2["Suite_Category"],
                                             categories=SUITE_ORDER, ordered=True)
    fig2 = px.bar(grp2.sort_values("Suite_Category"), x="Company", y="PPD",
                  color="Suite_Category", barmode="group",
                  color_discrete_map={"Vista Suite":"#d62728",
                                      "Veranda Suite":"#1f77b4",
                                      "Upper Suite":"#2ca02c"},
                  category_orders={"Suite_Category": SUITE_ORDER},
                  labels={"PPD": f"Avg PPD ({cur})"})
    fig2.update_layout(height=300, margin=dict(t=10,b=40,l=40,r=10), **CHART_STYLE)
    st.plotly_chart(fig2, use_container_width=True)

# ── Tab 2: By destination & month ─────────────────────────────────────────────
with tab2:
    avail_cos = sorted(df_f_last["Company"].unique())
    fc1, fc2  = st.columns(2)
    co_dm_a = fc1.selectbox("Company A", avail_cos, index=0, key="dm_a")
    co_dm_b = fc2.selectbox("Company B", avail_cos,
                             index=min(1, len(avail_cos)-1), key="dm_b")

    def area_month_pivot(co):
        sub = df_f_last[df_f_last["Company"] == co]
        grp = sub.groupby(["AreaLabel","ArrivalMonth"]).apply(wavg_ppd).reset_index()
        grp.columns = ["AreaLabel","ArrivalMonth","PPD"]
        p = grp.pivot_table(index="AreaLabel", columns="ArrivalMonth",
                            values="PPD", aggfunc="mean")
        p.columns = [MONTH_NAMES.get(c, c) for c in p.columns]
        return p

    pa = area_month_pivot(co_dm_a)
    pb = area_month_pivot(co_dm_b)

    def make_heatmap(pivot, title):
        vals = pivot.values.astype(float)
        finite = vals[np.isfinite(vals)]
        vmin = float(finite.min()) if len(finite) else 0
        vmax = float(finite.max()) if len(finite) else 1
        def _col(v):
            if not np.isfinite(v): return "#eeeeee"
            t = max(0.0, min(1.0, (v-vmin)/(vmax-vmin) if vmax>vmin else 0.5))
            r = int(255 - t*180); g = int(255 - t*80); b = int(255 - t*20)
            return f"#{r:02x}{g:02x}{b:02x}"
        def cell_style(val):
            if pd.isna(val): return "background-color:#f5f5f5; color:#aaaaaa"
            bg = _col(float(val))
            r,g,b = int(bg[1:3],16),int(bg[3:5],16),int(bg[5:7],16)
            fg = "#ffffff" if 0.299*r+0.587*g+0.114*b < 140 else "#111111"
            return f"background-color:{bg}; color:{fg}; font-size:0.82rem; font-weight:500"
        styled = pivot.style.applymap(cell_style).format("{:,.0f}", na_rep="—")
        return styled, title

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**{co_dm_a}**")
        s, _ = make_heatmap(pa, co_dm_a)
        st.dataframe(s, use_container_width=True,
                     height=max(220, len(pa)*28+50))
    with col2:
        st.markdown(f"**{co_dm_b}**")
        s, _ = make_heatmap(pb, co_dm_b)
        st.dataframe(s, use_container_width=True,
                     height=max(220, len(pb)*28+50))
    with col3:
        st.markdown(f"**{co_dm_b} vs {co_dm_a} (%)**")
        common_rows = pa.index.intersection(pb.index)
        common_cols = pa.columns.intersection(pb.columns)
        if len(common_rows) and len(common_cols):
            diff_pct = ((pb.loc[common_rows, common_cols] -
                          pa.loc[common_rows, common_cols]) /
                         pa.loc[common_rows, common_cols].replace(0, np.nan) * 100).round(1)
            st.dataframe(style_pct_heatmap(diff_pct, fmt="{:+.1f}%"),
                         use_container_width=True,
                         height=max(220, len(diff_pct)*28+50))
        else:
            st.info("No common area/month data.")

# ── Tab 3: Over time ──────────────────────────────────────────────────────────
with tab3:
    c1, c2 = st.columns([3,1])
    with c2:
        grp_by = st.radio("Group by", ["Company","Area"], key="ot_grp")
    cmap = COMPANY_COLORS if grp_by == "Company" else AREA_COLORS
    grp_ot = df_f.groupby([grp_by,"ObsDate"]).apply(wavg_ppd).reset_index()
    grp_ot.columns = [grp_by,"ObsDate","PPD"]
    with c1:
        fig_ot = px.line(grp_ot.sort_values("ObsDate"), x="ObsDate", y="PPD",
                         color=grp_by, markers=True, color_discrete_map=cmap,
                         labels={"ObsDate":"Observation date","PPD":f"Avg PPD ({cur})"})
        fig_ot.update_layout(height=360, margin=dict(t=10,b=40,l=40,r=10), **CHART_STYLE)
        st.plotly_chart(fig_ot, use_container_width=True)

    st.markdown(f"**PPD % change: {obs_prev} → {obs_last2}**")
    def ppd_snap(obs):
        sub = df_f[df_f["ObsDate"] == obs]
        return sub.groupby(grp_by).apply(wavg_ppd).reset_index().rename(columns={0:"PPD"})
    pa2 = ppd_snap(obs_prev); pb2 = ppd_snap(obs_last2)
    dp  = pa2.merge(pb2, on=grp_by, suffixes=("_prev","_last"))
    dp["Delta_pct"] = ((dp["PPD_last"] - dp["PPD_prev"]) /
                        dp["PPD_prev"].replace(0, np.nan) * 100).round(1)
    fig_dp = px.bar(dp.sort_values("Delta_pct"), x=grp_by, y="Delta_pct",
                    color=grp_by, color_discrete_map=cmap, text_auto=".1f",
                    labels={"Delta_pct":"PPD Δ%"})
    fig_dp.add_hline(y=0, line_color="black", line_width=1)
    fig_dp.update_traces(textposition="outside")
    fig_dp.update_layout(height=280, showlegend=False,
                         margin=dict(t=10,b=40,l=40,r=10), **CHART_STYLE)
    st.plotly_chart(fig_dp, use_container_width=True)

# ── Tab 4: Cruise drill-down matrix ──────────────────────────────────────────
with tab4:
    st.caption("One matrix per company: voyages (ship + departure) × obs dates | PPD values + % change vs previous snapshot")

    for co in (sel_co_p or sorted(df_f["Company"].unique())):
        df_co = df_f[df_f["Company"] == co].copy()
        if df_co.empty:
            continue
        df_co = df_co.sort_values(["ShipName","DepartureDate"])
        df_co["RowLabel"] = (df_co["ShipName"].str.split().str[-1] + " " +
                              df_co["DepartureDate"].dt.strftime("%m/%d") + " · " +
                              df_co["Itinerary"])

        grp = (df_co.groupby(["RowLabel","ObsDate"])
               .apply(wavg_ppd).reset_index()
               .rename(columns={0:"PPD"}))
        pivot_ppd = grp.pivot_table(index="RowLabel", columns="ObsDate",
                                     values="PPD", aggfunc="mean")

        # % change vs previous obs
        pivot_pct = pd.DataFrame(index=pivot_ppd.index,
                                  columns=pivot_ppd.columns, dtype=float)
        for i, col in enumerate(pivot_ppd.columns):
            if i == 0:
                pivot_pct[col] = np.nan
            else:
                prev = pivot_ppd.columns[i-1]
                pivot_pct[col] = ((pivot_ppd[col] - pivot_ppd[prev]) /
                                   pivot_ppd[prev].replace(0, np.nan) * 100).round(1)

        st.markdown(f"##### {co}")
        col_a, col_b = st.columns(2)

        h = min(600, max(200, len(pivot_ppd)*24+50))

        with col_a:
            st.markdown(f"*Entry PPD ({cur})*")
            st.dataframe(
                style_numeric_heatmap(pivot_ppd.astype(float),
                                       fmt="{:,.0f}", na_rep="—"),
                use_container_width=True, height=h)

        with col_b:
            st.markdown("*% change vs previous snapshot*")
            st.dataframe(
                style_pct_heatmap(pivot_pct, fmt="{:+.1f}%", na_rep="—"),
                use_container_width=True, height=h)

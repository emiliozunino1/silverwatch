from utils.auth import require_login, logout_button
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import (load_data, apply_filters, MONTH_NAMES, SUITE_ORDER,
                                COMPANY_COLORS, AREA_COLORS,
                                convert_ppd, wavg_ppd, get_two_latest_obs)
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header, bordered_chart, bordered_dataframe, style_pct_heatmap, style_numeric_heatmap

st.set_page_config(page_title="Pricing", layout="wide")
inject_css()
require_login()
logout_button()

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

cur = filters["currency"]; fx = filters["fx_rates"]
CUR_SYM = {"USD":"$","EUR":"€","GBP":"£","AUD":"A$"}; sym = CUR_SYM.get(cur,cur+" ")
df_base = df_base.copy(); df_base["PPD_conv"] = convert_ppd(df_base,cur,fx)
last_obs  = sorted(df_base["ObsDate"].dropna().unique())[-1] if df_base["ObsDate"].notna().any() else None
df_last   = df_base[df_base["ObsDate"]==last_obs] if last_obs else df_base
obs_prev, obs_last2 = get_two_latest_obs(df_base)
all_years = sorted(df_base["ArrivalYear"].dropna().unique().astype(int))
all_obs   = sorted(df_base["ObsDate"].dropna().unique())
CS = dict(paper_bgcolor="white", plot_bgcolor="#fafafa")

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

tab1,tab2,tab3,tab4 = st.tabs(["Overview","By destination & month","Over time","Cruise drill-down"])

def top_filter(df):
    m = pd.Series(True,index=df.index)
    if sel_yr_p:    m &= df["ArrivalYear"].isin(sel_yr_p)
    if sel_mon_p:   m &= df["ArrivalMonth"].isin(sel_mon_p)
    if sel_ct_p:    m &= df["CruiseType"].isin(sel_ct_p)
    if sel_co_p:    m &= df["Company"].isin(sel_co_p)
    if sel_ar_p:    m &= df["AreaLabel"].isin(sel_ar_p)
    if sel_suite_p: m &= df["Suite_Category"].isin(sel_suite_p)
    return df[m]

df_f = top_filter(df_base); df_f_last = top_filter(df_last)

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    cos = sel_co_p or sorted(df_f_last["Company"].unique())
    kpi = st.columns(min(len(cos),8))
    for i,co in enumerate(cos):
        v = wavg_ppd(df_f_last[df_f_last["Company"]==co])
        kpi[i].metric(co, f"{sym}{v:,.0f}" if pd.notna(v) else "N/A")
    st.divider()
    c1,c2 = st.columns([3,1])
    with c2: chart_mode = st.selectbox("Chart", ["Bar","Box"], key="ov_chart")
    with c1:
        if chart_mode=="Bar":
            grp = df_f_last.groupby("Company").apply(wavg_ppd).reset_index()
            grp.columns = ["Company","PPD"]
            fig = px.bar(grp.sort_values("PPD",ascending=False), x="Company", y="PPD",
                         color="Company", color_discrete_map=COMPANY_COLORS, text_auto=".0f",
                         labels={"PPD":f"Avg PPD ({cur})"})
            fig.update_traces(textposition="outside")
        else:
            fig = px.box(df_f_last, x="Company", y="PPD_conv", color="Company",
                         color_discrete_map=COMPANY_COLORS, labels={"PPD_conv":f"PPD ({cur})"})
        fig.update_layout(height=340,showlegend=False,margin=dict(t=10,b=40,l=40,r=10),**CS)
        bordered_chart(fig, use_container_width=True)

    grp2 = df_f_last.groupby(["Company","Suite_Category"]).apply(wavg_ppd).reset_index()
    grp2.columns = ["Company","Suite_Category","PPD"]
    grp2["Suite_Category"] = pd.Categorical(grp2["Suite_Category"],categories=SUITE_ORDER,ordered=True)
    fig2 = px.bar(grp2.sort_values("Suite_Category"), x="Company", y="PPD",
                  color="Suite_Category", barmode="group",
                  color_discrete_map={"Vista Suite":"#d62728","Veranda Suite":"#1f77b4","Upper Suite":"#2ca02c"},
                  category_orders={"Suite_Category":SUITE_ORDER}, labels={"PPD":f"Avg PPD ({cur})"})
    fig2.update_layout(height=300,margin=dict(t=10,b=40,l=40,r=10),**CS)
    bordered_chart(fig2, use_container_width=True)

# ── Tab 2: Three tables stacked vertically ─────────────────────────────────────
with tab2:
    avail_cos = sorted(df_f_last["Company"].unique())
    c1,c2 = st.columns(2)
    co_dm_a = c1.selectbox("Company A", avail_cos, index=0, key="dm_a")
    co_dm_b = c2.selectbox("Company B", avail_cos, index=min(1,len(avail_cos)-1), key="dm_b")

    def area_month_pivot(co):
        sub = df_f_last[df_f_last["Company"]==co]
        grp = sub.groupby(["AreaLabel","ArrivalMonth"]).apply(wavg_ppd).reset_index()
        grp.columns = ["AreaLabel","ArrivalMonth","PPD"]
        p = grp.pivot_table(index="AreaLabel",columns="ArrivalMonth",values="PPD",aggfunc="mean")
        p.columns = [MONTH_NAMES.get(c,c) for c in p.columns]
        return p

    pa = area_month_pivot(co_dm_a); pb = area_month_pivot(co_dm_b)

    def make_cell_styler(pivot):
        vals = pivot.values.astype(float)
        fin = vals[np.isfinite(vals)]
        vmin = float(fin.min()) if len(fin) else 0
        vmax = float(fin.max()) if len(fin) else 1
        def cell(val):
            if pd.isna(val): return "background-color:#f5f5f5; color:#aaa; text-align:center"
            try: v = float(val)
            except: return "text-align:center"
            t = max(0.0,min(1.0,(v-vmin)/(vmax-vmin) if vmax>vmin else 0.5))
            r=int(255-t*180); g=int(255-t*80); b=int(255-t*20)
            bg=f"#{r:02x}{g:02x}{b:02x}"
            r2,g2,b2=int(bg[1:3],16),int(bg[3:5],16),int(bg[5:7],16)
            fg="#ffffff" if 0.299*r2+0.587*g2+0.114*b2<140 else "#111111"
            return f"background-color:{bg}; color:{fg}; font-size:0.82rem; font-weight:500; text-align:center"
        return (pivot.style.applymap(cell).format("{:,.0f}",na_rep="—")
                .set_properties(**{"text-align":"center"})
                .set_table_styles([{"selector":"th","props":[("text-align","center")]},
                                   {"selector":"th.row_heading","props":[("text-align","left")]}]))

    # Table A
    st.markdown(f"**{co_dm_a}**")
    bordered_dataframe(make_cell_styler(pa), use_container_width=True,
                       height=max(180, len(pa)*28+50))

    # Table B
    st.markdown(f"**{co_dm_b}**")
    bordered_dataframe(make_cell_styler(pb), use_container_width=True,
                       height=max(180, len(pb)*28+50))

    # Diff table
    st.markdown(f"**{co_dm_b} vs {co_dm_a} (% difference)**")
    common_rows = pa.index.intersection(pb.index)
    common_cols = pa.columns.intersection(pb.columns)
    if len(common_rows) and len(common_cols):
        diff = ((pb.loc[common_rows,common_cols]-pa.loc[common_rows,common_cols]) /
                 pa.loc[common_rows,common_cols].replace(0,np.nan)*100).round(1)
        bordered_dataframe(style_pct_heatmap(diff,fmt="{:+.1f}%"),
                           use_container_width=True,
                           height=max(180,len(diff)*28+50))
    else:
        st.info("No common area/month data.")

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    c1,c2 = st.columns([3,1])
    with c2: grp_by = st.selectbox("Group by", ["Company","Area"], key="ot_grp")
    cmap = COMPANY_COLORS if grp_by=="Company" else AREA_COLORS
    grp_ot = df_f.groupby([grp_by,"ObsDate"]).apply(wavg_ppd).reset_index()
    grp_ot.columns = [grp_by,"ObsDate","PPD"]
    with c1:
        fig_ot = px.line(grp_ot.sort_values("ObsDate"), x="ObsDate", y="PPD",
                         color=grp_by, markers=True, color_discrete_map=cmap,
                         labels={"ObsDate":"Observation date","PPD":f"Avg PPD ({cur})"})
        fig_ot.update_layout(height=360,margin=dict(t=10,b=40,l=40,r=10),**CS)
        bordered_chart(fig_ot, use_container_width=True)

    st.markdown(f"**PPD % change: {obs_prev} → {obs_last2}**")
    def ppd_snap(obs):
        return df_f[df_f["ObsDate"]==obs].groupby(grp_by).apply(wavg_ppd).reset_index().rename(columns={0:"PPD"})
    pa2=ppd_snap(obs_prev); pb2=ppd_snap(obs_last2)
    dp=pa2.merge(pb2,on=grp_by,suffixes=("_prev","_last"))
    dp["Delta_pct"]=((dp["PPD_last"]-dp["PPD_prev"])/dp["PPD_prev"].replace(0,np.nan)*100).round(1)
    fig_dp=px.bar(dp.sort_values("Delta_pct"),x=grp_by,y="Delta_pct",
                  color=grp_by,color_discrete_map=cmap,text_auto=".1f",labels={"Delta_pct":"PPD Δ%"})
    fig_dp.add_hline(y=0,line_color="black",line_width=1)
    fig_dp.update_traces(textposition="outside")
    fig_dp.update_layout(height=280,showlegend=False,margin=dict(t=10,b=40,l=40,r=10),**CS)
    bordered_chart(fig_dp, use_container_width=True)

# ── Tab 4: Cruise drill-down — merged matrix ───────────────────────────────────
with tab4:
    st.caption("One matrix per company: rows = Ship · Month · Departure · Area, columns = obs dates (PPD) + % change vs previous")

    for co in (sel_co_p or sorted(df_f["Company"].unique())):
        df_co = df_f[df_f["Company"]==co].copy()
        if df_co.empty: continue
        df_co = df_co.sort_values(["ShipName","ArrivalMonth","DepartureDate"])
        df_co["ShipShort"] = df_co["ShipName"].str.split().str[-1]
        df_co["MonthName"] = df_co["ArrivalMonth"].map(MONTH_NAMES)
        df_co["RowLabel"]  = (df_co["ShipShort"] + " · " +
                               df_co["MonthName"] + " · " +
                               df_co["DepartureDate"].dt.strftime("%m/%d") + " · " +
                               df_co["AreaLabel"].str[:10])

        grp = (df_co.groupby(["RowLabel","ObsDate"])
               .apply(wavg_ppd).reset_index().rename(columns={0:"PPD"}))
        pivot_ppd = grp.pivot_table(index="RowLabel",columns="ObsDate",values="PPD",aggfunc="mean")
        pivot_ppd.columns = [str(c) for c in pivot_ppd.columns]

        # % change vs previous obs
        pivot_pct = pd.DataFrame(index=pivot_ppd.index,columns=pivot_ppd.columns,dtype=float)
        for i,col in enumerate(pivot_ppd.columns):
            if i==0: pivot_pct[col] = np.nan
            else:
                prev = pivot_ppd.columns[i-1]
                pivot_pct[col] = ((pivot_ppd[col]-pivot_ppd[prev]) /
                                   pivot_ppd[prev].replace(0,np.nan)*100).round(1)

        # Merge: PPD cols + pct cols side by side
        merged = pd.DataFrame(index=pivot_ppd.index)
        obs_list = pivot_ppd.columns.tolist()
        for i,col in enumerate(obs_list):
            merged[f"PPD {col}"] = pivot_ppd[col].map(
                lambda x: f"{sym}{x:,.0f}" if pd.notna(x) else "—")
            if i>0:
                merged[f"Δ% {col}"] = pivot_pct[col].map(
                    lambda x: f"{x:+.1f}%" if pd.notna(x) and np.isfinite(x) else "—")

        def merged_cell(val):
            if not isinstance(val,str) or val=="—": return "text-align:center; color:#aaa"
            if val.startswith(("+","-")) and val.endswith("%"):
                try:
                    v=float(val.replace("%","").replace("+",""))
                    if v>0: return "color:#155724; font-weight:500; text-align:center"
                    if v<0: return "color:#721c24; font-weight:500; text-align:center"
                except: pass
            return "text-align:center"

        st.markdown(f"##### {co}")
        bordered_dataframe(
            merged.style.applymap(merged_cell)
                        .set_properties(**{"text-align":"center"})
                        .set_table_styles([
                            {"selector":"th","props":[("text-align","center")]},
                            {"selector":"th.row_heading","props":[("text-align","left")]}]),
            use_container_width=True,
            height=min(700, max(200, len(merged)*26+60)))

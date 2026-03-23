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
df_full = load_data(DATA_PATH)
filters = render_sidebar(df_full)

df_base = apply_filters(df_full, companies=filters["companies"], areas=filters["areas"],
    markets=filters["markets"], cruise_types=filters["cruise_types"],
    years=filters["years"], months=filters["months"], obs_dates=filters["obs_dates"],
    suite_cats=filters["suite_cats"], exclude_outliers=filters["exclude_outliers"],
    future_only=filters["future_only"], last_obs_date=filters["last_obs_date"],
    available_only=True)

cur=filters["currency"]; fx=filters["fx_rates"]
sym={"USD":"$","EUR":"€","GBP":"£","AUD":"A$"}.get(cur,cur+" ")
df_base=df_base.copy(); df_base["PPD_conv"]=convert_ppd(df_base,cur,fx)
last_obs =sorted(df_base["ObsDate"].dropna().unique())[-1] if df_base["ObsDate"].notna().any() else None
df_last  =df_base[df_base["ObsDate"]==last_obs] if last_obs else df_base
obs_prev,obs_last2=get_two_latest_obs(df_base)
all_years=sorted(df_base["ArrivalYear"].dropna().unique().astype(int))
all_cos  =sorted(df_last["Company"].unique())
all_areas=sorted(df_last["AreaLabel"].unique())
CS=dict(paper_bgcolor="white",plot_bgcolor="#fafafa")

page_header("Pricing","Entry PPD — Available bookings only, ABD-weighted averages.")

# Shared top filters — compact single row
f=st.columns([1,1,1,2,2,1])
sel_yr   =f[0].multiselect("Year",  all_years, default=all_years, key="p_yr")
sel_mon  =f[1].multiselect("Month", list(range(1,13)), format_func=lambda x:MONTH_NAMES[x],
                            default=list(range(1,13)), key="p_mon")
sel_ct   =f[2].multiselect("Type",  ["Classic","Expedition"], default=["Classic","Expedition"], key="p_ct")
sel_co   =f[3].multiselect("Companies", all_cos, default=all_cos, key="p_co")
sel_ar   =f[4].multiselect("Area",  all_areas, default=all_areas, key="p_area")
sel_suite=f[5].multiselect("Suites",SUITE_ORDER, default=["Veranda Suite"], key="p_suite")

tab1,tab2,tab3,tab4=st.tabs(["Overview","By destination & month","Over time","Cruise drill-down"])

def top_filter(df):
    m=pd.Series(True,index=df.index)
    if sel_yr:    m&=df["ArrivalYear"].isin(sel_yr)
    if sel_mon:   m&=df["ArrivalMonth"].isin(sel_mon)
    if sel_ct:    m&=df["CruiseType"].isin(sel_ct)
    if sel_co:    m&=df["Company"].isin(sel_co)
    if sel_ar:    m&=df["AreaLabel"].isin(sel_ar)
    if sel_suite: m&=df["Suite_Category"].isin(sel_suite)
    return df[m]

df_f=top_filter(df_base); df_fl=top_filter(df_last)

with tab1:
    cos=sel_co or all_cos
    kpi=st.columns(min(len(cos),8))
    for i,co in enumerate(cos):
        v=wavg_ppd(df_fl[df_fl["Company"]==co])
        kpi[i].metric(co,f"{sym}{v:,.0f}" if pd.notna(v) else "N/A")

    f2=st.columns([3,1])
    chart_mode=f2[1].selectbox("Chart",["Bar","Box"],key="ov_chart")
    with f2[0]:
        if chart_mode=="Bar":
            grp=df_fl.groupby("Company").apply(wavg_ppd).reset_index()
            grp.columns=["Company","PPD"]
            fig=px.bar(grp.sort_values("PPD",ascending=False),x="Company",y="PPD",
                       color="Company",color_discrete_map=COMPANY_COLORS,text_auto=".0f",
                       labels={"PPD":f"PPD ({cur})"})
            fig.update_traces(textposition="outside")
        else:
            fig=px.box(df_fl,x="Company",y="PPD_conv",color="Company",
                       color_discrete_map=COMPANY_COLORS,labels={"PPD_conv":f"PPD ({cur})"})
        fig.update_layout(height=300,showlegend=False,margin=dict(t=10,b=40,l=40,r=10),**CS)
        bordered_chart(fig,use_container_width=True)

    grp2=df_fl.groupby(["Company","Suite_Category"]).apply(wavg_ppd).reset_index()
    grp2.columns=["Company","Suite_Category","PPD"]
    grp2["Suite_Category"]=pd.Categorical(grp2["Suite_Category"],categories=SUITE_ORDER,ordered=True)
    fig2=px.bar(grp2.sort_values("Suite_Category"),x="Company",y="PPD",color="Suite_Category",
                barmode="group",
                color_discrete_map={"Vista Suite":"#d62728","Veranda Suite":"#1f77b4","Upper Suite":"#2ca02c"},
                category_orders={"Suite_Category":SUITE_ORDER},labels={"PPD":f"PPD ({cur})"})
    fig2.update_layout(height=280,margin=dict(t=10,b=40,l=40,r=10),**CS)
    bordered_chart(fig2,use_container_width=True)

with tab2:
    f2=st.columns(2)
    co_a=f2[0].selectbox("Company A",all_cos,index=0,key="dm_a")
    co_b=f2[1].selectbox("Company B",all_cos,index=min(1,len(all_cos)-1),key="dm_b")

    def amp(co):
        sub=df_fl[df_fl["Company"]==co]
        grp=sub.groupby(["AreaLabel","ArrivalMonth"]).apply(wavg_ppd).reset_index()
        grp.columns=["AreaLabel","ArrivalMonth","PPD"]
        p=grp.pivot_table(index="AreaLabel",columns="ArrivalMonth",values="PPD",aggfunc="mean")
        p.columns=[MONTH_NAMES.get(c,c) for c in p.columns]
        return p

    pa=amp(co_a); pb=amp(co_b)

    def cell_styler(pivot):
        vals=pivot.values.astype(float)
        fin=vals[np.isfinite(vals)]
        vmin=float(fin.min()) if len(fin) else 0; vmax=float(fin.max()) if len(fin) else 1
        def cell(val):
            if pd.isna(val): return "background-color:#f5f5f5;color:#aaa;text-align:center"
            try: v=float(val)
            except: return "text-align:center"
            t=max(0.0,min(1.0,(v-vmin)/(vmax-vmin) if vmax>vmin else 0.5))
            r=int(255-t*180); g=int(255-t*80); b=int(255-t*20)
            bg=f"#{r:02x}{g:02x}{b:02x}"
            r2,g2,b2=int(bg[1:3],16),int(bg[3:5],16),int(bg[5:7],16)
            fg="#fff" if 0.299*r2+0.587*g2+0.114*b2<140 else "#111"
            return f"background-color:{bg};color:{fg};font-size:0.82rem;font-weight:500;text-align:center"
        return (pivot.style.applymap(cell).format("{:,.0f}",na_rep="—")
                .set_properties(**{"text-align":"center"})
                .set_table_styles([{"selector":"th","props":[("text-align","center")]},
                                   {"selector":"th.row_heading","props":[("text-align","left")]}]))

    st.markdown(f"**{co_a}**")
    bordered_dataframe(cell_styler(pa),use_container_width=True,height=max(160,len(pa)*28+50))
    st.markdown(f"**{co_b}**")
    bordered_dataframe(cell_styler(pb),use_container_width=True,height=max(160,len(pb)*28+50))
    st.markdown(f"**{co_b} vs {co_a} (% diff)**")
    cr=pa.index.intersection(pb.index); cc=pa.columns.intersection(pb.columns)
    if len(cr) and len(cc):
        diff=((pb.loc[cr,cc]-pa.loc[cr,cc])/pa.loc[cr,cc].replace(0,np.nan)*100).round(1)
        bordered_dataframe(style_pct_heatmap(diff),use_container_width=True,height=max(160,len(diff)*28+50))

with tab3:
    f3=st.columns([3,1])
    grp_by=f3[1].selectbox("Group by",["Company","Area"],key="ot_grp")
    cmap=COMPANY_COLORS if grp_by=="Company" else AREA_COLORS
    grp_ot=df_f.groupby([grp_by,"ObsDate"]).apply(wavg_ppd).reset_index()
    grp_ot.columns=[grp_by,"ObsDate","PPD"]
    with f3[0]:
        fig_ot=px.line(grp_ot.sort_values("ObsDate"),x="ObsDate",y="PPD",
                       color=grp_by,markers=True,color_discrete_map=cmap,
                       labels={"ObsDate":"Observation date","PPD":f"PPD ({cur})"})
        fig_ot.update_layout(height=320,margin=dict(t=10,b=40,l=40,r=10),**CS)
        bordered_chart(fig_ot,use_container_width=True)

    st.caption(f"PPD % change: **{obs_prev} → {obs_last2}**")
    def ppd_snap(obs):
        return df_f[df_f["ObsDate"]==obs].groupby(grp_by).apply(wavg_ppd).reset_index().rename(columns={0:"PPD"})
    dp=ppd_snap(obs_prev).merge(ppd_snap(obs_last2),on=grp_by,suffixes=("_p","_l"))
    dp["Δ%"]=((dp["PPD_l"]-dp["PPD_p"])/dp["PPD_p"].replace(0,np.nan)*100).round(1)
    fig_dp=px.bar(dp.sort_values("Δ%"),x=grp_by,y="Δ%",color=grp_by,
                  color_discrete_map=cmap,text_auto=".1f",labels={"Δ%":"PPD Δ%"})
    fig_dp.add_hline(y=0,line_color="black",line_width=1)
    fig_dp.update_traces(textposition="outside")
    fig_dp.update_layout(height=260,showlegend=False,margin=dict(t=10,b=40,l=40,r=10),**CS)
    bordered_chart(fig_dp,use_container_width=True)

with tab4:
    st.caption("Rows: Ship · Month · Departure · Area | Columns: obs dates PPD + Δ% vs previous")
    for co in (sel_co or all_cos):
        df_co=df_f[df_f["Company"]==co].copy()
        if df_co.empty: continue
        df_co=df_co.sort_values(["ShipName","ArrivalMonth","DepartureDate"])
        df_co["ShipShort"]=df_co["ShipName"].str.split().str[-1]
        df_co["MonthName"]=df_co["ArrivalMonth"].map(MONTH_NAMES)
        df_co["RowLabel"]=(df_co["ShipShort"]+" · "+df_co["MonthName"]+" · "+
                           df_co["DepartureDate"].dt.strftime("%m/%d")+" · "+
                           df_co["AreaLabel"].str[:10])
        grp=(df_co.groupby(["RowLabel","ObsDate"]).apply(wavg_ppd)
             .reset_index().rename(columns={0:"PPD"}))
        piv=grp.pivot_table(index="RowLabel",columns="ObsDate",values="PPD",aggfunc="mean")
        piv.columns=[str(c) for c in piv.columns]
        pct=pd.DataFrame(index=piv.index,columns=piv.columns,dtype=float)
        for i,col in enumerate(piv.columns):
            if i==0: pct[col]=np.nan
            else:
                prev=piv.columns[i-1]
                pct[col]=((piv[col]-piv[prev])/piv[prev].replace(0,np.nan)*100).round(1)
        merged=pd.DataFrame(index=piv.index)
        for i,col in enumerate(piv.columns):
            merged[f"PPD {col}"]=piv[col].map(lambda x:f"{sym}{x:,.0f}" if pd.notna(x) else "—")
            if i>0:
                merged[f"Δ% {col}"]=pct[col].map(lambda x:f"{x:+.1f}%" if pd.notna(x) and np.isfinite(x) else "—")
        def mc(val):
            if not isinstance(val,str) or val=="—": return "text-align:center;color:#aaa"
            if val.startswith(("+","-")) and val.endswith("%"):
                try:
                    v=float(val.replace("%","").replace("+",""))
                    if v>0: return "color:#155724;font-weight:500;text-align:center"
                    if v<0: return "color:#721c24;font-weight:500;text-align:center"
                except: pass
            return "text-align:center"
        st.markdown(f"##### {co}")
        bordered_dataframe(
            merged.style.applymap(mc)
                        .set_properties(**{"text-align":"center"})
                        .set_table_styles([
                            {"selector":"th","props":[("text-align","center")]},
                            {"selector":"th.row_heading","props":[("text-align","left")]}]),
            use_container_width=True,height=min(700,max(180,len(merged)*24+50)))

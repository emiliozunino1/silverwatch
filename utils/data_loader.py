import pandas as pd
import numpy as np
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FX_RATES_TO_USD = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "AUD": 0.65}

AREA_LABELS = {
    "MEDT": "Mediterranean", "CARI": "Caribbean", "ASIA": "Asia",
    "NEUR": "N. Europe", "NENG": "New England", "NOAM": "N. America",
    "SOAM": "S. America", "ALAS": "Alaska", "ASNZ": "Australia/NZ",
    "AFIO": "Africa/Indian Ocean", "WRLD": "World Cruise", "TRAN": "Transatlantic",
    "EFLY": "Fly Cruise Europe", "FARE": "Fly Cruise Americas", "GLPG": "Galapagos",
    "KIMB": "Kimberley", "EANT": "Antarctica", "EARC": "Arctic",
    "EXPD": "Expedition", "EXPD ALAS": "Exp. Alaska", "EXPD NENG": "Exp. New England",
    "EXPD NEUR": "Exp. N. Europe", "EXPD NOAM": "Exp. N. America",
    "EXPD OCEA": "Exp. Oceania", "EXPD TRAN": "Exp. Transatlantic",
    "EXPD WRLD": "Exp. World",
}

AREA_COORDS = {
    "Mediterranean":(36.,14.), "Caribbean":(17.,-66.), "Asia":(15.,105.),
    "N. Europe":(57.,5.), "New England":(42.,-70.), "N. America":(38.,-98.),
    "S. America":(-15.,-60.), "Alaska":(61.,-150.), "Australia/NZ":(-33.,151.),
    "Africa/Indian Ocean":(-5.,55.), "World Cruise":(0.,0.), "Transatlantic":(35.,-40.),
    "Fly Cruise Europe":(48.,10.), "Fly Cruise Americas":(25.,-80.),
    "Galapagos":(-0.5,-90.5), "Kimberley":(-16.,126.), "Antarctica":(-75.,0.),
    "Arctic":(80.,0.), "Expedition":(0.,0.), "Exp. Alaska":(61.,-150.),
    "Exp. New England":(42.,-70.), "Exp. N. Europe":(57.,5.),
    "Exp. N. America":(38.,-98.), "Exp. Oceania":(-25.,135.),
    "Exp. Transatlantic":(35.,-40.), "Exp. World":(0.,0.),
}

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
SUITE_ORDER = ["Vista Suite", "Veranda Suite", "Upper Suite"]
PPD_OUTLIER_THRESHOLD = 10_000

COMPANY_COLORS = {
    "Explora":"#1f77b4","Lindblad":"#ff7f0e","Ponant":"#2ca02c",
    "Quark":"#d62728","Regent":"#9467bd","Seabourn":"#8c564b",
    "Silversea":"#e377c2","Viking":"#17becf",
}
AREA_COLORS = {
    "Mediterranean":"#e41a1c","Caribbean":"#377eb8","Asia":"#ff7f00",
    "N. Europe":"#4daf4a","New England":"#984ea3","N. America":"#a65628",
    "S. America":"#f781bf","Alaska":"#999999","Australia/NZ":"#66c2a5",
    "Africa/Indian Ocean":"#fc8d62","World Cruise":"#8da0cb","Transatlantic":"#e78ac3",
    "Fly Cruise Europe":"#a6d854","Fly Cruise Americas":"#ffd92f","Galapagos":"#e5c494",
    "Kimberley":"#b3b3b3","Antarctica":"#1b9e77","Arctic":"#d95f02",
    "Expedition":"#7570b3","Exp. Alaska":"#e7298a","Exp. New England":"#66a61e",
    "Exp. N. Europe":"#e6ab02","Exp. N. America":"#a6761d","Exp. Oceania":"#666666",
    "Exp. Transatlantic":"#a6cee3","Exp. World":"#b2df8a",
}


def _get_port_coords():
    try:
        from port_coords import PORT_COORDS
        return PORT_COORDS
    except ImportError:
        return {}


@st.cache_data(show_spinner="Loading data...")
def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_excel(filepath)
    PORT_COORDS = _get_port_coords()

    # Use CruiseStartDate/CruiseEndDate if available, else parse from Voyage code
    if "CruiseStartDate" in df.columns:
        df["DepartureDate"] = pd.to_datetime(df["CruiseStartDate"], errors="coerce")
    else:
        def parse_dep_day(row):
            v=row["Voyage"]; yr=row["Voyage_Start_Year"]; mo=row["Voyage_Start_Month"]
            try:
                sy,sm,sd=int(v[4:6]),int(v[6:8]),int(v[8:10])
                if sm==mo and (2000+sy)==yr and 1<=sd<=31: return sd
            except (ValueError,IndexError): pass
            try:
                hy,hm,hd=int(v[2:4]),int(v[4:6]),int(v[6:8])
                if hm==mo and (2000+hy)==yr and 1<=hd<=31: return hd
            except (ValueError,IndexError): pass
            return None
        df["dep_day"]  = df.apply(parse_dep_day, axis=1)
        df["dep_year"] = df["Voyage_Start_Year"]
        df["dep_month"]= df["Voyage_Start_Month"]
        df["DepartureDate"] = pd.to_datetime(
            dict(year=df["dep_year"],month=df["dep_month"],day=df["dep_day"].fillna(1)),
            errors="coerce")
        df.loc[df["dep_day"].isna(),"DepartureDate"] = pd.NaT

    if "CruiseEndDate" in df.columns:
        df["ArrivalDate"] = pd.to_datetime(df["CruiseEndDate"], errors="coerce")
    else:
        df["ArrivalDate"] = df["DepartureDate"] + pd.to_timedelta(df["CruiseNights"],unit="D")

    df["ArrivalMonth"]     = df["ArrivalDate"].dt.month
    df["ArrivalYear"]      = df["ArrivalDate"].dt.year.astype("Int64")
    df["ArrivalMonthName"] = df["ArrivalMonth"].map(MONTH_NAMES)
    df["ArrivalWeek"]      = df["ArrivalDate"].dt.isocalendar().week.astype("Int64")
    df["ArrivalWeekSunday"]= df["ArrivalDate"] - pd.to_timedelta(
        (df["ArrivalDate"].dt.dayofweek+1)%7, unit="D")

    obs_sorted = sorted(df["AsDate"].dropna().unique())
    df["ObsDate"]      = df["AsDate"].dt.strftime("%Y-%m-%d")
    df["ObsDateLabel"] = df["AsDate"].map({d: pd.Timestamp(d).strftime("%d %b %Y") for d in obs_sorted})

    df["AreaLabel"] = df["Area"].map(AREA_LABELS).fillna(df["Area"])
    df["AreaLat"]   = df["AreaLabel"].map(lambda x: AREA_COORDS.get(x,(0,0))[0])
    df["AreaLon"]   = df["AreaLabel"].map(lambda x: AREA_COORDS.get(x,(0,0))[1])

    # Port coordinates
    if "Embarkement_Port_Name" in df.columns:
        df["EmbLat"] = df["Embarkement_Port_Name"].map(
            lambda x: PORT_COORDS.get(x,(None,None))[0] if x else None)
        df["EmbLon"] = df["Embarkement_Port_Name"].map(
            lambda x: PORT_COORDS.get(x,(None,None))[1] if x else None)
    else:
        df["Embarkement_Port_Name"]    = None
        df["Disembarkement_Port_Name"] = None
        df["EmbLat"] = None
        df["EmbLon"] = None

    df["PPD_outlier"] = (
        (df["Entry_Ad_PPD"] > PPD_OUTLIER_THRESHOLD) |
        (df["Entry_Ad_PPD"] == 0) | df["Entry_Ad_PPD"].isna()
    )
    return df


def apply_filters(df, companies=None, areas=None, markets=None, cruise_types=None,
                  years=None, months=None, obs_dates=None, suite_cats=None,
                  exclude_outliers=True, master_only=True, available_only=False,
                  future_only=False, last_obs_date=None):
    mask = pd.Series(True, index=df.index)
    if master_only:      mask &= df["Segment_Criteria"] == "MASTER"
    if companies:        mask &= df["Company"].isin(companies)
    if areas:            mask &= df["Area"].isin(areas)
    if markets:          mask &= df["Market"].isin(markets)
    if cruise_types:     mask &= df["CruiseType"].isin(cruise_types)
    if years:            mask &= df["ArrivalYear"].isin(years)
    if months:           mask &= df["ArrivalMonth"].isin(months)
    if obs_dates:        mask &= df["ObsDate"].isin(obs_dates)
    if suite_cats:       mask &= df["Suite_Category"].isin(suite_cats)
    if exclude_outliers: mask &= ~df["PPD_outlier"]
    if available_only:   mask &= df["Availability_tag"] == "Available"
    if future_only and last_obs_date is not None:
        mask &= df["ArrivalDate"] > pd.Timestamp(last_obs_date)
    return df[mask]


def get_two_latest_obs(df):
    obs = sorted(df["ObsDate"].dropna().unique())
    return (obs[-2], obs[-1]) if len(obs) >= 2 else (obs[0], obs[-1])


def safe_abd_delta(df, group_col, obs_prev, obs_last):
    def agg(obs):
        return (df[df["ObsDate"]==obs]
                .drop_duplicates(subset=[group_col,"Company","Voyage","Suite_Category"])
                .groupby(group_col, as_index=False)["ABD"].sum()
                .rename(columns={"ABD":f"ABD_{obs}"}))
    a=agg(obs_prev); b=agg(obs_last)
    m=a.merge(b, on=group_col, how="outer")
    m[f"ABD_{obs_prev}"] = pd.to_numeric(m[f"ABD_{obs_prev}"],errors="coerce").fillna(0)
    m[f"ABD_{obs_last}"] = pd.to_numeric(m[f"ABD_{obs_last}"],errors="coerce").fillna(0)
    m["Delta"]     = m[f"ABD_{obs_last}"] - m[f"ABD_{obs_prev}"]
    m["Delta_pct"] = (m["Delta"]/m[f"ABD_{obs_prev}"].replace(0,np.nan)*100).round(1)
    m.rename(columns={f"ABD_{obs_prev}":"ABD_prev",f"ABD_{obs_last}":"ABD_last"},inplace=True)
    return m


def convert_ppd(df, target_currency, fx_rates):
    rates = df["Curr"].map(fx_rates)
    return df["Entry_Ad_PPD"] * rates / fx_rates.get(target_currency,1.0)


def wavg_ppd(sub):
    w = sub["ABD"]
    return float((sub["PPD_conv"]*w).sum()/w.sum()) if w.sum()>0 else np.nan

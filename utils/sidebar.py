import streamlit as st
import pandas as pd
from utils.data_loader import FX_RATES_TO_USD, MONTH_NAMES


def render_sidebar(df: pd.DataFrame) -> dict:
    st.sidebar.title("Global Filters")

    # Currency
    st.sidebar.subheader("Currency")
    currency = st.sidebar.selectbox("Display currency", ["USD","EUR","GBP","AUD"], index=0)
    fx_rates = {"USD": 1.0}
    with st.sidebar.expander("Custom FX rates (1 unit → USD)"):
        for cur, default in FX_RATES_TO_USD.items():
            if cur != "USD":
                val = st.number_input(f"1 {cur} = ? USD", value=default,
                                       min_value=0.001, step=0.01, format="%.4f",
                                       key=f"fx_{cur}")
                fx_rates[cur] = val

    st.sidebar.divider()

    # Observation dates
    st.sidebar.subheader("Observation dates")
    all_obs = sorted(df["ObsDate"].dropna().unique())
    obs_labels = {d: pd.Timestamp(d).strftime("%d %b %Y") for d in all_obs}
    selected_obs = st.sidebar.multiselect(
        "Snapshots", options=all_obs,
        format_func=lambda x: obs_labels[x], default=all_obs)

    st.sidebar.divider()

    # Companies
    all_companies = sorted(df["Company"].unique())
    selected_companies = st.sidebar.multiselect("Companies", all_companies, default=all_companies)

    # Market
    all_markets = sorted(df["Market"].unique())
    selected_markets = st.sidebar.multiselect("Markets", all_markets, default=["Americas"])

    # Cruise type
    cruise_types = st.sidebar.multiselect("Cruise type", ["Classic","Expedition"],
                                           default=["Classic","Expedition"])

    # Area
    all_areas = sorted(df["Area"].unique())
    selected_areas = st.sidebar.multiselect("Areas", all_areas, default=all_areas)

    # Suite
    from utils.data_loader import SUITE_ORDER
    suite_cats = st.sidebar.multiselect("Suite category", SUITE_ORDER, default=SUITE_ORDER)

    # Arrival period
    all_years = sorted(df["ArrivalYear"].dropna().unique().astype(int))
    selected_years = st.sidebar.multiselect("Arrival year", all_years, default=all_years)
    all_months = list(range(1,13))
    selected_months = st.sidebar.multiselect("Arrival month", all_months,
                                              format_func=lambda x: MONTH_NAMES[x],
                                              default=all_months)

    st.sidebar.divider()

    # Future only filter
    last_obs_date = pd.Timestamp(sorted(df["ObsDate"].dropna().unique())[-1])
    future_only = st.sidebar.checkbox(
        f"Future voyages only (arrival after {last_obs_date.strftime('%d %b %Y')})",
        value=False)

    # Outlier toggle
    exclude_outliers = st.sidebar.checkbox("Exclude PPD outliers (>10k or =0)", value=True)

    return {
        "currency":        currency,
        "fx_rates":        fx_rates,
        "obs_dates":       selected_obs,
        "companies":       selected_companies,
        "markets":         selected_markets,
        "cruise_types":    cruise_types,
        "areas":           selected_areas,
        "suite_cats":      suite_cats,
        "years":           selected_years,
        "months":          selected_months,
        "exclude_outliers":exclude_outliers,
        "future_only":     future_only,
        "last_obs_date":   last_obs_date,
    }

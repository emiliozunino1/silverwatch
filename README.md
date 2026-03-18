# SilverWatch Dashboard

Luxury cruise competitive intelligence dashboard built with Streamlit.

## Setup

```bash
pip install -r requirements.txt
streamlit run Home.py
```

## Data refresh

Replace `SilverWatch_PowerBi_input_ALL_MARKETS.xlsx` with the new file (same name),
or use the **Control Panel → Upload** page in the dashboard itself.

## Deploying to Streamlit Cloud

1. Push this folder to a GitHub repository
2. Go to https://share.streamlit.io → New app
3. Select your repo, branch, and set **Main file path** to `Home.py`
4. Click Deploy

> ⚠️ The Excel file (12 MB) must be committed to the repo for Streamlit Cloud to access it.
> For monthly updates: replace the file in the repo and push — the dashboard auto-refreshes.

## Pages

| Page | File |
|------|------|
| Home | `Home.py` |
| 1 · Capacity Map | `pages/1_Capacity_Map.py` |
| 2 · Blockout View | `pages/2_Blockout_View.py` |
| 3 · Capacity Movement | `pages/3_Capacity_Movement.py` |
| 4 · PPD Pricing | `pages/4_PPD_Pricing.py` |
| 5 · Control Panel | `pages/5_Control_Panel.py` |

## Structure

```
silverwatch/
├── Home.py                  # Landing page
├── requirements.txt
├── SilverWatch_PowerBi_input_ALL_MARKETS.xlsx
├── .streamlit/
│   └── config.toml
├── pages/
│   ├── 1_Capacity_Map.py
│   ├── 2_Blockout_View.py
│   ├── 3_Capacity_Movement.py
│   ├── 4_PPD_Pricing.py
│   └── 5_Control_Panel.py
└── utils/
    ├── __init__.py
    ├── data_loader.py       # Data loading, caching, date parsing, FX conversion
    └── sidebar.py           # Shared sidebar filters
```

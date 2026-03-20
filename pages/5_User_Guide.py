from utils.auth import require_login, logout_button
import streamlit as st
from utils.data_loader import load_data
from utils.sidebar import render_sidebar
from utils.ui import inject_css, page_header, bordered_chart, bordered_dataframe

st.set_page_config(page_title="User Guide", layout="wide")
inject_css()
require_login()
logout_button()

DATA_PATH = "SilverWatch_PowerBi_input_ALL_MARKETS.xlsx"
df_full   = load_data(DATA_PATH)
filters   = render_sidebar(df_full)

page_header("User Guide", "How to use the SilverWatch dashboard.")

# Dynamic context
last_obs  = sorted(df_full["ObsDate"].dropna().unique())[-1]
all_obs   = sorted(df_full["ObsDate"].dropna().unique())
companies = sorted(df_full["Company"].unique())
markets   = sorted(df_full["Market"].unique())
n_voyages = df_full[df_full["Segment_Criteria"]=="MASTER"]["Voyage"].nunique()
n_rows    = len(df_full)

st.markdown(f"""
## Overview

SilverWatch is a competitive intelligence dashboard for luxury cruise capacity and pricing.
It covers **{len(companies)} companies** ({', '.join(companies)}), across **{len(markets)} markets**
({', '.join(markets)}), with data taken at **{len(all_obs)} observation snapshots**:
{', '.join([f'`{o}`' for o in all_obs])}.

The latest observation date is **`{last_obs}`**. The dataset contains **{n_rows:,} raw rows**
({df_full[df_full["Segment_Criteria"]=="MASTER"]["Voyage"].nunique():,} unique MASTER voyages).

---

## How to use the filters

### Left sidebar (global filters)
The sidebar applies to **all pages simultaneously**. Use it to narrow down:
- **Currency** — all PPD and fare values are converted in real time to the selected currency (default USD).
  You can also set custom FX rates in the expandable panel below the currency selector.
- **Observation dates** — select which of the {len(all_obs)} snapshots to include.
- **Companies, Markets, Cruise type, Areas, Suite category** — standard multi-select filters.
- **Arrival year / month** — filter voyages by when they arrive.
- **Future voyages only** — when checked, only voyages arriving after `{last_obs}` are shown.
  This is useful to focus on forward-looking capacity and pricing.
- **Exclude PPD outliers** — removes rows where Entry PPD > 10,000 or = 0 (data quality filter).

### Top-of-page filters (quick filters)
Each page has a row of filters just below the title. These are **page-specific** and let you
quickly change the most common selections for that page without scrolling to the sidebar.
The active top filters are applied **on top of** the sidebar filters.

---

## Page-by-page guide

### 1 · Capacity Map
**What it shows:** Available Berth Days (ABD) — a proxy for deployed capacity.
One ABD = one berth available for one day.

| Sub-page | What to look for |
|----------|-----------------|
| **By Area & Company** | Which areas each company is deploying to, and how their mix compares. One chart per arrival year. Use top filters to pick specific companies or months. |
| **By Ship & Area** | A heatmap matrix for each company: rows = ships (or areas), columns = arrival months. Quick way to see seasonal patterns per ship. Toggle between Ship and Area rows. |
| **ABD Heatmap** | Company × month matrix. Spot which months have the most capacity per company. Filter by area on top. |
| **World Map** | Bubble map: each bubble = one area, sized by ABD. Color by company or area. Filter by year, month and area. |

**Tips:**
- The sidebar "Future voyages only" toggle is especially useful here — uncheck it to see the full picture, check it to focus on upcoming deployments.
- ABD is summed across suite categories; COMBO voyages are excluded (MASTER only).

---

### 2 · Blockout View
**What it shows:** The full voyage schedule — departure dates, itineraries, ships and availability.

| Sub-page | What to look for |
|----------|-----------------|
| **Voyage list** | Searchable and filterable table of all voyages. Area cells are colored by the area color legend. No suite-level breakdown — one row per voyage. |
| **Ship deployment timeline** | A Gantt chart per company. Each bar is a voyage, colored by area. Compare how ships move between areas across the calendar. Legends are positioned below each chart to maximize horizontal space. |
| **Company comparison** | Select two companies and a departure date range. See a weekly summary (week ending Sunday) of voyages, ships and itineraries side by side. Use the Area filter to focus on a specific deployment zone. |

**Tips:**
- Use the departure date range in Company comparison to align both companies on the same period.
- The voyage list can be downloaded as CSV.

---

### 3 · Capacity Movement
**What it shows:** How ABD and voyage assignments changed between the {len(all_obs)} observation snapshots.

| Sub-page | What to look for |
|----------|-----------------|
| **ABD by area over time** | Two matrices: left = ABD per company × obs date; right = % change vs the previous snapshot. A red cell = capacity dropped, green = added. The bar chart below shows the delta between the last two snapshots. |
| **Ship redeployment matrix** | One table per company. Rows = voyages (ship + departure date), columns = observation dates. Each cell shows Area · Itinerary, colored by area. A color change across columns means the voyage was reassigned. |

**Tips:**
- In the redeployment matrix, scan horizontally across a row to spot changes.
  If a cell goes from "Mediterranean · Western Med" to "Caribbean · Eastern Caribbean", the voyage was re-routed.
- Use the arrival year and area top filters to narrow down to a specific deployment season.

---

### 4 · Pricing
**What it shows:** Entry PPD (Price Per Person Per Day) — the most comparable pricing metric.
**Important:** all PPD figures use only rows where `Availability_tag = Available`.
PPD is ABD-weighted so that larger voyages carry more weight in the average.

| Sub-page | What to look for |
|----------|-----------------|
| **Overview** | KPI cards per company + bar/box chart. Breakdown by suite (Vista → Veranda → Upper). |
| **By destination & month** | Two heatmaps (one per selected company) + a third showing the % price difference between them, by area and arrival month. |
| **Over time** | Line chart showing PPD evolution across all 4 snapshots, by company or area. Bar chart below shows the % change between the last two snapshots only. |
| **Cruise drill-down** | One matrix per company: rows = voyages ordered by ship + departure date, columns = observation dates. Left matrix = PPD values, right = % change vs previous snapshot. Use the top filters to narrow by year, month, cruise type and area. |

**Tips:**
- Select a single suite category in the top filter ("Veranda Suite") for the most meaningful cross-company comparison, since not all companies offer all suite tiers.
- The "Cruise type" filter separates Classic ocean voyages from Expedition (polar/adventure) — these have very different pricing structures and should not be averaged together.
- If Vista Suite shows higher PPD than Upper Suite for a company, check the area and cruise type filter — it often reflects a different deployment mix rather than a genuine pricing anomaly.

---

### 5 · User Guide *(this page)*
This guide updates automatically when new data is loaded (company names, obs dates, row counts).

---

### 6 · Control Panel
**What it shows:** Data quality and file management.

| Section | What to check |
|---------|--------------|
| **Dataset overview** | Total rows (raw: {n_rows:,}), MASTER vs COMBO split, rows per observation date. |
| **QC 1** | Missing values in key columns. Any "⚠️ Has nulls" row needs investigation. |
| **QC 2** | Rows where Availability = Available but PPD or Fare is missing — these affect pricing analysis. |
| **QC 3** | PPD outlier rows (>10,000 or =0). Bar chart shows which company has the highest outlier %. |
| **QC 4** | Voyage date parsing check — should show 0 unparseable rows. |
| **File upload** | Drop the new monthly Excel here to refresh everything. Same column structure required. |

**Monthly refresh procedure:**
1. Receive the new Excel file.
2. Go to Control Panel → upload the file.
3. All pages refresh automatically with the new data.
4. Check QC 1–4 to confirm data integrity before sharing with colleagues.
""")

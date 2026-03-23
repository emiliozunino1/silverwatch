import streamlit as st
import pandas as pd
import numpy as np
import os

# Compact layout CSS
LAYOUT_CSS = """
<style>
/* Reduce top padding */
.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
/* Tighter tab bar */
button[data-baseweb="tab"] {
    padding: 4px 14px !important;
    font-size: 0.85rem !important;
}
/* Smaller filter labels */
label[data-testid="stWidgetLabel"] p {
    font-size: 0.78rem !important;
    margin-bottom: 0 !important;
}
/* Compact selectbox / multiselect */
div[data-baseweb="select"] {
    font-size: 0.80rem !important;
}
/* Reduce gap between columns */
div[data-testid="stHorizontalBlock"] {
    gap: 6px !important;
    align-items: flex-end !important;
}
/* Smaller page title */
[data-testid="stAppViewContainer"] h1 {
    font-size: 1.3rem !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
    display: inline-block;
}
/* Sidebar tighter */
section[data-testid="stSidebar"] .block-container {
    padding-top: 0.3rem !important;
}
/* Reduce divider margin */
hr { margin: 0.3rem 0 !important; }
</style>
"""

def inject_css():
    st.markdown(LAYOUT_CSS, unsafe_allow_html=True)


def page_header(title: str, description: str):
    """Logo + SILVERWATCH name + title + caption."""
    inject_css()
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        c1, c2, c3 = st.columns([1, 2, 9])
        with c1:
            st.image(logo_path, width=55)
        with c2:
            st.markdown(
                "<p style='font-size:0.85rem;font-weight:700;letter-spacing:0.1em;"
                "color:#1a1a2e;margin:0;padding-top:14px;'>SILVERWATCH</p>",
                unsafe_allow_html=True)
        with c3:
            st.markdown(
                f"<h1 style='font-size:1.2rem;font-weight:600;margin:0;padding-top:10px;'>"
                f"{title}</h1>",
                unsafe_allow_html=True)
    else:
        st.title(title)
    st.caption(description)
    st.divider()


def bordered_chart(fig, **kwargs):
    st.markdown('<div style="border:1px solid #d0d0d0;border-radius:6px;padding:2px">',
                unsafe_allow_html=True)
    st.plotly_chart(fig, **kwargs)
    st.markdown('</div>', unsafe_allow_html=True)


def bordered_dataframe(df_or_styler, **kwargs):
    st.markdown('<div style="border:1px solid #d0d0d0;border-radius:6px;overflow:hidden">',
                unsafe_allow_html=True)
    st.dataframe(df_or_styler, **kwargs)
    st.markdown('</div>', unsafe_allow_html=True)


def filter_row(*specs):
    """
    Render a compact horizontal filter row.
    specs: list of dicts with keys:
      type: 'multiselect' | 'selectbox'
      label, options, default, key
      format_func (optional)
      width (optional, int 1-12 for relative column width)
    Returns dict of {key: value}
    """
    widths = [s.get("width", 1) for s in specs]
    cols   = st.columns(widths)
    results = {}
    for col, spec in zip(cols, specs):
        with col:
            kwargs = dict(label=spec["label"], options=spec["options"],
                         key=spec["key"])
            if "format_func" in spec:
                kwargs["format_func"] = spec["format_func"]
            if spec["type"] == "multiselect":
                kwargs["default"] = spec.get("default", spec["options"])
                results[spec["key"]] = st.multiselect(**kwargs)
            else:
                idx = 0
                if "default" in spec and spec["default"] in spec["options"]:
                    idx = spec["options"].index(spec["default"])
                kwargs["index"] = idx
                results[spec["key"]] = st.selectbox(**kwargs)
    return results


# ── Matplotlib-free heatmap helpers ──────────────────────────────────────────
def style_numeric_heatmap(df: pd.DataFrame,
                           low_hex="#dce9f5", high_hex="#08306b",
                           fmt="{:,.0f}", na_rep="—"):
    vals = df.values.astype(float)
    fin  = vals[np.isfinite(vals)]
    vmin = float(fin.min()) if len(fin) else 0
    vmax = float(fin.max()) if len(fin) else 1
    def _hex(h): return int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    r0,g0,b0 = _hex(low_hex); r1,g1,b1 = _hex(high_hex)
    def cell(val):
        try: v = float(val)
        except: return "text-align:center"
        if not np.isfinite(v): return "text-align:center"
        t = max(0.0, min(1.0, (v-vmin)/(vmax-vmin) if vmax>vmin else 0.5))
        r=int(r0+t*(r1-r0)); g=int(g0+t*(g1-g0)); b=int(b0+t*(b1-b0))
        fg = "#ffffff" if 0.299*r+0.587*g+0.114*b < 140 else "#111111"
        return f"background-color:#{r:02x}{g:02x}{b:02x}; color:{fg}; text-align:center"
    return (df.style.applymap(cell).format(fmt, na_rep=na_rep)
              .set_properties(**{"text-align":"center"})
              .set_table_styles([
                  {"selector":"th","props":[("text-align","center")]},
                  {"selector":"th.row_heading","props":[("text-align","left")]}]))


def style_pct_heatmap(df: pd.DataFrame, fmt="{:+.1f}%", na_rep="—"):
    def cell(val):
        try: v = float(val)
        except: return "text-align:center"
        if not np.isfinite(v): return "text-align:center"
        if v > 0:
            t = min(1.0, v/20); r=int(255-t*155); g=255; b=int(255-t*155)
        elif v < 0:
            t = min(1.0, abs(v)/20); r=255; g=int(255-t*155); b=int(255-t*155)
        else:
            r=g=b=255
        fg = "#111111" if 0.299*r+0.587*g+0.114*b > 140 else "#ffffff"
        return f"background-color:#{r:02x}{g:02x}{b:02x}; color:{fg}; font-weight:500; text-align:center"
    return (df.style.applymap(cell).format(fmt, na_rep=na_rep)
              .set_properties(**{"text-align":"center"})
              .set_table_styles([
                  {"selector":"th","props":[("text-align","center")]},
                  {"selector":"th.row_heading","props":[("text-align","left")]}]))

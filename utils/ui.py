import streamlit as st
import pandas as pd
import numpy as np
import os
import base64

def _img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

LAYOUT_CSS = """
<style>
/* Remove default top padding */
.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
/* Tighter widgets */
div[data-testid="stHorizontalBlock"] { gap: 6px !important; align-items: flex-end !important; }
label[data-testid="stWidgetLabel"] p { font-size: 0.78rem !important; margin-bottom: 1px !important; }
div[data-baseweb="select"] { font-size: 0.80rem !important; }
button[data-baseweb="tab"] { padding: 4px 14px !important; font-size: 0.84rem !important; }
section[data-testid="stSidebar"] .block-container { padding-top: 0.3rem !important; }
hr { margin: 0.3rem 0 !important; }
/* Page title size */
[data-testid="stAppViewContainer"] h1 {
    font-size: 1.25rem !important;
    margin: 0.1rem 0 0 0 !important;
    padding: 0 !important;
}
</style>
"""

def _fixed_header_html(maiora_logo_path: str, title: str, description: str) -> str:
    """Build the fixed top bar: Maiora logo + SILVERWATCH text, flush with Streamlit toolbar."""
    logo_html = ""
    if os.path.exists(maiora_logo_path):
        b64 = _img_to_b64(maiora_logo_path)
        ext = maiora_logo_path.split(".")[-1].lower()
        mime = "image/png" if ext == "png" else "image/jpeg"
        logo_html = f'<img src="data:{mime};base64,{b64}" style="height:28px;vertical-align:middle;margin-right:8px;">'

    return f"""
<div style="
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 48px;
    background: white;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    align-items: center;
    padding: 0 1rem;
    z-index: 999990;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
">
    {logo_html}
    <span style="font-size:1.0rem;font-weight:700;letter-spacing:0.1em;color:#1a1a2e;">
        SILVERWATCH
    </span>
</div>
"""

def inject_css():
    st.markdown(LAYOUT_CSS, unsafe_allow_html=True)


def page_header(title: str, description: str):
    inject_css()
    maiora = "logo_maiora.png"
    st.markdown(_fixed_header_html(maiora, title, description), unsafe_allow_html=True)
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
            t=min(1.0,v/20); r=int(255-t*155); g=255; b=int(255-t*155)
        elif v < 0:
            t=min(1.0,abs(v)/20); r=255; g=int(255-t*155); b=int(255-t*155)
        else:
            r=g=b=255
        fg="#111111" if 0.299*r+0.587*g+0.114*b>140 else "#ffffff"
        return f"background-color:#{r:02x}{g:02x}{b:02x}; color:{fg}; font-weight:500; text-align:center"
    return (df.style.applymap(cell).format(fmt, na_rep=na_rep)
              .set_properties(**{"text-align":"center"})
              .set_table_styles([
                  {"selector":"th","props":[("text-align","center")]},
                  {"selector":"th.row_heading","props":[("text-align","left")]}]))

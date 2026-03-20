import streamlit as st
import pandas as pd
import numpy as np
import os

# Minimal CSS: reduce top padding only
HEADER_CSS = """
<style>
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
[data-testid="stAppViewContainer"] h1 { font-size: 1.4rem !important; margin-bottom: 0.1rem !important; }
</style>
"""

def inject_css():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)

def page_header(title: str, description: str):
    inject_css()
    # Logo + SILVERWATCH name inline
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        col_logo, col_name, col_rest = st.columns([1, 3, 8])
        with col_logo:
            st.image(logo_path, width=80)
        with col_name:
            st.markdown("<div style='display:flex;align-items:center;height:100%;'>"
                        "<span style='font-size:1.1rem;font-weight:600;letter-spacing:0.08em;"
                        "color:#1a1a2e;padding-top:18px;'>SILVERWATCH</span></div>",
                        unsafe_allow_html=True)
    st.title(title)
    st.caption(description)
    st.divider()


def bordered_chart(fig, **kwargs):
    """Wrap a plotly chart with a visible border."""
    st.markdown('<div style="border:1px solid #d0d0d0;border-radius:6px;padding:4px;">',
                unsafe_allow_html=True)
    st.plotly_chart(fig, **kwargs)
    st.markdown('</div>', unsafe_allow_html=True)


def bordered_dataframe(df_or_styler, **kwargs):
    """Wrap a dataframe with a visible border."""
    st.markdown('<div style="border:1px solid #d0d0d0;border-radius:6px;overflow:hidden;">',
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
    return (df.style
              .applymap(cell)
              .format(fmt, na_rep=na_rep)
              .set_properties(**{"text-align":"center"})
              .set_table_styles([{"selector":"th","props":[("text-align","center")]}]))


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
    return (df.style
              .applymap(cell)
              .format(fmt, na_rep=na_rep)
              .set_properties(**{"text-align":"center"})
              .set_table_styles([{"selector":"th","props":[("text-align","center")]}]))

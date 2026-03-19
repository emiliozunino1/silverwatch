import streamlit as st
import pandas as pd
import numpy as np


def inject_css():
    pass  # CSS removed — using Streamlit defaults


def page_header(title: str, description: str):
    st.title(title)
    st.caption(description)
    st.divider()


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
        except: return ""
        if not np.isfinite(v): return ""
        t = max(0.0, min(1.0, (v-vmin)/(vmax-vmin) if vmax>vmin else 0.5))
        r=int(r0+t*(r1-r0)); g=int(g0+t*(g1-g0)); b=int(b0+t*(b1-b0))
        fg = "#ffffff" if 0.299*r+0.587*g+0.114*b < 140 else "#111111"
        return f"background-color:#{r:02x}{g:02x}{b:02x}; color:{fg}"
    return df.style.applymap(cell).format(fmt, na_rep=na_rep)


def style_pct_heatmap(df: pd.DataFrame, fmt="{:+.1f}%", na_rep="—"):
    def cell(val):
        try: v = float(val)
        except: return ""
        if not np.isfinite(v): return ""
        if v > 0:
            t = min(1.0, v/20); r=int(255-t*155); g=255; b=int(255-t*155)
        elif v < 0:
            t = min(1.0, abs(v)/20); r=255; g=int(255-t*155); b=int(255-t*155)
        else:
            r=g=b=255
        fg = "#111111" if 0.299*r+0.587*g+0.114*b > 140 else "#ffffff"
        return f"background-color:#{r:02x}{g:02x}{b:02x}; color:{fg}; font-weight:500"
    return df.style.applymap(cell).format(fmt, na_rep=na_rep)

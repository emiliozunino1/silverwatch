import streamlit as st
import pandas as pd
import numpy as np
import os
import base64


def _img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _build_css(maiora_b64: str) -> str:
    header_left = "120px" if maiora_b64 else "16px"

    header_after_css = ""
    if maiora_b64:
        header_after_css = f"""
        [data-testid="stHeader"]::after {{
            content: "";
            position: absolute;
            left: 8px;
            top: 50%;
            transform: translateY(-50%);
            width: 96px;
            height: 28px;
            background-image: url("data:image/png;base64,{maiora_b64}");
            background-size: contain;
            background-repeat: no-repeat;
            background-position: left center;
            z-index: 999;
            pointer-events: none;
        }}
        """

    return f"""
    <style>
    /* Main page padding */
    .block-container {{
        padding-top: 2.8rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}

    /* Header */
    [data-testid="stHeader"] {{
        background: white !important;
        border-bottom: 1px solid #e8e8e8 !important;
        position: relative !important;
    }}

    [data-testid="stHeader"]::before {{
        content: "SILVERWATCH";
        position: absolute;
        left: {header_left};
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        color: #1a1a2e;
        z-index: 999;
        pointer-events: none;
        white-space: nowrap;
    }}

    {header_after_css}

    /* When sidebar is narrow/collapsed, hide header branding to avoid overlap */
    @media (max-width: 1200px) {{
        [data-testid="stHeader"]::before,
        [data-testid="stHeader"]::after {{
            content: none !important;
            display: none !important;
        }}
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] .block-container {{
        padding-top: 0.4rem !important;
    }}

    /* Sidebar logo wrapper created by st.image */
    .sidebar-logo-wrap {{
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin: 0.2rem 0 0.7rem 0;
    }}

    /* Hard cap on sidebar logo size */
    .sidebar-logo-wrap img {{
        width: 180px !important;
        max-width: 180px !important;
        min-width: 180px !important;
        height: auto !important;
        display: block !important;
        object-fit: contain !important;
    }}

    /* Also protect against generic sidebar image scaling */
    section[data-testid="stSidebar"] img {{
        max-width: 180px !important;
        height: auto !important;
    }}

    /* Compact widgets */
    div[data-testid="stHorizontalBlock"] {{
        gap: 6px !important;
        align-items: flex-end !important;
    }}

    label[data-testid="stWidgetLabel"] p {{
        font-size: 0.78rem !important;
        margin-bottom: 1px !important;
    }}

    div[data-baseweb="select"] {{
        font-size: 0.80rem !important;
    }}

    button[data-baseweb="tab"] {{
        padding: 4px 14px !important;
        font-size: 0.84rem !important;
    }}

    hr {{
        margin: 0.3rem 0 !important;
    }}

    [data-testid="stAppViewContainer"] h1 {{
        font-size: 1.2rem !important;
        margin: 0.2rem 0 0 0 !important;
        padding: 0 !important;
    }}
    </style>
    """


def inject_css():
    maiora_b64 = ""
    if os.path.exists("logo_maiora.png"):
        maiora_b64 = _img_to_b64("logo_maiora.png")
    st.markdown(_build_css(maiora_b64), unsafe_allow_html=True)


def render_sidebar_logo():
    logo_path = "logo_silversea.png"   # change if your sidebar logo file has a different name
    if os.path.exists(logo_path):
        with st.sidebar:
            st.markdown('<div class="sidebar-logo-wrap">', unsafe_allow_html=True)
            st.image(logo_path, width=180)
            st.markdown('</div>', unsafe_allow_html=True)


def page_header(title: str, description: str):
    inject_css()
    render_sidebar_logo()
    st.title(title)
    st.caption(description)
    st.divider()


def bordered_chart(fig, **kwargs):
    st.markdown(
        '<div style="border:1px solid #d0d0d0;border-radius:6px;padding:2px">',
        unsafe_allow_html=True
    )
    st.plotly_chart(fig, **kwargs)
    st.markdown("</div>", unsafe_allow_html=True)


def bordered_dataframe(df_or_styler, **kwargs):
    st.markdown(
        '<div style="border:1px solid #d0d0d0;border-radius:6px;overflow:hidden">',
        unsafe_allow_html=True
    )
    st.dataframe(df_or_styler, **kwargs)
    st.markdown("</div>", unsafe_allow_html=True)


def style_numeric_heatmap(
    df: pd.DataFrame,
    low_hex: str = "#dce9f5",
    high_hex: str = "#08306b",
    fmt: str = "{:,.0f}",
    na_rep: str = "—"
):
    vals = df.values.astype(float)
    fin = vals[np.isfinite(vals)]
    vmin = float(fin.min()) if len(fin) else 0
    vmax = float(fin.max()) if len(fin) else 1

    def _hex(h):
        return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)

    r0, g0, b0 = _hex(low_hex)
    r1, g1, b1 = _hex(high_hex)

    def cell(val):
        try:
            v = float(val)
        except Exception:
            return "text-align:center"

        if not np.isfinite(v):
            return "text-align:center"

        t = max(0.0, min(1.0, (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5))
        r = int(r0 + t * (r1 - r0))
        g = int(g0 + t * (g1 - g0))
        b = int(b0 + t * (b1 - b0))
        fg = "#ffffff" if 0.299 * r + 0.587 * g + 0.114 * b < 140 else "#111111"

        return f"background-color:#{r:02x}{g:02x}{b:02x}; color:{fg}; text-align:center"

    return (
        df.style
        .applymap(cell)
        .format(fmt, na_rep=na_rep)
        .set_properties(**{"text-align": "center"})
        .set_table_styles([
            {"selector": "th", "props": [("text-align", "center")]},
            {"selector": "th.row_heading", "props": [("text-align", "left")]}
        ])
    )


def style_pct_heatmap(df: pd.DataFrame, fmt: str = "{:+.1f}%", na_rep: str = "—"):
    def cell(val):
        try:
            v = float(val)
        except Exception:
            return "text-align:center"

        if not np.isfinite(v):
            return "text-align:center"

        if v > 0:
            t = min(1.0, v / 20)
            r = int(255 - t * 155)
            g = 255
            b = int(255 - t * 155)
        elif v < 0:
            t = min(1.0, abs(v) / 20)
            r = 255
            g = int(255 - t * 155)
            b = int(255 - t * 155)
        else:
            r = g = b = 255

        fg = "#111111" if 0.299 * r + 0.587 * g + 0.114 * b > 140 else "#ffffff"

        return (
            f"background-color:#{r:02x}{g:02x}{b:02x}; "
            f"color:{fg}; font-weight:500; text-align:center"
        )

    return (
        df.style
        .applymap(cell)
        .format(fmt, na_rep=na_rep)
        .set_properties(**{"text-align": "center"})
        .set_table_styles([
            {"selector": "th", "props": [("text-align", "center")]},
            {"selector": "th.row_heading", "props": [("text-align", "left")]}
        ])
    )
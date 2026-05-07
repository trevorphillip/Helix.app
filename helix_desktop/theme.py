from __future__ import annotations

import streamlit as st


def inject_helix_theme() -> None:
    st.markdown("""
<style>
/* App background */
.stApp { background: #0f1117 !important; }

/* Sidebar */
[data-testid="stSidebar"] { background: #111318 !important; border-right: 0.5px solid #1e2130 !important; }
[data-testid="stSidebar"] label { color: #888780 !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: 0.8px !important; }
[data-testid="stSidebar"] .stSelectbox select { background: #1a1f2e !important; color: #e8e6df !important; border: 0.5px solid #2a2e3e !important; }

/* Main content */
.block-container { background: #0f1117 !important; padding-top: 1rem !important; }

/* Tabs */
[data-baseweb="tab-list"] { background: #151821 !important; border-bottom: 0.5px solid #1e2130 !important; }
[data-baseweb="tab"] { color: #5F5E5A !important; }
[aria-selected="true"][data-baseweb="tab"] { color: #EF9F27 !important; border-bottom: 2px solid #EF9F27 !important; }

/* Metrics */
[data-testid="stMetric"] { background: #151821 !important; border: 0.5px solid #1e2130 !important; border-radius: 8px !important; padding: 10px 14px !important; }
[data-testid="stMetricValue"] { color: #1D9E75 !important; }
[data-testid="stMetricLabel"] { color: #5F5E5A !important; }

/* Buttons */
.stButton button { background: #1a1f2e !important; color: #e8e6df !important; border: 0.5px solid #2a2e3e !important; border-radius: 8px !important; }
.stButton button:hover { border-color: #1D9E75 !important; color: #1D9E75 !important; }

/* Inputs */
.stTextInput input, .stTextArea textarea { background: #151821 !important; color: #e8e6df !important; border: 0.5px solid #2a2e3e !important; border-radius: 6px !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: #1D9E75 !important; }

/* Expander */
[data-testid="stExpander"] { background: #151821 !important; border: 0.5px solid #1e2130 !important; border-radius: 8px !important; }

/* Dataframes */
[data-testid="stDataFrame"] { background: #151821 !important; }

/* Radio buttons */
.stRadio label { color: #888780 !important; }

/* Selectbox */
[data-baseweb="select"] { background: #1a1f2e !important; }

/* Slider */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] { background: #1D9E75 !important; }

/* Text */
p, li, span { color: #e8e6df !important; }
h1, h2, h3 { color: #e8e6df !important; }
.stCaption { color: #5F5E5A !important; }
</style>
""", unsafe_allow_html=True)

import streamlit as st
from mobile_app.viewmodel import (
    analyze_sequence, format_summary, format_guides,
    get_available_enzymes
)

st.set_page_config(page_title="Helix – CRISPR Sandbox (Safe Mode)", layout="wide")
st.title("CRISPR Sandbox — Safe Mode")

seq = st.text_area("DNA sequence (ACGT…)", height=180)
enzymes = get_available_enzymes()
enzyme = st.selectbox("Enzyme", enzymes)
scan_rev = st.checkbox("Scan reverse strand", True)

if st.button("Analyze"):
    try:
        res = analyze_sequence(seq, enzyme, scan_reverse=scan_rev)
        st.code(format_summary(res))
        st.subheader("Top guides")
        st.code(format_guides(res.guides, limit=10))
    except Exception as e:
        st.error(str(e))

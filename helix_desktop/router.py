# helix_desktop/router.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # add project root to PYTHONPATH
import streamlit as st
from helix_platform.plugins import bootstrap, list_plugins

def run():
    bootstrap()
    st.set_page_config(page_title="Helix Suite", layout="wide")
    plugins = list_plugins()
    # show the two modes using plugin titles
    choice = st.sidebar.selectbox("Choose mode", ["crispr", "medprep"],
                                  format_func=lambda s: plugins[s].title)
    vm = plugins[choice].get_viewmodel()

    if choice == "crispr":
        # hand off to CRISPR Sandbox miniature (safe mode)
        st.title("CRISPR Sandbox")
        seq = st.text_area("DNA", height=160)
        enzyme = st.selectbox("Enzyme", vm["get_available_enzymes"]())
        if st.button("Analyze"):
            res = vm["analyze_sequence"](seq, enzyme, scan_reverse=True)
            st.code(vm["format_summary"](res))
            st.subheader("Top guides"); st.code(vm["format_guides"](res.guides, 8))
    else:
        st.title("Med-Prep (Biology & Chemistry)")
        tracks = vm["list_tracks"]()
        col1, col2 = st.columns(2)
        with col1:
            track = st.selectbox("Track", list(tracks.keys()))
        with col2:
            module = st.selectbox("Module", tracks[track])
        user = st.text_input("User", "student")
        if st.button("Start Practice"):
            cards = vm["next_due_cards"](user, track, module, limit=1)
            if not cards:
                st.success("No cards due. Come back later!")
            else:
                card = cards[0]; lesson = card["lesson"]
                st.subheader(lesson["prompt"])
                if lesson["type"] == "mcq":
                    pick = st.radio("Choose", lesson["choices"])
                    if st.button("Submit"):
                        correct = lesson["choices"].index(pick) == lesson["answer"]
                        vm["grade_card"](user, card["card_id"], correct)
                        st.write("✅ Correct" if correct else "❌ Incorrect")
                        st.caption(lesson.get("explain",""))

if __name__ == "__main__":
    run()


import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.components.landing import show_landing
from frontend.components.auth import show_auth
from frontend.components.dashboard import show_dashboard
from frontend.components.trip_setup import show_trip_setup
from frontend.components.itinerary import show_itinerary

st.set_page_config(
    page_title="TripTailor — AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="auto"
)

st.markdown("""
<style>
    .stButton > button[kind="primary"] {
        background-color: #1D9E75;
        border-color: #1D9E75;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #0F6E56;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    defaults = {
        "username": None,
        "country": None,
        "currency_code": "INR",
        "currency_symbol": "₹",
        "travel_personality": "Explorer",
        "category_weights": {},
        "page": "home",
        "itinerary": None,
        "city": None,
        "days": 3,
        "budget_usd": 50,
        "budget_local": 2000,
        "hotels": [],
        "restaurants": [],
        "total_cost_local": 0,
        "feedback_given": {},
        "replan_triggered": False,
        "setup_step": 1,
        "parsed_trip": {},
        "chat_history": [],
        "view_mode": "timeline",
        "show_chat": False,
        "collab_recs": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def show_navbar():
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    with col1:
        st.markdown("### ✈️ TripTailor")
    with col2:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    with col3:
        if st.button("✨ New Trip", use_container_width=True):
            st.session_state.page = "trip_setup"
            st.rerun()
    with col4:
        st.markdown(
            f"<div style='padding:8px; text-align:center; font-size:13px'>"
            f"👤 {st.session_state.username}</div>",
            unsafe_allow_html=True
        )
    with col5:
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    st.divider()

def main():
    init_session_state()

    if st.session_state.username is None:
        show_landing()
        show_auth()
        return

    show_navbar()

    page = st.session_state.page

    if page == "dashboard":
        show_dashboard()
    elif page == "trip_setup":
        show_trip_setup()
    elif page == "itinerary":
        show_itinerary()
    else:
        show_dashboard()

main()
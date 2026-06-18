import streamlit as st
from frontend.api import get_dashboard, delete_trip
import random

TRAVEL_QUOTES = [
    ("The world is a book, and those who do not travel read only one page.", "Saint Augustine"),
    ("Travel is the only thing you buy that makes you richer.", "Anonymous"),
    ("Life is short and the world is wide.", "Simon Raven"),
    ("Adventure is worthwhile in itself.", "Amelia Earhart"),
    ("Travel makes one modest. You see what a tiny place you occupy in the world.", "Gustave Flaubert"),
    ("The journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("Travel far enough, you meet yourself.", "David Mitchell"),
    ("To travel is to live.", "Hans Christian Andersen"),
    ("Not all those who wander are lost.", "J.R.R. Tolkien"),
    ("Travel is fatal to prejudice, bigotry, and narrow-mindedness.", "Mark Twain"),
    ("The real voyage of discovery consists not in seeking new landscapes, but in having new eyes.", "Marcel Proust"),
    ("A good traveler has no fixed plans and is not intent on arriving.", "Lao Tzu"),
    ("Once a year, go someplace you have never been before.", "Dalai Lama"),
    ("We travel not to escape life, but for life not to escape us.", "Anonymous"),
    ("The world is too big to stay in one place.", "Anonymous"),
    ("Wherever you go becomes a part of you somehow.", "Anita Desai"),
    ("Travel opens your heart, broadens your mind, and fills your life with stories to tell.", "Paula Bendfeldt"),
    ("Jobs fill your pocket, adventures fill your soul.", "Jaime Lyn"),
    ("Travel is not a reward for working, it is education for living.", "Anonymous"),
    ("To travel is to discover that everyone is wrong about other countries.", "Aldous Huxley")
]

def load_trip_to_session(trip):
    st.session_state.itinerary = trip.get("itinerary_data")
    st.session_state.city = trip["city"]
    st.session_state.days = trip["days"]
    st.session_state.budget_usd = trip.get("budget_per_day_usd", 50)
    st.session_state.budget_local = trip.get("budget_per_day_local", 0)
    st.session_state.current_trip_id = trip["id"]
    st.session_state.current_trip_notes = trip.get("notes", "")

    hotel_data = trip.get("hotel_data") or {}
    restaurant_data = trip.get("restaurant_data") or {}

    if isinstance(hotel_data, dict):
        st.session_state.hotels = hotel_data.get("hotels", [])
    elif isinstance(hotel_data, list):
        st.session_state.hotels = hotel_data
    else:
        st.session_state.hotels = []

    if isinstance(restaurant_data, dict):
        st.session_state.restaurants = restaurant_data.get("restaurants", [])
    elif isinstance(restaurant_data, list):
        st.session_state.restaurants = restaurant_data
    else:
        st.session_state.restaurants = []

    st.session_state.feedback_given = {}
    st.session_state.selected_hotel = None
    st.session_state.is_saved_trip = True
    st.session_state.page = "itinerary"

def show_dashboard():
    with st.spinner("Loading your dashboard..."):
        data = get_dashboard(st.session_state.username)

    if "detail" in data:
        st.error("Could not load dashboard")
        return

    currency_symbol = data.get("currency_symbol", "₹")

    if "dashboard_quote" not in st.session_state:
        st.session_state.dashboard_quote = random.choice(TRAVEL_QUOTES)

    quote, author = st.session_state.dashboard_quote

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.markdown(
            f"<div style='text-align:center; padding:24px 32px; "
            f"border-radius:16px; border:1px solid #e0e0e0; "
            f"margin-bottom:8px'>"
            f"<div style='font-size:22px; font-style:italic; "
            f"font-family:Georgia,serif; margin-bottom:12px'>"
            f"\"{quote}\"</div>"
            f"<div style='font-size:14px; opacity:0.6'>— {author}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.metric("🌍 Home Country", data.get("country", ""))

    st.divider()

    active_trip = data.get("active_trip")
    past_trips = data.get("past_trips", [])

    st.markdown("### 🗺️ Current Active Trip")

    if active_trip:
        confirm_key = "confirm_delete_active"
        if st.session_state.get(confirm_key):
            st.error(
                f"Are you sure you want to delete "
                f"**{active_trip.get('trip_name', active_trip['city'])}**? "
                f"This cannot be undone."
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Yes, delete it",
                    type="primary",
                    key="confirm_del_active",
                    use_container_width=True
                ):
                    result = delete_trip(
                        active_trip["id"], st.session_state.username
                    )
                    if result.get("message") == "Trip deleted":
                        st.session_state[confirm_key] = False
                        st.rerun()
                    else:
                        st.error("Could not delete trip")
            with col2:
                if st.button(
                    "Cancel",
                    key="cancel_del_active",
                    use_container_width=True
                ):
                    st.session_state[confirm_key] = False
                    st.rerun()
        else:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                trip_name = (
                    active_trip.get("trip_name") or active_trip["city"]
                )
                st.markdown(f"**{trip_name}**")
                st.caption(
                    f"📍 {active_trip['city']} | "
                    f"📅 {active_trip['days']} days"
                )
            with col2:
                if st.button(
                    "See Itinerary →",
                    type="primary",
                    use_container_width=True,
                    key="active_see_itinerary"
                ):
                    load_trip_to_session(active_trip)
                    st.rerun()
            with col3:
                if st.button(
                    "🗑️ Delete",
                    key="delete_active",
                    use_container_width=True
                ):
                    st.session_state[confirm_key] = True
                    st.rerun()
    else:
        st.info("No active trip at the moment.")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(
                "✨ Plan New Trip",
                type="primary",
                use_container_width=True,
                key="plan_new_btn"
            ):
                st.session_state.page = "trip_setup"
                st.rerun()

    if past_trips:
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 📚 Past Trips")
        with col2:
            if "show_all_trips" not in st.session_state:
                st.session_state.show_all_trips = False
            btn_label = (
                "Hide trips" if st.session_state.show_all_trips
                else f"Show all ({len(past_trips)})"
            )
            if st.button(
                btn_label,
                use_container_width=True,
                key="toggle_trips"
            ):
                st.session_state.show_all_trips = (
                    not st.session_state.show_all_trips
                )
                st.rerun()

        if st.session_state.show_all_trips:
            for trip in past_trips:
                trip_name = trip.get("trip_name") or trip["city"]
                budget = trip.get("budget_per_day_local", 0)
                confirm_key = f"confirm_delete_{trip['id']}"

                if st.session_state.get(confirm_key):
                    st.error(
                        f"Are you sure you want to delete "
                        f"**{trip_name}**? This cannot be undone."
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "Yes, delete it",
                            type="primary",
                            key=f"confirm_yes_{trip['id']}",
                            use_container_width=True
                        ):
                            result = delete_trip(
                                trip["id"], st.session_state.username
                            )
                            if result.get("message") == "Trip deleted":
                                st.session_state[confirm_key] = False
                                st.rerun()
                            else:
                                st.error("Could not delete trip")
                    with col2:
                        if st.button(
                            "Cancel",
                            key=f"cancel_del_{trip['id']}",
                            use_container_width=True
                        ):
                            st.session_state[confirm_key] = False
                            st.rerun()
                else:
                    with st.expander(
                        f"🗺️ {trip_name} — {trip['days']} days | "
                        f"{currency_symbol}{budget:.0f}/day | "
                        f"📆 {str(trip['created_at'])[:10]}"
                    ):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.write(f"**City:** {trip['city']}")
                            st.write(f"**Days:** {trip['days']}")
                        with col2:
                            st.write(
                                f"**Date:** "
                                f"{str(trip['created_at'])[:10]}"
                            )
                        with col3:
                            if st.button(
                                "View →",
                                key=f"view_{trip['id']}",
                                use_container_width=True,
                                type="primary"
                            ):
                                load_trip_to_session(trip)
                                st.rerun()
                            if st.button(
                                "🗑️",
                                key=f"delete_{trip['id']}",
                                use_container_width=True
                            ):
                                st.session_state[confirm_key] = True
                                st.rerun()
    else:
        st.divider()
        st.markdown("### 📚 Past Trips")
        st.info("No past trips yet. Your saved trips will appear here.")
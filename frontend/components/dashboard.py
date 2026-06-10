import streamlit as st
from frontend.api import get_dashboard
from frontend.config import PERSONALITY_ICONS

def show_dashboard():
    with st.spinner("Loading your dashboard..."):
        data = get_dashboard(st.session_state.username)

    if "detail" in data:
        st.error("Could not load dashboard")
        return

    personality = data.get("travel_personality", "Explorer")
    icon = PERSONALITY_ICONS.get(personality, "🧭")
    currency_symbol = data.get("currency_symbol", "₹")

    st.title(f"Welcome back, {st.session_state.username}! 👋")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Travel Personality", f"{icon} {personality}")
    with col2:
        st.metric("Total Trips", data.get("total_trips", 0))
    with col3:
        st.metric("Home Country", data.get("country", ""))

    st.divider()

    weights = data.get("category_weights", {})
    if weights:
        st.markdown("### 🧠 Your taste profile")
        cols = st.columns(len(weights))
        for col, (category, weight) in zip(cols, weights.items()):
            with col:
                if weight > 1.0:
                    st.success(f"**{category}**\n\n{weight}")
                elif weight < 0.5:
                    st.error(f"**{category}**\n\n{weight}")
                else:
                    st.info(f"**{category}**\n\n{weight}")

    st.divider()

    active_trip = data.get("active_trip")
    if active_trip:
        st.markdown("### 🗺️ Current Active Trip")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Destination", active_trip["city"])
        with col2:
            st.metric("Duration", f"{active_trip['days']} days")
        with col3:
            budget = active_trip.get("budget_per_day_local", 0)
            st.metric("Budget/day", f"{currency_symbol}{budget}")
        with col4:
            st.metric("Stay", active_trip.get("hotel_type", "Hotel"))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Continue Planning",
                        type="primary", use_container_width=True):
                st.session_state.current_trip = active_trip
                st.session_state.itinerary = active_trip.get("itinerary_data")
                st.session_state.city = active_trip["city"]
                st.session_state.days = active_trip["days"]
                st.session_state.budget_usd = active_trip.get("budget_per_day_usd", 50)
                st.session_state.page = "itinerary"
                st.rerun()
        with col2:
            if st.button("✨ Plan New Trip", use_container_width=True):
                st.session_state.page = "trip_setup"
                st.rerun()
    else:
        st.info("No active trip yet. Plan your first adventure!")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✨ Plan Your First Trip",
                        type="primary", use_container_width=True):
                st.session_state.page = "trip_setup"
                st.rerun()

    past_trips = data.get("past_trips", [])
    if past_trips:
        st.divider()
        st.markdown("### 📚 Past Trips")
        for trip in past_trips:
            budget = trip.get("budget_per_day_local", 0)
            trip_name = trip.get("trip_name", trip["city"])
            with st.expander(
                f"🗺️ {trip_name} — {trip['days']} days | "
                f"{currency_symbol}{budget}/day"
            ):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**City:** {trip['city']}")
                    st.write(f"**Days:** {trip['days']}")
                with col2:
                    st.write(f"**Stay:** {trip.get('hotel_type', 'Hotel')}")
                    st.write(f"**Food:** {trip.get('food_type', 'Any')}")
                with col3:
                    st.write(f"**Date:** {str(trip['created_at'])[:10]}")

                if trip.get("itinerary_data"):
                    if st.button("View Full Itinerary",
                                key=f"view_{trip['id']}"):
                        st.session_state.itinerary = trip["itinerary_data"]
                        st.session_state.city = trip["city"]
                        st.session_state.days = trip["days"]
                        st.session_state.budget_usd = trip.get(
                            "budget_per_day_usd", 50)
                        st.session_state.hotels = trip.get("hotel_data", {})
                        st.session_state.restaurants = trip.get(
                            "restaurant_data", {})
                        st.session_state.page = "itinerary"
                        st.rerun()
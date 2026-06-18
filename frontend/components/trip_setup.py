import streamlit as st
from frontend.api import parse_trip, generate_itinerary
from frontend.config import CITIES


def show_trip_setup():
    st.title("✨ Plan Your Perfect Trip")

    if "setup_step" not in st.session_state:
        st.session_state.setup_step = 1
    if "parsed_trip" not in st.session_state:
        st.session_state.parsed_trip = {}

    col1, col2 = st.columns(2)
    for i, (col, step) in enumerate(
        zip([col1, col2], ["💬 Describe", "🎯 Generate"])
    ):
        with col:
            if i + 1 == st.session_state.setup_step:
                st.markdown(
                    f"<div style='background:#1D9E75; color:white; "
                    f"padding:8px; border-radius:8px; text-align:center; "
                    f"font-weight:600'>{step}</div>",
                    unsafe_allow_html=True
                )
            elif i + 1 < st.session_state.setup_step:
                st.markdown(
                    f"<div style='background:#E8F5E9; color:#1D9E75; "
                    f"padding:8px; border-radius:8px; "
                    f"text-align:center'>✅ {step}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background:#F5F5F5; color:#999; "
                    f"padding:8px; border-radius:8px; "
                    f"text-align:center'>{step}</div>",
                    unsafe_allow_html=True
                )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.setup_step == 1:
        show_step1()
    elif st.session_state.setup_step == 2:
        show_step2()


def show_step1():
    st.markdown("### 💬 Tell me about your trip")
    st.caption(
        "Describe your trip naturally — I'll understand destination, "
        "total budget, duration, companions and preferences"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        user_message = st.text_area(
            "Your trip in your own words",
            placeholder=(
                "e.g. I want to take my parents to Jaipur for 4 days, "
                "total budget ₹20000, they love cultural sites. "
                "My dad has knee problems so avoid too much walking."
            ),
            height=130,
            key="trip_message"
        )

    with col2:
        st.markdown("**Or fill manually:**")
        manual_city = st.selectbox(
            "City", [""] + CITIES, key="manual_city"
        )
        manual_days = st.number_input(
            "Days", 1, 14, 3, key="manual_days"
        )
        currency_symbol = st.session_state.get("currency_symbol", "₹")
        manual_total_budget = st.number_input(
            f"Total budget ({currency_symbol})",
            500, 10000000, 10000,
            key="manual_budget"
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🤖 Parse with AI",
            type="primary",
            use_container_width=True,
            key="parse_btn"
        ):
            if not user_message.strip():
                st.error("Please describe your trip first")
            else:
                with st.spinner("AI is understanding your trip..."):
                    result = parse_trip(
                        st.session_state.username, user_message
                    )
                if "error" in result:
                    st.error(
                        "Could not understand. Try being more specific."
                    )
                else:
                    st.session_state.parsed_trip = result
                    st.session_state.trip_city = result.get("city", "")
                    days = result.get("days", 3) or 3
                    st.session_state.trip_days = days

                    total_budget = result.get(
                        "budget_per_day_local", 2000
                    ) or 2000
                    budget_per_day = total_budget / days
                    st.session_state.trip_budget_local = budget_per_day

                    st.session_state.trip_companions = result.get(
                        "travel_companions", ""
                    )
                    st.session_state.trip_requirements = result.get(
                        "special_requirements", ""
                    )

                    city = result.get("city", "?")
                    confidence = int(
                        result.get("confidence", 0) * 100
                    )

                    st.success(
                        f"✅ Got it! **{city}** for **{days} days** | "
                        f"Confidence: {confidence}%"
                    )
                    if result.get("special_requirements"):
                        st.info(
                            f"🔔 Special note: "
                            f"{result['special_requirements']}"
                        )
                    if result.get("travel_companions"):
                        st.info(
                            f"👥 Travelling: "
                            f"{result['travel_companions']}"
                        )

                    import time
                    time.sleep(1)
                    st.session_state.setup_step = 2
                    st.rerun()

    with col2:
        if st.button(
            "Fill manually →",
            use_container_width=True,
            key="manual_btn"
        ):
            if not manual_city:
                st.error("Please select a city")
            else:
                from frontend.currency_helper import local_to_usd
                budget_per_day = manual_total_budget / manual_days
                budget_usd = local_to_usd(
                    budget_per_day,
                    st.session_state.get("currency_symbol", "₹")
                )
                st.session_state.trip_city = manual_city
                st.session_state.trip_days = manual_days
                st.session_state.trip_budget_local = budget_per_day
                st.session_state.trip_budget_usd = budget_usd
                st.session_state.setup_step = 2
                st.rerun()


def show_step2():
    st.markdown("### 🎯 Generating your perfect itinerary...")

    city = st.session_state.get("trip_city", "")
    days = st.session_state.get("trip_days", 3)
    budget_local = st.session_state.get("trip_budget_local", 2000)

    if not city:
        st.error(
            "No city selected. Please go back and describe your trip."
        )
        if st.button("← Go Back"):
            st.session_state.setup_step = 1
            st.rerun()
        return

    from frontend.currency_helper import local_to_usd
    budget_usd = local_to_usd(
        budget_local,
        st.session_state.get("currency_symbol", "₹")
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📍 Destination", city)
    with col2:
        st.metric("📅 Duration", f"{days} days")
    with col3:
        currency_symbol = st.session_state.get("currency_symbol", "₹")
        st.metric(
            "💰 Budget/day",
            f"{currency_symbol}{budget_local:.0f}"
        )

    companions = st.session_state.get("trip_companions", "")
    requirements = st.session_state.get("trip_requirements", "")
    if companions:
        st.info(f"👥 Travelling: {companions}")
    if requirements:
        st.warning(f"🔔 Special note: {requirements}")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.spinner(
        f"Building your perfect {days}-day {city} itinerary... "
        f"Finding best spots, hotels and restaurants near your route..."
    ):
        result = generate_itinerary(
            username=st.session_state.username,
            city=city,
            budget_per_day_usd=budget_usd,
            days=days,
            food_type=None,
            hotel_type=None,
            bedrooms=1
        )

    if "itinerary" in result:
        st.session_state.itinerary = result["itinerary"]
        st.session_state.weather_forecast = result.get("weather_forecast", [])
        st.session_state.city = city
        st.session_state.days = days
        st.session_state.budget_usd = budget_usd
        st.session_state.budget_local = budget_local
        st.session_state.hotels = result.get("hotels", [])
        st.session_state.restaurants = result.get("restaurants", [])
        st.session_state.total_cost_local = result.get(
            "total_cost_local", 0
        )
        st.session_state.travel_personality = result.get(
            "travel_personality", "Explorer"
        )
        st.session_state.collab_recs = result.get(
            "collaborative_recommendations", []
        )
        st.session_state.feedback_given = {}
        st.session_state.replan_triggered = False
        st.session_state.selected_hotel = None
        st.session_state.is_saved_trip = False
        st.session_state.current_trip_id = None
        st.session_state.current_trip_notes = ""
        st.session_state.setup_step = 1
        st.session_state.page = "itinerary"
        st.rerun()
    else:
        st.error("Could not generate itinerary. Please try again.")
        if st.button("← Try Again"):
            st.session_state.setup_step = 1
            st.rerun()
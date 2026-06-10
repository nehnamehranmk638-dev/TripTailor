import streamlit as st
from frontend.api import parse_trip, generate_itinerary, get_countries
from frontend.config import CITIES, HOTEL_TYPES, FOOD_TYPES

def show_trip_setup():
    st.title("✨ Plan Your Perfect Trip")

    if "setup_step" not in st.session_state:
        st.session_state.setup_step = 1
    if "parsed_trip" not in st.session_state:
        st.session_state.parsed_trip = {}

    steps = ["💬 Describe", "🏨 Stay", "🍽️ Food", "🎯 Generate"]
    cols = st.columns(4)
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if i + 1 == st.session_state.setup_step:
                st.markdown(
                    f"<div style='background:#1D9E75; color:white; padding:8px; "
                    f"border-radius:8px; text-align:center; font-weight:600'>{step}</div>",
                    unsafe_allow_html=True
                )
            elif i + 1 < st.session_state.setup_step:
                st.markdown(
                    f"<div style='background:#E8F5E9; color:#1D9E75; padding:8px; "
                    f"border-radius:8px; text-align:center'>✅ {step}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background:#F5F5F5; color:#999; padding:8px; "
                    f"border-radius:8px; text-align:center'>{step}</div>",
                    unsafe_allow_html=True
                )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.setup_step == 1:
        show_step1()
    elif st.session_state.setup_step == 2:
        show_step2()
    elif st.session_state.setup_step == 3:
        show_step3()
    elif st.session_state.setup_step == 4:
        show_step4()

def show_step1():
    st.markdown("### 💬 Tell me about your trip")
    st.caption("Describe your trip naturally — destination, budget, duration, who you're travelling with")

    col1, col2 = st.columns([3, 1])
    with col1:
        user_message = st.text_area(
            "Your trip in your own words",
            placeholder="e.g. I want to take my parents to Jaipur for 4 days, budget ₹5000 per day, we prefer vegetarian food and cultural sites. My dad has trouble walking so avoid too much physical activity.",
            height=120,
            key="trip_message"
        )

    with col2:
        st.markdown("**Or fill manually:**")
        manual_city = st.selectbox("City", [""] + CITIES, key="manual_city")
        manual_days = st.number_input("Days", 1, 14, 3, key="manual_days")
        manual_budget = st.number_input(
            f"Budget/day ({st.session_state.currency_symbol})",
            100, 100000, 2000, key="manual_budget"
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🤖 Parse with AI", type="primary",
                    use_container_width=True, key="parse_btn"):
            if not user_message.strip():
                st.error("Please describe your trip first")
            else:
                with st.spinner("AI is understanding your trip..."):
                    result = parse_trip(st.session_state.username, user_message)

                if "error" in result:
                    st.error("Could not understand. Try being more specific.")
                else:
                    st.session_state.parsed_trip = result
                    if result.get("city"):
                        st.session_state.trip_city = result["city"]
                    if result.get("days"):
                        st.session_state.trip_days = result["days"]
                    if result.get("budget_per_day_local"):
                        from frontend.currency_helper import local_to_usd
                        st.session_state.trip_budget_local = result["budget_per_day_local"]
                    if result.get("food_type"):
                        st.session_state.trip_food_type = result["food_type"]

                    st.success(
                        f"✅ Got it! {result.get('city', '?')} for "
                        f"{result.get('days', '?')} days | "
                        f"Confidence: {int(result.get('confidence', 0) * 100)}%"
                    )
                    if result.get("special_requirements"):
                        st.info(f"🔔 Special note: {result['special_requirements']}")
                    st.session_state.setup_step = 2
                    st.rerun()

    with col2:
        if st.button("Fill manually →", use_container_width=True, key="manual_btn"):
            if not manual_city:
                st.error("Please select a city")
            else:
                from frontend.currency_helper import local_to_usd
                budget_usd = local_to_usd(
                    manual_budget,
                    st.session_state.get("currency_symbol", "₹")
                )
                st.session_state.trip_city = manual_city
                st.session_state.trip_days = manual_days
                st.session_state.trip_budget_local = manual_budget
                st.session_state.trip_budget_usd = budget_usd
                st.session_state.setup_step = 2
                st.rerun()

def show_step2():
    st.markdown("### 🏨 Where would you like to stay?")
    parsed = st.session_state.get("parsed_trip", {})

    col1, col2 = st.columns(2)
    with col1:
        hotel_type = st.selectbox(
            "Type of accommodation",
            HOTEL_TYPES,
            index=HOTEL_TYPES.index(parsed.get("hotel_type", "Hotel"))
            if parsed.get("hotel_type") in HOTEL_TYPES else 0
        )
        hotel_descriptions = {
            "Hotel": "🏨 Standard hotel rooms with all amenities",
            "Resort": "🌴 Premium resort with pools, spa and activities",
            "Villa": "🏡 Private villa with personal space and privacy"
        }
        st.info(hotel_descriptions[hotel_type])

    with col2:
        bedrooms = st.selectbox(
            "Number of bedrooms",
            [1, 2, 3, 4, 5],
            index=min((parsed.get("bedrooms", 1) or 1) - 1, 4)
        )
        st.caption("Choose based on your group size")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.setup_step = 1
            st.rerun()
    with col2:
        if st.button("Next: Food →", type="primary", use_container_width=True):
            st.session_state.trip_hotel_type = hotel_type
            st.session_state.trip_bedrooms = bedrooms
            st.session_state.setup_step = 3
            st.rerun()

def show_step3():
    st.markdown("### 🍽️ What are your food preferences?")
    parsed = st.session_state.get("parsed_trip", {})

    col1, col2 = st.columns(2)
    with col1:
        food_type = st.radio(
            "Food preference",
            ["veg", "non-veg"],
            index=0 if parsed.get("food_type") == "veg" else 1,
            format_func=lambda x: "🥦 Vegetarian" if x == "veg" else "🍖 Non-Vegetarian"
        )

    with col2:
        st.markdown("**This helps us:**")
        st.markdown("- Filter restaurant recommendations")
        st.markdown("- Prioritize food spots matching your diet")
        st.markdown("- Suggest cuisine types you'll enjoy")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.setup_step = 2
            st.rerun()
    with col2:
        if st.button("Generate Itinerary! →", type="primary",
                    use_container_width=True):
            st.session_state.trip_food_type = food_type
            st.session_state.setup_step = 4
            st.rerun()

def show_step4():
    st.markdown("### 🎯 Generating your perfect itinerary...")

    city = st.session_state.get("trip_city", "Mumbai")
    days = st.session_state.get("trip_days", 3)
    budget_local = st.session_state.get("trip_budget_local", 2000)
    hotel_type = st.session_state.get("trip_hotel_type", "Hotel")
    bedrooms = st.session_state.get("trip_bedrooms", 1)
    food_type = st.session_state.get("trip_food_type", "veg")

    from frontend.currency_helper import local_to_usd
    budget_usd = local_to_usd(budget_local,
                              st.session_state.get("currency_symbol", "₹"))

    with st.spinner(f"Building your {days}-day {city} itinerary..."):
        result = generate_itinerary(
            username=st.session_state.username,
            city=city,
            budget_per_day_usd=budget_usd,
            days=days,
            food_type=food_type,
            hotel_type=hotel_type,
            bedrooms=bedrooms
        )

    if "itinerary" in result:
        st.session_state.itinerary = result["itinerary"]
        st.session_state.city = city
        st.session_state.days = days
        st.session_state.budget_usd = budget_usd
        st.session_state.budget_local = budget_local
        st.session_state.hotels = result.get("hotels", [])
        st.session_state.restaurants = result.get("restaurants", [])
        st.session_state.total_cost_local = result.get("total_cost_local", 0)
        st.session_state.travel_personality = result.get("travel_personality", "Explorer")
        st.session_state.collab_recs = result.get("collaborative_recommendations", [])
        st.session_state.feedback_given = {}
        st.session_state.replan_triggered = False
        st.session_state.setup_step = 1
        st.session_state.page = "itinerary"
        st.rerun()
    else:
        st.error("Could not generate itinerary. Please try again.")
        if st.button("← Try Again"):
            st.session_state.setup_step = 1
            st.rerun()
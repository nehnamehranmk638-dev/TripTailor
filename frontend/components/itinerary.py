import streamlit as st
from frontend.api import submit_feedback, smart_replan, midtrip_assist, save_trip
from frontend.config import TIME_ICONS, CATEGORY_ICONS, PERSONALITY_ICONS
from frontend.map_view import show_map

def show_sidebar_chat():
    with st.sidebar:
        st.markdown("### 💬 Trip Assistant")
        st.caption("Ask me anything about your trip")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for msg in st.session_state.chat_history[-6:]:
            if msg["role"] == "user":
                st.markdown(
                    f"<div style='background:#1D9E75; color:white; "
                    f"padding:8px 12px; border-radius:12px 12px 4px 12px; "
                    f"margin:4px 0; font-size:13px'>{msg['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background:#F0F2F6; color:#333; "
                    f"padding:8px 12px; border-radius:12px 12px 12px 4px; "
                    f"margin:4px 0; font-size:13px'>{msg['content']}</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        user_input = st.text_input(
            "Your message",
            key="sidebar_chat_input",
            placeholder="e.g. It's raining tomorrow...",
            label_visibility="collapsed"
        )

        if st.button("Send 💬", use_container_width=True, key="send_chat"):
            if user_input.strip():
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_input}
                )
                with st.spinner("Thinking..."):
                    result = midtrip_assist(
                        username=st.session_state.username,
                        message=user_input,
                        city=st.session_state.city,
                        current_itinerary=st.session_state.itinerary
                    )
                ai_response = result.get("ai_response", {})
                response_text = ai_response.get(
                    "response_message",
                    "I understand. Let me help you with that."
                )
                suggestions = result.get("suggestions", [])
                if suggestions:
                    response_text += "\n\nAlternatives: "
                    for s in suggestions:
                        response_text += f"{s['name']} ({s['category']}). "

                st.session_state.chat_history.append(
                    {"role": "assistant", "content": response_text}
                )
                st.rerun()

        if st.session_state.chat_history:
            if st.button("Clear chat", use_container_width=True,
                        key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()

        st.divider()
        st.markdown("**Try asking:**")
        st.caption("• It's raining, suggest indoor spots")
        st.caption("• We're tired, remove Day 3 evening")
        st.caption("• Suggest something for kids")
        st.caption("• Best time to visit the fort?")

def show_itinerary():
    show_sidebar_chat()

    itinerary = st.session_state.itinerary
    city = st.session_state.city
    days = st.session_state.days
    currency_symbol = st.session_state.get("currency_symbol", "₹")
    budget_local = st.session_state.get("budget_local", 0)
    total_cost_local = st.session_state.get("total_cost_local", 0)
    hotels = st.session_state.get("hotels", [])
    restaurants = st.session_state.get("restaurants", [])
    personality = st.session_state.get("travel_personality", "Explorer")

    if "feedback_given" not in st.session_state:
        st.session_state.feedback_given = {}
    if "replan_triggered" not in st.session_state:
        st.session_state.replan_triggered = False
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "timeline"

    col1, col2 = st.columns([3, 1])
    with col1:
        icon = PERSONALITY_ICONS.get(personality, "🧭")
        st.title(f"🗺️ Your {days}-Day {city} Itinerary")
        st.caption(
            f"{icon} {personality} | "
            f"Budget: {currency_symbol}{budget_local}/day | "
            f"Total spots cost: {currency_symbol}{total_cost_local}"
        )
    with col2:
        if st.button("💾 Save Trip", use_container_width=True):
            save_current_trip()
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "📋 Timeline",
            type="primary" if st.session_state.view_mode == "timeline" else "secondary",
            use_container_width=True
        ):
            st.session_state.view_mode = "timeline"
            st.rerun()
    with col2:
        if st.button(
            "🗺️ Map View",
            type="primary" if st.session_state.view_mode == "map" else "secondary",
            use_container_width=True
        ):
            st.session_state.view_mode = "map"
            st.rerun()

    has_dislikes = any(
        v == "down" for v in st.session_state.feedback_given.values()
    )
    if has_dislikes:
        dislike_count = sum(
            1 for v in st.session_state.feedback_given.values()
            if v == "down"
        )
        like_count = sum(
            1 for v in st.session_state.feedback_given.values()
            if v == "up"
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            parts = []
            if like_count:
                parts.append(f"❤️ {like_count} locked in")
            if dislike_count:
                parts.append(f"🚫 {dislike_count} to replace")
            st.info(" | ".join(parts))
        with col2:
            if st.button("🔄 Replan", type="primary",
                        use_container_width=True, key="replan_btn"):
                st.session_state.replan_triggered = True
                st.rerun()

    st.divider()

    if st.session_state.view_mode == "map":
        st.markdown(f"### 📍 {city} — Your route")
        show_map(itinerary, city)
        st.divider()

    show_timeline(itinerary)

    if hotels:
        st.divider()
        show_hotels(hotels, currency_symbol)

    if restaurants:
        st.divider()
        show_restaurants(restaurants, currency_symbol)

    collab_recs = st.session_state.get("collab_recs", [])
    if collab_recs:
        st.divider()
        st.markdown("### 👥 Loved by travelers like you")
        cols = st.columns(len(collab_recs))
        for col, rec in zip(cols, collab_recs):
            with col:
                st.markdown(f"**{rec['name']}**")
                st.caption(f"{rec['category']} | ⭐ {rec['rating']}")
                st.caption(rec.get("reason", ""))

    if st.session_state.replan_triggered:
        st.session_state.replan_triggered = False
        liked_ids = [
            sid for sid, d in st.session_state.feedback_given.items()
            if d == "up"
        ]
        disliked_ids = [
            sid for sid, d in st.session_state.feedback_given.items()
            if d == "down"
        ]
        with st.spinner("Replanning only the spots you disliked..."):
            result = smart_replan(
                username=st.session_state.username,
                city=city,
                budget_per_day_usd=st.session_state.get("budget_usd", 50),
                days=days,
                current_itinerary=itinerary,
                locked_spot_ids=liked_ids,
                disliked_spot_ids=disliked_ids
            )
        if "itinerary" in result:
            st.session_state.itinerary = result["itinerary"]
            st.session_state.feedback_given = {}
            st.rerun()
        else:
            st.error("Replan failed. Try again.")

def show_timeline(itinerary):
    time_slots = ["Morning", "Afternoon", "Evening"]
    for day_num in sorted(itinerary.keys(), key=lambda x: int(x)):
        st.markdown(f"## 📅 Day {day_num}")
        day_data = itinerary[day_num]
        for i, time_slot in enumerate(time_slots):
            spot = day_data.get(time_slot)
            col_dot, col_content = st.columns([1, 15])
            with col_dot:
                st.markdown(
                    "<div style='text-align:center; padding-top:8px'>🔵</div>",
                    unsafe_allow_html=True
                )
                if i < len(time_slots) - 1:
                    st.markdown(
                        "<div style='text-align:center; color:#1D9E75; "
                        "line-height:1.8; font-size:16px'>│<br>│<br>│</div>",
                        unsafe_allow_html=True
                    )
            with col_content:
                if spot is None:
                    st.info(
                        f"{TIME_ICONS.get(time_slot, '')} {time_slot} — "
                        f"No spot available"
                    )
                else:
                    render_spot_card(day_num, time_slot, spot)
        st.divider()

def render_spot_card(day, time_slot, spot):
    spot_id = int(spot["id"])
    feedback = st.session_state.feedback_given.get(spot_id)
    currency_symbol = st.session_state.get("currency_symbol", "₹")

    cat_icon = CATEGORY_ICONS.get(spot["category"], "📍")
    stars = "⭐" * int(round(spot["rating"]))
    cost_usd = spot["cost_usd"]
    cost_local = spot.get("cost_local", 0)

    if cost_usd == 0:
        cost_str = "Free"
    else:
        cost_str = f"{currency_symbol}{cost_local} (${cost_usd})"

    liked = feedback == "up"
    disliked = feedback == "down"
    border_color = "#1D9E75" if liked else "#E24B4A" if disliked else "#e0e0e0"

    st.markdown(
        f"<div style='border-left:4px solid {border_color}; "
        f"padding-left:12px; margin-bottom:4px'>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(
            f"{TIME_ICONS.get(time_slot, '')} **{time_slot}: {spot['name']}**"
        )
        st.caption(
            f"{cat_icon} {spot['category']} | "
            f"💰 {cost_str} | "
            f"{stars} {spot['rating']} | "
            f"⏱️ {spot.get('duration_hours', 2)}h | "
            f"📝 {spot['description']}"
        )
    with col2:
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button(
                "✅" if liked else "👍",
                key=f"up_{day}_{time_slot}_{spot_id}",
                help="Like — click again to undo"
            ):
                if liked:
                    del st.session_state.feedback_given[spot_id]
                else:
                    submit_feedback(
                        st.session_state.username, spot_id, "up"
                    )
                    st.session_state.feedback_given[spot_id] = "up"
                st.rerun()
        with btn_col2:
            if st.button(
                "❌" if disliked else "👎",
                key=f"down_{day}_{time_slot}_{spot_id}",
                help="Dislike — click again to undo"
            ):
                if disliked:
                    del st.session_state.feedback_given[spot_id]
                else:
                    submit_feedback(
                        st.session_state.username, spot_id, "down"
                    )
                    st.session_state.feedback_given[spot_id] = "down"
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

def show_hotels(hotels, currency_symbol):
    st.markdown("### 🏨 Recommended Hotels")
    cols = st.columns(min(len(hotels), 3))
    for col, hotel in zip(cols, hotels[:3]):
        with col:
            st.markdown(f"#### {hotel['name']}")
            st.write(f"{'⭐' * int(round(hotel['rating']))} {hotel['rating']}")
            st.write(f"🏷️ {hotel['type']} | 🛏️ {hotel['bedrooms']} bedroom(s)")
            st.write(
                f"**{currency_symbol}{hotel.get('price_per_night_local', 0)}/night** "
                f"(${hotel['price_per_night_usd']})"
            )
            st.caption(f"✨ {hotel['amenities']}")
            st.caption(hotel['description'])

def show_restaurants(restaurants, currency_symbol):
    st.markdown("### 🍽️ Recommended Restaurants")
    cols = st.columns(min(len(restaurants), 3))
    for col, rest in zip(cols, restaurants[:3]):
        with col:
            food_emoji = "🥦" if rest["food_type"] == "veg" else "🍖"
            st.markdown(f"#### {rest['name']}")
            st.write(f"{'⭐' * int(round(rest['rating']))} {rest['rating']}")
            st.write(f"{food_emoji} {rest['food_type']} | 🍴 {rest['cuisine']}")
            st.write(
                f"**{currency_symbol}{rest.get('price_per_meal_local', 0)}/meal** "
                f"(${rest['price_per_meal_usd']})"
            )
            st.caption(rest['description'])

def save_current_trip():
    currency_symbol = st.session_state.get("currency_symbol", "₹")
    result = save_trip(
        username=st.session_state.username,
        city=st.session_state.city,
        country=st.session_state.get("country", "India"),
        days=st.session_state.days,
        budget_per_day_usd=st.session_state.get("budget_usd", 50),
        budget_per_day_local=st.session_state.get("budget_local", 0),
        currency_code=st.session_state.get("currency_code", "INR"),
        currency_symbol=currency_symbol,
        hotel_type=st.session_state.get("trip_hotel_type", "Hotel"),
        bedrooms=st.session_state.get("trip_bedrooms", 1),
        food_type=st.session_state.get("trip_food_type", "veg"),
        itinerary_data=st.session_state.itinerary,
        hotel_data={"hotels": st.session_state.get("hotels", [])},
        restaurant_data={"restaurants": st.session_state.get("restaurants", [])}
    )
    if "trip_id" in result:
        st.success(f"✅ Trip saved as '{result.get('trip_name')}'!")
    else:
        st.error("Could not save trip")
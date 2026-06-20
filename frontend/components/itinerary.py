import streamlit as st
from datetime import datetime
from frontend.api import (submit_feedback, smart_replan, midtrip_assist,
                          save_trip, get_trip_chat, save_trip_chat,
                          clear_trip_chat, get_trip_notes, add_trip_note,
                          delete_trip_note, update_trip_itinerary,
                          get_local_tip)
from frontend.config import CATEGORY_ICONS
from frontend.map_view import show_map


def _check_opening_hours(spot, start_time_str):
    try:
        opening = spot.get("opening_time", "09:00") or "09:00"
        closing = spot.get("closing_time", "18:00") or "18:00"
        closed_day = spot.get("closed_day", "") or ""

        open_h, open_m = map(int, opening.split(":"))
        close_h, close_m = map(int, closing.split(":"))
        open_mins = open_h * 60 + open_m
        close_mins = close_h * 60 + close_m

        is_pm = "PM" in start_time_str
        parts = start_time_str.replace(" AM", "").replace(
            " PM", ""
        ).split(":")
        start_h = int(parts[0])
        start_m = int(parts[1])
        if is_pm and start_h != 12:
            start_h += 12
        if not is_pm and start_h == 12:
            start_h = 0
        start_mins = start_h * 60 + start_m

        warnings = []

        today = datetime.now().strftime("%A")
        if closed_day and today.lower() == closed_day.lower():
            warnings.append(
                f"⚠️ Closed on {closed_day}s — verify before visiting"
            )

        if start_mins < open_mins:
            warnings.append(
                f"⚠️ Opens at {opening} — you may arrive too early"
            )
        elif start_mins >= close_mins - 30:
            warnings.append(
                f"⚠️ Closes at {closing} — limited time remaining"
            )

        afternoon_break = spot.get("afternoon_break", False)
        if afternoon_break and 12 * 60 <= start_mins <= 16 * 60:
            warnings.append(
                "⚠️ Closed 12pm-4pm for afternoon break"
            )

        return warnings
    except:
        return []


def _get_nearby_restaurant(restaurants, spot_lat, spot_lon,
                           meal_type="lunch"):
    if not restaurants:
        return None
    if isinstance(restaurants, dict):
        restaurants = restaurants.get("restaurants", [])
    if not restaurants:
        return None

    def dist(r):
        if not (r.get("latitude") and spot_lat):
            return 999
        try:
            import math
            lat1, lon1 = float(spot_lat), float(spot_lon)
            lat2, lon2 = float(r["latitude"]), float(r["longitude"])
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat/2)**2 +
                 math.cos(math.radians(lat1)) *
                 math.cos(math.radians(lat2)) *
                 math.sin(dlon/2)**2)
            return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        except:
            return 999

    sorted_rests = sorted(restaurants, key=dist)
    return sorted_rests[0] if sorted_rests else None


def show_sidebar_chat():
    with st.sidebar:
        trip_id = st.session_state.get("current_trip_id")
        chat_key = f"chat_{trip_id}_{st.session_state.get('city', '')}"
        input_key = f"input_key_{trip_id}"

        if chat_key not in st.session_state:
            if trip_id:
                st.session_state[chat_key] = get_trip_chat(trip_id)
            else:
                st.session_state[chat_key] = []

        if input_key not in st.session_state:
            st.session_state[input_key] = 0

        if "pending_suggestion" in st.session_state:
            pending = st.session_state.pending_suggestion
            spot = pending.get("spot", {})
            all_suggestions = pending.get("all_suggestions", [spot])

            st.markdown("### 💡 AI Suggestion")
            st.caption("Choose an alternative to add to your trip")

            if pending.get("day"):
                st.info(f"For Day {pending.get('day')}")

            suggestion_names = [
                f"{s.get('name', '')} ({s.get('category', '')})"
                for s in all_suggestions
            ]
            selected_idx = st.radio(
                "Choose one:",
                range(len(suggestion_names)),
                format_func=lambda i: suggestion_names[i],
                key="suggestion_radio"
            )
            selected_spot = all_suggestions[selected_idx]
            st.markdown(f"**{selected_spot.get('name')}**")
            st.caption(
                f"⭐ {selected_spot.get('rating')} | "
                f"⏱️ {selected_spot.get('duration_hours', 2)}h | "
                f"{selected_spot.get('category')}"
            )
            st.caption(selected_spot.get("description", ""))

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "✅ Add to trip",
                    use_container_width=True,
                    type="primary",
                    key="apply_suggestion"
                ):
                    pending["spot"] = selected_spot
                    apply_ai_suggestion(pending)
                    del st.session_state.pending_suggestion
                    st.rerun()
            with col2:
                if st.button(
                    "❌ Skip",
                    use_container_width=True,
                    key="dismiss_suggestion"
                ):
                    del st.session_state.pending_suggestion
                    st.rerun()

            st.divider()

        st.markdown("### 💬 Trip Assistant")
        st.caption("Ask me anything about your trip")

        chat_history = st.session_state[chat_key]

        for msg in chat_history[-8:]:
            if msg["role"] == "user":
                st.markdown(
                    f"<div style='background:#1D9E75; color:white;"
                    f" padding:8px 12px; border-radius:12px 12px"
                    f" 4px 12px; margin:4px 0; font-size:13px'>"
                    f"{msg['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background:#F0F2F6; color:#333;"
                    f" padding:8px 12px; border-radius:12px 12px"
                    f" 12px 4px; margin:4px 0; font-size:13px'>"
                    f"{msg['content']}</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        user_input = st.text_input(
            "Message",
            key=f"chat_input_{st.session_state[input_key]}_{trip_id}",
            placeholder="e.g. Replace Day 2 with something indoors",
            label_visibility="collapsed"
        )

        if st.button(
            "Send 💬",
            use_container_width=True,
            key=f"send_{st.session_state[input_key]}_{trip_id}"
        ):
            if user_input.strip():
                chat_history.append(
                    {"role": "user", "content": user_input}
                )
                if trip_id:
                    save_trip_chat(trip_id, "user", user_input)

                with st.spinner("Thinking..."):
                    result = midtrip_assist(
                        username=st.session_state.username,
                        message=user_input,
                        city=st.session_state.city,
                        current_itinerary=st.session_state.itinerary,
                        chat_history=chat_history
                    )

                ai_response = result.get("ai_response", {})
                response_text = ai_response.get(
                    "response_message",
                    "I understand. Let me help you with that."
                )
                suggestions = result.get("suggestions", [])
                restaurant_suggestions = result.get("restaurant_suggestions", [])

                if suggestions:
                    response_text += (
                        f"\n\nFound {len(suggestions)} alternative(s)."
                        f" See suggestion panel above ☝️"
                    )
                    target_day = result.get("target_day")
                    target_slot = result.get("target_time_slot")
                    st.session_state.pending_suggestion = {
                        "day": str(target_day) if target_day else None,
                        "time_slot": target_slot,
                        "spot": suggestions[0],
                        "all_suggestions": suggestions
                    }
                elif restaurant_suggestions:
                    response_text += "\n\n"
                    for r in restaurant_suggestions:
                        response_text += (
                            f"\n🍽️ **{r['name']}** ({r.get('cuisine', '')}) — "
                            f"{r['currency_symbol']}{r['cost_local']:.0f} | "
                            f"⭐ {r['rating']}\n_{r.get('description', '')}_\n"
                        )

                chat_history.append(
                    {"role": "assistant", "content": response_text}
                )
                if trip_id:
                    save_trip_chat(trip_id, "assistant", response_text)

                st.session_state[chat_key] = chat_history
                st.session_state[input_key] += 1
                st.rerun()

        if chat_history:
            if st.button(
                "Clear chat",
                use_container_width=True,
                key=f"clear_{trip_id}"
            ):
                if trip_id:
                    clear_trip_chat(trip_id)
                st.session_state[chat_key] = []
                st.session_state[input_key] += 1
                st.rerun()


def apply_ai_suggestion(pending):
    day = pending.get("day")
    new_spot = pending.get("spot")
    if not new_spot:
        return

    itinerary = st.session_state.itinerary
    currency_symbol = st.session_state.get("currency_symbol", "₹")
    cost_local = round(new_spot.get("cost_usd", 0) * 83.5, 2)
    new_spot_full = {**new_spot, "cost_local": cost_local,
                    "currency_symbol": currency_symbol}

    target_day = str(day) if day else None

    if target_day and target_day in itinerary:
        slots = itinerary[target_day]
        if isinstance(slots, list):
            disliked_ids = [
                sid for sid, d in st.session_state.feedback_given.items()
                if d == "down"
            ]
            replaced = False
            for i, slot in enumerate(slots):
                if slot.get("spot", {}).get("id") in disliked_ids:
                    slots[i] = {
                        **slot,
                        "duration_hours": new_spot.get(
                            "duration_hours", 2.0
                        ),
                        "spot": new_spot_full
                    }
                    replaced = True
                    break
            if not replaced:
                last = slots[-1] if slots else {}
                last_end = last.get("end_time", "8:00 PM")
                dur = new_spot.get("duration_hours", 2.0)
                dur_mins = int(dur * 60)
                slots.append({
                    "start_time": _add_minutes_to_time(last_end, 30),
                    "end_time": _add_minutes_to_time(
                        last_end, 30 + dur_mins
                    ),
                    "duration_hours": dur,
                    "time_label": _get_label_from_time(
                        _add_minutes_to_time(last_end, 30)
                    ),
                    "travel_mins": 30,
                    "transport_mode": None,
                    "transport_label": None,
                    "spot": new_spot_full
                })
            itinerary[target_day] = slots
    else:
        for day_key in sorted(itinerary.keys(), key=lambda x: int(x)):
            slots = itinerary[day_key]
            if isinstance(slots, list):
                dur = new_spot.get("duration_hours", 2.0)
                dur_mins = int(dur * 60)
                last_end = slots[-1].get(
                    "end_time", "9:00 AM"
                ) if slots else "9:00 AM"
                slots.append({
                    "start_time": _add_minutes_to_time(last_end, 30),
                    "end_time": _add_minutes_to_time(
                        last_end, 30 + dur_mins
                    ),
                    "duration_hours": dur,
                    "time_label": _get_label_from_time(
                        _add_minutes_to_time(last_end, 30)
                    ),
                    "travel_mins": 30,
                    "transport_mode": None,
                    "transport_label": None,
                    "spot": new_spot_full
                })
                itinerary[day_key] = slots
                break

    st.session_state.itinerary = itinerary
    trip_id = st.session_state.get("current_trip_id")
    if trip_id:
        update_trip_itinerary(
            trip_id, st.session_state.username, itinerary
        )
    st.success(f"✅ Added {new_spot.get('name')} to your itinerary!")
    st.session_state.feedback_given = {}


def _add_minutes_to_time(time_str, minutes):
    try:
        is_pm = "PM" in time_str
        is_am = "AM" in time_str
        clean = time_str.replace(" AM", "").replace(" PM", "")
        h, m = map(int, clean.split(":"))
        if is_pm and h != 12:
            h += 12
        if is_am and h == 12:
            h = 0
        total = min(h * 60 + m + minutes, 20 * 60)
        return _format_time_from_mins(total)
    except:
        return "8:00 PM"


def _format_time_from_mins(minutes):
    hour = minutes // 60
    minute = minutes % 60
    am_pm = "AM" if hour < 12 else "PM"
    dh = hour if hour <= 12 else hour - 12
    if dh == 0:
        dh = 12
    return f"{dh}:{minute:02d} {am_pm}"


def _get_label_from_time(time_str):
    try:
        is_pm = "PM" in time_str
        hour = int(time_str.split(":")[0])
        if is_pm and hour != 12:
            hour += 12
        return ("Morning" if hour < 12
                else "Afternoon" if hour < 17
                else "Evening")
    except:
        return "Morning"


def calculate_budget_breakdown(itinerary, hotels, restaurants,
                               currency_symbol, budget_local, days):
    entry_fees = 0
    for day_slots in itinerary.values():
        if isinstance(day_slots, list):
            for slot in day_slots:
                if isinstance(slot, dict):
                    spot = slot.get("spot", {})
                    cost = spot.get("cost_local", 0)
                    if cost:
                        entry_fees += float(cost)

    total_budget = budget_local * days

    cheapest_hotel = None
    if isinstance(hotels, list) and hotels:
        cheapest_hotel = sorted(
            hotels, key=lambda h: h.get("price_per_night_local", 999999)
        )[0]

    cheapest_meal = None
    if isinstance(restaurants, list) and restaurants:
        cheapest_meal = sorted(
            restaurants,
            key=lambda r: r.get("price_per_meal_local", 999999)
        )[0]

    remaining_after_entry = total_budget - entry_fees

    nights = max(days - 1, 1)
    suggested_stay_per_night = (
        remaining_after_entry * 0.4 / nights if remaining_after_entry > 0
        else 0
    )
    suggested_food_per_day = (
        remaining_after_entry * 0.4 / days if remaining_after_entry > 0
        else 0
    )
    suggested_transport_per_day = (
        remaining_after_entry * 0.2 / days if remaining_after_entry > 0
        else 0
    )

    stay_cost = suggested_stay_per_night * nights
    food_cost = suggested_food_per_day * days
    transport_cost = suggested_transport_per_day * days

    total_estimated = entry_fees + stay_cost + food_cost + transport_cost
    buffer = total_budget - total_estimated
    buffer_pct = (buffer / total_budget * 100) if total_budget > 0 else 0

    return {
        "entry_fees": round(entry_fees, 0),
        "stay_cost": round(stay_cost, 0),
        "food_cost": round(food_cost, 0),
        "transport_cost": round(transport_cost, 0),
        "total_estimated": round(total_estimated, 0),
        "total_budget": round(total_budget, 0),
        "buffer": round(buffer, 0),
        "buffer_pct": round(buffer_pct, 1),
        "cheapest_hotel": cheapest_hotel,
        "cheapest_meal": cheapest_meal,
        "days": days,
        "suggested_stay_per_night": round(suggested_stay_per_night, 0),
        "suggested_food_per_day": round(suggested_food_per_day, 0)
    }


def show_budget_tab():
    currency_symbol = st.session_state.get("currency_symbol", "₹")
    budget_local = st.session_state.get("budget_local", 0)
    days = st.session_state.get("days", 1)
    itinerary = st.session_state.get("itinerary", {})

    hotels = st.session_state.get("hotels", [])
    restaurants = st.session_state.get("restaurants", [])
    if isinstance(hotels, dict):
        hotels = hotels.get("hotels", [])
    if isinstance(restaurants, dict):
        restaurants = restaurants.get("restaurants", [])
    if not isinstance(hotels, list):
        hotels = []
    if not isinstance(restaurants, list):
        restaurants = []

    b = calculate_budget_breakdown(
        itinerary, hotels, restaurants,
        currency_symbol, budget_local, days
    )

    st.markdown("### 💰 Trip Budget Breakdown")
    st.caption(
        f"Estimated costs for your {days}-day trip to "
        f"{st.session_state.get('city', '')}"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Your Total Budget",
                  f"{currency_symbol}{b['total_budget']:,.0f}")
    with col2:
        st.metric("Estimated Cost",
                  f"{currency_symbol}{b['total_estimated']:,.0f}")
    with col3:
        if b["buffer"] >= 0:
            st.metric("Buffer Remaining",
                      f"{currency_symbol}{b['buffer']:,.0f}",
                      delta=f"{b['buffer_pct']}% under budget")
        else:
            st.metric("Over Budget By",
                      f"{currency_symbol}{abs(b['buffer']):,.0f}",
                      delta=f"{abs(b['buffer_pct'])}% over",
                      delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 📊 Cost Breakdown")

    for label, amount, note in [
        ("🎫 Entry Fees", b["entry_fees"], "All spot entry costs"),
        ("🏨 Accommodation", b["stay_cost"],
         f"{max(days-1,1)} night(s) budget hotel"),
        ("🍽️ Food", b["food_cost"],
         f"3 meals/day × {days} days"),
        ("🚗 Transport", b["transport_cost"],
         f"Auto/bus × {days} days"),
    ]:
        col1, col2, col3 = st.columns([3, 1, 2])
        with col1:
            st.write(f"**{label}**")
            st.caption(note)
        with col2:
            st.write(f"**{currency_symbol}{amount:,.0f}**")
        with col3:
            pct = (amount / b["total_estimated"] * 100
                   ) if b["total_estimated"] > 0 else 0
            st.progress(min(pct / 100, 1.0))

    st.divider()

    for label, amount, is_buffer in [
        ("**💰 Total Estimated**", b["total_estimated"], False),
        ("**🎯 Your Budget**", b["total_budget"], False),
        (("**✅ Buffer**" if b["buffer"] >= 0 else "**⚠️ Over Budget**"),
         abs(b["buffer"]), True)
    ]:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(label)
        with col2:
            if is_buffer:
                color = "green" if b["buffer"] >= 0 else "red"
                st.markdown(
                    f"<span style='color:{color}; font-weight:600'>"
                    f"{currency_symbol}{amount:,.0f}</span>",
                    unsafe_allow_html=True
                )
            else:
                st.write(f"**{currency_symbol}{amount:,.0f}**")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if b["cheapest_hotel"]:
            st.markdown("#### 🏨 Budget Stay")
            h = b["cheapest_hotel"]
            st.markdown(f"**{h.get('name', '')}**")
            st.write(f"🏷️ {h.get('type', '')} | ⭐ {h.get('rating', '')}")
            st.write(
                f"💰 {currency_symbol}"
                f"{h.get('price_per_night_local', 0):,.0f}/night"
            )
            st.write(f"📍 {h.get('neighborhood', '')}")
            st.markdown(
                f"[📍 Maps]({h.get('google_maps_url', '#')})"
            )
    with col2:
        if b["cheapest_meal"]:
            st.markdown("#### 🍽️ Budget Meal")
            r = b["cheapest_meal"]
            fe = "🥦" if r.get("food_type") == "veg" else "🍖"
            st.markdown(f"**{r.get('name', '')}**")
            st.write(
                f"{fe} {r.get('cuisine', '')} | ⭐ {r.get('rating', '')}"
            )
            st.write(
                f"💰 {currency_symbol}"
                f"{r.get('price_per_meal_local', 0):,.0f}/meal"
            )
            st.write(f"📍 {r.get('neighborhood', '')}")
            st.markdown(
                f"[📍 Maps]({r.get('google_maps_url', '#')})"
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.warning(
        "🛍️ **Shopping & Adventure** not included — "
        "these are discretionary expenses. Budget separately."
    )
    st.info(
        "💡 Estimates based on budget options. "
        "Actual costs may vary."
    )


def show_itinerary():
    show_sidebar_chat()

    itinerary = st.session_state.itinerary
    city = st.session_state.city
    days = st.session_state.days
    currency_symbol = st.session_state.get("currency_symbol", "₹")
    is_saved = st.session_state.get("is_saved_trip", False)

    hotels = st.session_state.get("hotels", [])
    restaurants = st.session_state.get("restaurants", [])
    if isinstance(hotels, dict):
        hotels = hotels.get("hotels", [])
    if isinstance(restaurants, dict):
        restaurants = restaurants.get("restaurants", [])
    if not isinstance(hotels, list):
        hotels = []
    if not isinstance(restaurants, list):
        restaurants = []

    if "feedback_given" not in st.session_state:
        st.session_state.feedback_given = {}
    if "replan_triggered" not in st.session_state:
        st.session_state.replan_triggered = False
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "timeline"

    weather_forecast = st.session_state.get("weather_forecast", [])

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"🗺️ Your {days}-Day {city} Itinerary")
    with col2:
        if not is_saved:
            if st.button("💾 Save Trip", use_container_width=True,
                        key="itinerary_save"):
                save_current_trip()
                st.session_state.is_saved_trip = True
                st.rerun()

    col1, col2, col3, col4 = st.columns(4)
    views = [
        ("📋 Timeline", "timeline", col1, "btn_timeline"),
        ("🗺️ Map", "map", col2, "btn_map"),
        ("💰 Budget", "budget", col3, "btn_budget"),
        ("📝 Notes", "notes", col4, "btn_notes"),
    ]
    for label, mode, col, key in views:
        with col:
            if st.button(
                label,
                type="primary" if st.session_state.view_mode == mode
                else "secondary",
                use_container_width=True,
                key=key
            ):
                st.session_state.view_mode = mode
                st.rerun()

    has_dislikes = any(
        v == "down" for v in st.session_state.feedback_given.values()
    )
    if has_dislikes:
        dislike_count = sum(
            1 for v in st.session_state.feedback_given.values()
            if v == "down"
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            st.warning(f"🚫 {dislike_count} spot(s) marked for replacement")
        with col2:
            if st.button("🔄 Replan", type="primary",
                        use_container_width=True, key="replan_btn"):
                st.session_state.replan_triggered = True
                st.rerun()

    st.divider()

    if st.session_state.view_mode == "budget":
        show_budget_tab()
    elif st.session_state.view_mode == "notes":
        show_notes_section()
    elif st.session_state.view_mode == "map":
        st.markdown(f"### 📍 {city} — Your route")
        show_map_from_timed(itinerary, city)
        st.divider()
        show_timed_timeline(itinerary)
    else:
        show_timed_timeline(itinerary)
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
            cols = st.columns(min(len(collab_recs), 3))
            for col, rec in zip(cols, collab_recs):
                with col:
                    st.markdown(f"**{rec['name']}**")
                    st.caption(
                        f"{rec['category']} | ⭐ {rec['rating']}"
                    )

    if st.session_state.replan_triggered:
        st.session_state.replan_triggered = False
        disliked_ids = [
            sid for sid, d in st.session_state.feedback_given.items()
            if d == "down"
        ]
        with st.spinner("Replanning..."):
            result = smart_replan(
                username=st.session_state.username,
                city=city,
                budget_per_day_usd=st.session_state.get("budget_usd", 50),
                days=days,
                current_itinerary=itinerary,
                locked_spot_ids=[],
                disliked_spot_ids=disliked_ids
            )
        if "itinerary" in result:
            st.session_state.itinerary = result["itinerary"]
            st.session_state.feedback_given = {}
            st.rerun()
        else:
            st.error("Replan failed. Try again.")


def show_map_from_timed(itinerary, city):
    flat_itinerary = {}
    time_labels = ["Morning", "Afternoon", "Evening"]
    for day_num, slots in itinerary.items():
        flat_itinerary[str(day_num)] = {}
        if isinstance(slots, list):
            li = 0
            for slot in slots:
                if isinstance(slot, dict):
                    spot = slot.get("spot", {})
                    if spot and li < 3:
                        flat_itinerary[str(day_num)][time_labels[li]] = spot
                        li += 1
        elif isinstance(slots, dict):
            flat_itinerary[str(day_num)] = slots
    show_map(flat_itinerary, city)


def show_timed_timeline(itinerary):
    if not itinerary:
        st.info("No itinerary data found.")
        return

    for day_num in sorted(itinerary.keys(), key=lambda x: int(x)):
        slots = itinerary[day_num]
        st.markdown(f"## 📅 Day {day_num}")

        if not slots:
            st.info("No spots planned for this day.")
            st.divider()
            continue

        if isinstance(slots, list):
            for i, slot in enumerate(slots):
                if not isinstance(slot, dict):
                    continue
                spot = slot.get("spot")
                if not spot or not isinstance(spot, dict):
                    continue

                start_time = slot.get("start_time", "")
                end_time = slot.get("end_time", "")
                duration = slot.get("duration_hours", 2.0)
                transport_label = slot.get("transport_label")
                transport_mode = slot.get("transport_mode")

                if i > 0 and transport_label:
                    t1, t2, t3 = st.columns([2, 1, 12])
                    with t2:
                        st.markdown(
                            "<div style='text-align:center; "
                            "color:#aaa; font-size:14px; "
                            "line-height:0.8; padding:2px 0'>│</div>",
                            unsafe_allow_html=True
                        )
                    with t3:
                        st.markdown(
                            f"<div style='background:#F0F0F0; color:#666; "
                            f"font-size:11px; padding:3px 12px; border-radius:12px; "
                            f"display:inline-block; margin:3px 0 5px'>"
                            f"🕒 {transport_label}</div>",
                            unsafe_allow_html=True
                        )

                col_time, col_dot, col_content = st.columns([2, 1, 12])

                with col_time:
                    st.markdown(
                        f"<div style='text-align:right; "
                        f"padding-top:8px; font-size:13px; opacity:0.7'>"
                        f"<b>{start_time}</b><br>"
                        f"<span style='font-size:11px'>"
                        f"to {end_time}</span></div>",
                        unsafe_allow_html=True
                    )

                with col_dot:
                    st.markdown(
                        "<div style='text-align:center; "
                        "padding-top:8px'>🔵</div>",
                        unsafe_allow_html=True
                    )
                    if i < len(slots) - 1:
                        st.markdown(
                            "<div style='text-align:center; "
                            "color:#1D9E75; line-height:1.6; "
                            "font-size:16px'>│<br>│</div>",
                            unsafe_allow_html=True
                        )

                with col_content:
                    render_spot_card(day_num, i, spot, duration)

        elif isinstance(slots, dict):
            time_order = ["Morning", "Afternoon", "Evening"]
            time_icons = {
                "Morning": "🌅", "Afternoon": "☀️", "Evening": "🌆"
            }
            slot_items = [
                (t, slots[t]) for t in time_order
                if t in slots and slots[t]
            ]
            for i, (time_slot, spot) in enumerate(slot_items):
                if not isinstance(spot, dict):
                    continue
                col_time, col_dot, col_content = st.columns([2, 1, 12])
                with col_time:
                    st.markdown(
                        f"<div style='text-align:right; padding-top:8px;"
                        f" font-size:13px; opacity:0.7'>"
                        f"<b>{time_icons.get(time_slot, '')} "
                        f"{time_slot}</b></div>",
                        unsafe_allow_html=True
                    )
                with col_dot:
                    st.markdown(
                        "<div style='text-align:center; "
                        "padding-top:8px'>🔵</div>",
                        unsafe_allow_html=True
                    )
                    if i < len(slot_items) - 1:
                        st.markdown(
                            "<div style='text-align:center; "
                            "color:#1D9E75; line-height:1.6; "
                            "font-size:16px'>│<br>│</div>",
                            unsafe_allow_html=True
                        )
                with col_content:
                    render_spot_card(
                        day_num, i, spot,
                        spot.get("duration_hours", 2.0)
                    )

        st.divider()

def _get_hour_from_time(time_str):
    try:
        is_pm = "PM" in time_str
        h = int(time_str.replace(" AM", "").replace(
            " PM", ""
        ).split(":")[0])
        if is_pm and h != 12:
            h += 12
        if not is_pm and h == 12:
            h = 0
        return h
    except:
        return 9


def _show_meal_slot(meal_type, last_spot, restaurants,
                   after_time, currency_symbol="₹"):
    meal_icons = {
        "breakfast": "🌅 Breakfast",
        "lunch": "🍽️ Lunch",
        "dinner": "🌙 Dinner"
    }
    label = meal_icons.get(meal_type, "🍽️ Meal")

    spot_lat = None
    spot_lon = None
    if isinstance(last_spot, dict):
        spot_lat = last_spot.get("latitude")
        spot_lon = last_spot.get("longitude")

    nearby = _get_nearby_restaurant(
        restaurants, spot_lat, spot_lon, meal_type
    )

    t1, t2, t3 = st.columns([2, 1, 12])
    with t2:
        st.markdown(
            "<div style='text-align:center; color:#aaa; "
            "font-size:14px; line-height:0.8; padding:2px 0'>│</div>",
            unsafe_allow_html=True
        )
    with t3:
        if nearby:
            food_type = nearby.get("food_type", "veg")
            fe = "🥦" if food_type == "veg" else "🍖"
            price = nearby.get("price_per_meal_local", 0)
            maps_url = nearby.get(
                "google_maps_url",
                f"https://maps.google.com/?q={nearby.get('name', '')}"
            )
            st.markdown(
                f"<div style='background:#FFF8E1; color:#5D4037; "
                f"padding:6px 12px; border-radius:10px; "
                f"display:inline-block; margin:4px 0; font-size:12px'>"
                f"🍽️ <b>{label}</b> — "
                f"{fe} {nearby.get('name', '')} "
                f"({nearby.get('cuisine', '')}) | "
                f"{currency_symbol}{price:.0f}/meal | "
                f"<a href='{maps_url}' target='_blank' "
                f"style='color:#1D9E75'>📍 Maps</a>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background:#FFF8E1; color:#5D4037; "
                f"padding:6px 12px; border-radius:10px; "
                f"display:inline-block; margin:4px 0; font-size:12px'>"
                f"🍽️ <b>{label}</b> — "
                f"Find a local restaurant nearby"
                f"</div>",
                unsafe_allow_html=True
            )

    t1, t2, t3 = st.columns([2, 1, 12])
    with t2:
        st.markdown(
            "<div style='text-align:center; color:#aaa; "
            "font-size:14px; line-height:0.8; padding:2px 0'>│</div>",
            unsafe_allow_html=True
        )


def render_spot_card(day, slot_index, spot, duration_hours=2.0):
    if not isinstance(spot, dict):
        return

    spot_id = spot.get("id")
    if spot_id is None:
        return

    spot_id = int(spot_id)
    feedback = st.session_state.feedback_given.get(spot_id)

    cat_icon = CATEGORY_ICONS.get(spot.get("category", ""), "📍")
    rating = spot.get("rating", 0)
    stars = "⭐" * int(round(rating))

    disliked = feedback == "down"
    border_color = "#E24B4A" if disliked else "#e0e0e0"

    st.markdown(
        f"<div style='border-left:4px solid {border_color}; "
        f"padding-left:12px; margin-bottom:4px'>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown(f"**{spot.get('name', '')}**")
        st.caption(
            f"{cat_icon} {spot.get('category', '')} | "
            f"{stars} {rating} | "
            f"📝 {spot.get('description', '')}"
        )
    with col2:
        if st.button(
            "❌" if disliked else "👎",
            key=f"down_{day}_{slot_index}_{spot_id}",
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


def show_notes_section():
    trip_id = st.session_state.get("current_trip_id")
    if not trip_id:
        st.info("Save your trip first to add notes.")
        return

    st.markdown("### 📝 Trip Notes")
    st.caption("Keep important info, reminders and booking details here")

    notes_key = f"trip_notes_{trip_id}"
    if notes_key not in st.session_state:
        st.session_state[notes_key] = get_trip_notes(trip_id)

    notes = st.session_state[notes_key]

    st.markdown("#### ➕ Add New Note")
    col1, col2 = st.columns([1, 2])
    with col1:
        new_title = st.text_input("Title",
                                  placeholder="e.g. Hotel Booking",
                                  key="new_note_title")
    with col2:
        new_content = st.text_area(
            "Content",
            placeholder="e.g. Zostel Mumbai — Confirmation #12345",
            height=80,
            key="new_note_content"
        )

    if st.button("➕ Add Note", type="primary", key="add_note_btn"):
        if not new_title.strip():
            st.error("Please give your note a title")
        elif not new_content.strip():
            st.error("Please add some content")
        else:
            result = add_trip_note(
                trip_id, new_title.strip(), new_content.strip()
            )
            if result.get("message") == "Note added":
                st.session_state[notes_key] = get_trip_notes(trip_id)
                st.success("✅ Note added!")
                st.rerun()

    if notes:
        st.divider()
        st.markdown("#### 📋 Your Notes")
        for note in notes:
            with st.expander(
                f"📌 {note['title']} — {str(note['created_at'])[:10]}"
            ):
                st.write(note["content"])
                if st.button("🗑️ Delete", key=f"del_{note['id']}"):
                    result = delete_trip_note(note["id"])
                    if result.get("message") == "Note deleted":
                        st.session_state[notes_key] = get_trip_notes(
                            trip_id
                        )
                        st.rerun()
    else:
        st.info("No notes yet.")


def show_hotels(hotels, currency_symbol):
    if isinstance(hotels, dict):
        hotels = hotels.get("hotels", [])
    if not isinstance(hotels, list):
        hotels = []

    st.markdown("## 🏨 Recommended Stays")
    st.caption(
        "Ranked by proximity to your trip spots. "
        "Note preferred stay in 📝 Notes tab."
    )
    if not hotels:
        st.info("No hotel recommendations available.")
        return

    for hotel in hotels[:5]:
        with st.container():
            st.markdown(
                "<div style='border:1px solid #e0e0e0; "
                "border-radius:12px; padding:16px; margin-bottom:12px'>",
                unsafe_allow_html=True
            )
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                stars = "⭐" * int(round(hotel.get("rating", 0)))
                st.markdown(f"#### {hotel.get('name', '')}")
                st.write(
                    f"{stars} {hotel.get('rating', '')} | "
                    f"🏷️ {hotel.get('type', '')}"
                )
                st.write(f"📍 {hotel.get('neighborhood', '')}")
                st.write(
                    f"👥 Best for: "
                    f"{hotel.get('best_for', 'All travelers')}"
                )
                st.caption(hotel.get("description", ""))
            with col2:
                price = hotel.get("price_per_night_local", 0)
                st.write(f"💰 **{currency_symbol}{price:.0f}/night**")
                st.write(f"🛏️ {hotel.get('bedrooms', 1)} bedroom(s)")
                st.write(
                    f"🏠 {hotel.get('rooms_available', 10)} available"
                )
                st.write(
                    f"📞 "
                    f"{hotel.get('contact_number', 'Contact directly')}"
                )
                amenities = hotel.get("amenities", "")
                if amenities:
                    tags = amenities.split(", ")
                    st.caption(
                        " · ".join([f"✓ {t}" for t in tags[:4]])
                    )
            with col3:
                if hotel.get("why_recommend"):
                    st.caption(f"💡 {hotel['why_recommend']}")
                st.markdown(
                    f"[📍 Maps]({hotel.get('google_maps_url', '#')})"
                )
            st.markdown("</div>", unsafe_allow_html=True)


def show_restaurants(restaurants, currency_symbol):
    if isinstance(restaurants, dict):
        restaurants = restaurants.get("restaurants", [])
    if not isinstance(restaurants, list):
        restaurants = []

    st.markdown("## 🍽️ Recommended Restaurants")
    if not restaurants:
        st.info("No restaurant recommendations available.")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Ranked by proximity and rating.")
    with col2:
        food_filter = st.radio(
            "Filter",
            ["all", "veg", "non-veg"],
            format_func=lambda x: "All" if x == "all"
            else "🥦 Veg" if x == "veg" else "🍖 Non-veg",
            key="food_filter_radio",
            horizontal=True,
            label_visibility="collapsed"
        )

    filtered = (restaurants if food_filter == "all"
                else [r for r in restaurants
                      if r.get("food_type") == food_filter])

    if not filtered:
        st.info(f"No {food_filter} restaurants found. Try 'All'.")
        return

    for rest in filtered[:5]:
        ft = rest.get("food_type", "veg")
        fc = "#2E7D32" if ft == "veg" else "#E65100"
        fl = "🥦 Vegetarian" if ft == "veg" else "🍖 Non-Vegetarian"
        rating = rest.get("rating", 0)
        stars = "⭐" * int(round(rating))

        with st.container():
            st.markdown(
                "<div style='border:1px solid #e0e0e0; "
                "border-radius:12px; padding:16px; margin-bottom:12px'>",
                unsafe_allow_html=True
            )
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"#### {rest.get('name', '')}")
                st.write(
                    f"{stars} {rating} | 🍴 {rest.get('cuisine', '')}"
                )
                nearest_day = rest.get("nearest_day_label", "")
                if nearest_day:
                    st.caption(f"📍 {nearest_day}")   
                st.markdown(
                    f"<span style='background:{fc}; color:white; "
                    f"padding:2px 8px; border-radius:12px; "
                    f"font-size:12px'>{fl}</span>",
                    unsafe_allow_html=True
                )
                st.markdown("<br>", unsafe_allow_html=True)
                st.caption(rest.get("description", ""))
            with col2:
                price = rest.get("price_per_meal_local", 0)
                st.write(f"💰 **{currency_symbol}{price:.0f}/meal**")
                st.write(f"📍 {rest.get('neighborhood', '')}")
                st.write(
                    f"⭐ Famous for: "
                    f"{rest.get('best_meal', 'Chef special')}"
                )
                st.write(f"🕐 {rest.get('best_time', 'Open daily')}")
                crowd = rest.get("crowd_level", "Moderate")
                ce = ("🔴" if "busy" in crowd.lower() or
                      "packed" in crowd.lower()
                      else "🟡" if "moderate" in crowd.lower()
                      else "🟢")
                st.write(f"{ce} {crowd}")
            with col3:
                if rest.get("why_recommend"):
                    st.caption(f"💡 {rest['why_recommend']}")
                st.markdown(
                    f"[📍 Maps]({rest.get('google_maps_url', '#')})"
                )
            st.markdown("</div>", unsafe_allow_html=True)


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
        hotel_type="Hotel",
        bedrooms=1,
        food_type=st.session_state.get("trip_food_type_saved", "veg"),
        itinerary_data=st.session_state.itinerary,
        hotel_data={"hotels": st.session_state.get("hotels", [])},
        restaurant_data={
            "restaurants": st.session_state.get("restaurants", [])
        }
    )
    if "trip_id" in result:
        st.session_state.current_trip_id = result["trip_id"]
        st.session_state.current_trip_notes = ""
        st.success(f"✅ Trip saved as '{result.get('trip_name')}'!")
    else:
        st.error("Could not save trip")
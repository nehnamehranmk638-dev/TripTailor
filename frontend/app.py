import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.api import create_user, generate_itinerary, submit_feedback, smart_replan

st.set_page_config(
    page_title="TripTailor",
    page_icon="🗺️",
    layout="wide"
)

if "username" not in st.session_state:
    st.session_state.username = None
if "itinerary" not in st.session_state:
    st.session_state.itinerary = None
if "city" not in st.session_state:
    st.session_state.city = None
if "budget" not in st.session_state:
    st.session_state.budget = 50
if "days" not in st.session_state:
    st.session_state.days = 3
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}
if "replan_triggered" not in st.session_state:
    st.session_state.replan_triggered = False

TIME_ICONS = {
    "Morning": "🌅",
    "Afternoon": "☀️",
    "Evening": "🌆"
}

CATEGORY_ICONS = {
    "Culture": "🏛️",
    "Food": "🍜",
    "Shopping": "🛍️",
    "Nature": "🌿",
    "Art": "🎨",
    "Nightlife": "🎶"
}

def login_section():
    st.title("🗺️ TripTailor")
    st.subheader("Your AI-powered personal travel planner")
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Welcome! Enter your name to start")
        username = st.text_input("Your name", placeholder="e.g. Nehna")
        if st.button("Start Planning →", type="primary", use_container_width=True):
            if username.strip() == "":
                st.error("Please enter your name first")
            else:
                create_user(username.strip())
                st.session_state.username = username.strip()
                st.rerun()

def sidebar_controls():
    with st.sidebar:
        st.markdown(f"### 👋 Hey, {st.session_state.username}!")
        st.divider()
        st.markdown("### 🌍 Plan your trip")

        city = st.selectbox(
            "Destination city",
            ["Mumbai", "Jaipur", "Agra", "Mysore"],
            index=["Mumbai", "Jaipur", "Agra", "Mysore"].index(st.session_state.city)
            if st.session_state.city else 0
        )

        budget = st.slider(
            "Daily budget (USD)",
            min_value=10,
            max_value=200,
            value=st.session_state.budget,
            step=5
        )

        days = st.selectbox(
            "Trip duration",
            [1, 2, 3, 4, 5],
            index=2
        )

        st.divider()

        if st.button("✨ Generate My Perfect Itinerary", type="primary", use_container_width=True):
            with st.spinner("Building your perfect itinerary..."):
                result = generate_itinerary(
                    st.session_state.username, city, budget, days
                )
                if "itinerary" in result:
                    st.session_state.itinerary = result["itinerary"]
                    st.session_state.city = city
                    st.session_state.budget = budget
                    st.session_state.days = days
                    st.session_state.feedback_given = {}
                    st.session_state.replan_triggered = False
                    st.rerun()
                else:
                    st.error("Something went wrong. Try again.")

        has_dislikes = any(
            v == "down" for v in st.session_state.feedback_given.values()
        )

        if has_dislikes:
            st.divider()
            dislike_count = sum(
                1 for v in st.session_state.feedback_given.values()
                if v == "down"
            )
            st.warning(f"👎 {dislike_count} spot(s) marked as not for you")
            if st.button("🔄 Replan My Trip", use_container_width=True, key="sidebar_replan"):
                st.session_state.replan_triggered = True
                st.rerun()

        st.divider()
        st.markdown("### 🧠 Your preferences")
        st.caption("Updates as you give feedback")

        if st.session_state.feedback_given:
            like_count = sum(
                1 for v in st.session_state.feedback_given.values()
                if v == "up"
            )
            dislike_count = sum(
                1 for v in st.session_state.feedback_given.values()
                if v == "down"
            )
            if like_count > 0:
                st.success(f"❤️ {like_count} spot(s) locked in")
            if dislike_count > 0:
                st.error(f"🚫 {dislike_count} spot(s) will be replaced")
        else:
            st.caption("No feedback yet")

def render_spot_card(day, time_slot, spot):
    if spot is None:
        st.markdown(f"**{TIME_ICONS.get(time_slot, '')} {time_slot}:** No spot available")
        return

    spot_id = int(spot["id"])
    feedback = st.session_state.feedback_given.get(spot_id)

    cat_icon = CATEGORY_ICONS.get(spot["category"], "📍")
    stars = "⭐" * int(round(spot["rating"]))
    cost_str = "Free" if spot["cost_usd"] == 0 else f"${spot['cost_usd']}"

    with st.container():
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(
                f"{TIME_ICONS.get(time_slot, '')} **{time_slot}: {spot['name']}**"
            )
            st.caption(
                f"{cat_icon} {spot['category']}  |  💰 {cost_str}  |  {stars} {spot['rating']}  |  📝 {spot['description']}"
            )
        with col2:
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                liked = feedback == "up"
                if st.button(
                    "✅" if liked else "👍",
                    key=f"up_{day}_{time_slot}_{spot_id}",
                    help="Click to like — click again to undo"
                ):
                    if liked:
                        del st.session_state.feedback_given[spot_id]
                    else:
                        submit_feedback(st.session_state.username, spot_id, "up")
                        st.session_state.feedback_given[spot_id] = "up"
                    st.rerun()
            with btn_col2:
                disliked = feedback == "down"
                if st.button(
                    "❌" if disliked else "👎",
                    key=f"down_{day}_{time_slot}_{spot_id}",
                    help="Click to dislike — click again to undo"
                ):
                    if disliked:
                        del st.session_state.feedback_given[spot_id]
                    else:
                        submit_feedback(st.session_state.username, spot_id, "down")
                        st.session_state.feedback_given[spot_id] = "down"
                    st.rerun()

def itinerary_section():
    st.title(f"🗺️ Your {st.session_state.days}-Day {st.session_state.city} Itinerary")
    st.caption(f"Daily budget: ${st.session_state.budget} | 👍 locks a spot in place | 👎 replaces only that spot")
    st.divider()

    itinerary = st.session_state.itinerary

    for day_num in sorted(itinerary.keys(), key=lambda x: int(x)):
        st.markdown(f"## 📅 Day {day_num}")
        day_data = itinerary[day_num]

        for time_slot in ["Morning", "Afternoon", "Evening"]:
            spot = day_data.get(time_slot)
            render_spot_card(day_num, time_slot, spot)

        st.divider()

    if st.session_state.replan_triggered:
        st.session_state.replan_triggered = False

        liked_ids = [sid for sid, d in st.session_state.feedback_given.items()
                    if d == "up"]
        disliked_ids = [sid for sid, d in st.session_state.feedback_given.items()
                       if d == "down"]

        with st.spinner("Replanning only the spots you disliked..."):
            result = smart_replan(
                username=st.session_state.username,
                city=st.session_state.city,
                budget_per_day=st.session_state.budget,
                days=st.session_state.days,
                current_itinerary=st.session_state.itinerary,
                locked_spot_ids=liked_ids,
                disliked_spot_ids=disliked_ids
            )
            if "itinerary" in result:
                st.session_state.itinerary = result["itinerary"]
                st.session_state.feedback_given = {}
                st.rerun()
            else:
                st.error("Replan failed. Try again.")

def main():
    if st.session_state.username is None:
        login_section()
    elif st.session_state.itinerary is None:
        sidebar_controls()
        st.title("🗺️ TripTailor")
        st.markdown("### 👈 Choose your destination and hit Generate!")
        st.image("https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800",
                 caption="Your next adventure awaits")
    else:
        sidebar_controls()
        itinerary_section()

main()
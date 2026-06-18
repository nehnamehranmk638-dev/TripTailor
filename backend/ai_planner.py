from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

AVAILABLE_CITIES = [
    "Mumbai", "Jaipur", "Agra", "Mysore", "Delhi",
    "Goa", "Kerala", "Chennai", "Dubai", "Singapore", "Bangkok"
]

def extract_trip_details(user_message: str, user_country: str = "India") -> dict:
    prompt = f"""
You are a travel planning assistant. Extract trip details from the user's message.

Available cities: {', '.join(AVAILABLE_CITIES)}

User message: "{user_message}"
User's home country: {user_country}

Extract and return ONLY a JSON object with these fields:
{{
    "city": "city name from available cities or null",
    "days": number or null,
    "budget_per_day_local": number or null,
    "food_type": "veg" or "non-veg" or null,
    "hotel_type": "Hotel" or "Resort" or "Villa" or null,
    "bedrooms": number or null,
    "special_requirements": "any special needs like accessibility, kids, elderly" or null,
    "travel_companions": "solo" or "couple" or "family" or "friends" or null,
    "interests": ["Culture", "Food", "Nature", "Shopping", "Art", "Nightlife"] subset or null,
    "confidence": 0.0 to 1.0
}}

Return ONLY the JSON, no other text.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        return {"error": str(e), "confidence": 0.0}

def generate_trip_name(city: str, days: int, travel_companions: str = None) -> str:
    companion_str = f" with {travel_companions}" if travel_companions else ""
    prompt = f"Generate a creative, exciting trip name for a {days}-day trip to {city}{companion_str}. Return ONLY the name, max 6 words, no quotes."
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except:
        return f"{days}-Day {city} Adventure"

def handle_midtrip_request(
    user_message: str,
    current_itinerary: dict,
    city: str,
    day: int = None,
    chat_history: list = None
) -> dict:
    itinerary_summary = []
    for day_num, slots in current_itinerary.items():
        if isinstance(slots, list):
            for slot in slots:
                if isinstance(slot, dict):
                    spot = slot.get("spot", {})
                    if spot:
                        itinerary_summary.append(
                            f"Day {day_num} {slot.get('start_time', '')}: "
                            f"{spot.get('name', '')} ({spot.get('category', '')})"
                        )

    messages = []

    messages.append({
        "role": "user",
        "content": f"""You are a helpful travel assistant for a trip to {city}.

Current itinerary:
{chr(10).join(itinerary_summary)}

You have memory of the full conversation. Be helpful, friendly and specific."""
    })
    messages.append({
        "role": "assistant",
        "content": "I'm your trip assistant! I can help you modify plans, suggest alternatives, or answer questions about your itinerary."
    })

    if chat_history:
        for msg in chat_history[:-1]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    messages.append({"role": "user", "content": user_message})

    prompt_suffix = """

Based on the conversation and current itinerary, return ONLY a JSON object:
{
    "action": "replace_spot" or "add_info" or "general_advice",
    "day": specific day number as integer if mentioned (e.g. 2 for "Day 2") or null,
    "time_slot": "Morning" or "Afternoon" or "Evening" or null,
    "reason": "brief reason for change",
    "category_preference": "Culture" or "Food" or "Nature" or "Shopping" or "Art" or "Nightlife" or null,
    "response_message": "friendly conversational response. If suggesting a replacement, mention you found alternatives and they can see them in the suggestion panel.",
    "indoor_preferred": true or false
}

If the user asks to replace, change, swap, remove or modify any spot — set action to "replace_spot".
Return ONLY the JSON, nothing else."""

    messages[-1]["content"] += prompt_suffix

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        return {
            "action": "general_advice",
            "response_message": "I understand. Could you tell me more specifically what you'd like to change?",
            "error": str(e)
        }

def get_spot_insight(spot_name: str, city: str) -> str:
    prompt = f"Give one interesting insider tip about visiting {spot_name} in {city}. Max 2 sentences. Be specific and practical."
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except:
        return ""
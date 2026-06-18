import requests
from frontend.config import API_BASE_URL

def signup(username, password, country):
    r = requests.post(f"{API_BASE_URL}/signup",
                     json={"username": username,
                           "password": password,
                           "country": country})
    return r.json()

def login(username, password):
    r = requests.post(f"{API_BASE_URL}/login",
                     json={"username": username,
                           "password": password})
    return r.json()

def get_countries():
    r = requests.get(f"{API_BASE_URL}/countries")
    return r.json().get("countries", [])

def get_cities():
    r = requests.get(f"{API_BASE_URL}/cities")
    return r.json().get("cities", [])

def parse_trip(username, message):
    r = requests.post(f"{API_BASE_URL}/parse-trip",
                     json={"username": username, "message": message})
    return r.json()

def generate_itinerary(username, city, budget_per_day_usd, days,
                      food_type=None, hotel_type=None, bedrooms=1):
    r = requests.post(f"{API_BASE_URL}/generate-itinerary", json={
        "username": username,
        "city": city,
        "budget_per_day_usd": budget_per_day_usd,
        "days": days,
        "food_type": food_type,
        "hotel_type": hotel_type,
        "bedrooms": bedrooms
    })
    return r.json()

def submit_feedback(username, spot_id, direction):
    r = requests.post(f"{API_BASE_URL}/feedback", json={
        "username": username,
        "spot_id": spot_id,
        "direction": direction
    })
    return r.json()

def smart_replan(username, city, budget_per_day_usd, days,
                current_itinerary, locked_spot_ids, disliked_spot_ids):
    r = requests.post(f"{API_BASE_URL}/smart-replan", json={
        "username": username,
        "city": city,
        "budget_per_day_usd": budget_per_day_usd,
        "days": days,
        "current_itinerary": current_itinerary,
        "locked_spot_ids": locked_spot_ids,
        "disliked_spot_ids": disliked_spot_ids
    })
    return r.json()

def midtrip_assist(username, message, city, current_itinerary,
                  day=None, chat_history=None):
    r = requests.post(f"{API_BASE_URL}/midtrip-assist", json={
        "username": username,
        "message": message,
        "city": city,
        "current_itinerary": current_itinerary,
        "day": day,
        "chat_history": chat_history or []
    })
    return r.json()

def save_trip(username, city, country, days, budget_per_day_usd,
             budget_per_day_local, currency_code, currency_symbol,
             hotel_type, bedrooms, food_type, itinerary_data,
             hotel_data, restaurant_data, trip_name=None):
    r = requests.post(f"{API_BASE_URL}/save-trip", json={
        "username": username,
        "city": city,
        "country": country,
        "days": days,
        "budget_per_day_usd": budget_per_day_usd,
        "budget_per_day_local": budget_per_day_local,
        "currency_code": currency_code,
        "currency_symbol": currency_symbol,
        "hotel_type": hotel_type,
        "bedrooms": bedrooms,
        "food_type": food_type,
        "itinerary_data": itinerary_data,
        "hotel_data": hotel_data,
        "restaurant_data": restaurant_data,
        "trip_name": trip_name
    })
    return r.json()

def get_dashboard(username):
    r = requests.get(f"{API_BASE_URL}/dashboard/{username}")
    return r.json()

def delete_trip(trip_id, username):
    r = requests.delete(
        f"{API_BASE_URL}/trip/{trip_id}",
        params={"username": username}
    )
    return r.json()

def save_notes(trip_id, username, notes):
    r = requests.put(
        f"{API_BASE_URL}/trip/{trip_id}/notes",
        params={"username": username, "notes": notes}
    )
    return r.json()

def get_trip_notes(trip_id):
    r = requests.get(f"{API_BASE_URL}/trip/{trip_id}/trip-notes")
    return r.json().get("notes", [])

def add_trip_note(trip_id, title, content):
    r = requests.post(
        f"{API_BASE_URL}/trip/{trip_id}/trip-notes",
        params={"title": title, "content": content}
    )
    return r.json()

def delete_trip_note(note_id):
    r = requests.delete(f"{API_BASE_URL}/trip-note/{note_id}")
    return r.json()

def get_trip_chat(trip_id):
    r = requests.get(f"{API_BASE_URL}/trip/{trip_id}/chat")
    return r.json().get("messages", [])

def save_trip_chat(trip_id, role, content):
    r = requests.post(
        f"{API_BASE_URL}/trip/{trip_id}/chat",
        params={"role": role, "content": content}
    )
    return r.json()

def clear_trip_chat(trip_id):
    r = requests.delete(f"{API_BASE_URL}/trip/{trip_id}/chat")
    return r.json()

def update_trip_itinerary(trip_id, username, itinerary_data):
    r = requests.put(
        f"{API_BASE_URL}/trip/{trip_id}/itinerary",
        params={"username": username},
        json=itinerary_data
    )
    return r.json()

def get_weather(city, days):
    try:
        r = requests.get(
            f"{API_BASE_URL}/weather/{city}/{days}",
            timeout=5
        )
        return r.json()
    except:
        return {"forecast": [], "available": False}

def get_local_tip(spot_id):
    try:
        r = requests.get(
            f"{API_BASE_URL}/local-tip/{spot_id}",
            timeout=8
        )
        return r.json().get("tip", "")
    except:
        return ""
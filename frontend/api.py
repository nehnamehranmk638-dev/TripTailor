import requests
from frontend.config import API_BASE_URL

def create_user(username):
    response = requests.post(f"{API_BASE_URL}/users/create",
                            json={"username": username})
    return response.json()

def generate_itinerary(username, city, budget_per_day, days):
    response = requests.post(f"{API_BASE_URL}/generate-itinerary", json={
        "username": username,
        "city": city,
        "budget_per_day": budget_per_day,
        "days": days
    })
    return response.json()

def submit_feedback(username, spot_id, direction):
    response = requests.post(f"{API_BASE_URL}/feedback", json={
        "username": username,
        "spot_id": spot_id,
        "direction": direction
    })
    return response.json()

def smart_replan(username, city, budget_per_day, days,
                 current_itinerary, locked_spot_ids, disliked_spot_ids):
    response = requests.post(f"{API_BASE_URL}/smart-replan", json={
        "username": username,
        "city": city,
        "budget_per_day": budget_per_day,
        "days": days,
        "current_itinerary": current_itinerary,
        "locked_spot_ids": locked_spot_ids,
        "disliked_spot_ids": disliked_spot_ids
    })
    return response.json()
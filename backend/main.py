from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.database import SessionLocal
from backend.models import (SignupRequest, LoginRequest, ItineraryRequest,
                            FeedbackRequest, SmartReplanRequest,
                            NaturalLanguageRequest, MidTripRequest,
                            SaveTripRequest)
from backend.ranker import rank_spots, build_timed_itinerary, smart_replan
from backend.auth import hash_password, verify_password
from backend.currency import (get_currency_for_country, convert_to_local,
                              get_all_countries)
from backend.ml_engine import (update_category_weights, get_travel_personality,
                               get_collaborative_recommendations)
from backend.ai_planner import (extract_trip_details, generate_trip_name,
                                handle_midtrip_request, get_spot_insight)
from backend.weather import get_weather_forecast
from sqlalchemy import text
import json
import math

app = FastAPI(title="TripTailor API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

def get_user(db, username):
    return db.execute(
        text("SELECT * FROM users WHERE username = :u"),
        {"u": username}
    ).fetchone()

def spot_to_dict(spot, usd_rate=1.0, currency_symbol="$"):
    cost_local = convert_to_local(float(spot.cost_usd), usd_rate)
    return {
        "id": spot.id,
        "name": spot.name,
        "category": spot.category,
        "cost_usd": float(spot.cost_usd),
        "cost_local": cost_local,
        "currency_symbol": currency_symbol,
        "rating": float(spot.rating),
        "description": spot.description,
        "duration_hours": float(spot.duration_hours) if spot.duration_hours else 2.0,
        "time_of_day": spot.time_of_day,
        "latitude": float(spot.latitude) if spot.latitude else None,
        "longitude": float(spot.longitude) if spot.longitude else None,
        "opening_time": spot.opening_time or "09:00",
        "closing_time": spot.closing_time or "18:00",
        "closed_day": spot.closed_day or "",
        "afternoon_break": spot.afternoon_break or False,
        "local_tip": spot.local_tip or ""
    }

def haversine(lat1, lon1, lat2, lon2):
    if not all([lat1, lon1, lat2, lon2]):
        return 999
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_center(spot_list):
    lats, lons = [], []
    for s in spot_list:
        if hasattr(s, 'latitude'):
            if s.latitude:
                lats.append(float(s.latitude))
                lons.append(float(s.longitude))
        elif isinstance(s, dict):
            if s.get('latitude'):
                lats.append(float(s['latitude']))
                lons.append(float(s['longitude']))
    if not lats:
        return None, None
    return sum(lats)/len(lats), sum(lons)/len(lons)

@app.get("/")
def root():
    return {"message": "TripTailor API v2.0 running"}

@app.post("/signup")
def signup(request: SignupRequest):
    db = SessionLocal()
    try:
        existing = get_user(db, request.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        currency_info = get_currency_for_country(request.country)
        hashed = hash_password(request.password)
        db.execute(
            text("""INSERT INTO users
                    (username, password_hash, country, currency_code, currency_symbol)
                    VALUES (:u, :p, :c, :cc, :cs)"""),
            {"u": request.username, "p": hashed, "c": request.country,
             "cc": currency_info["currency_code"],
             "cs": currency_info["currency_symbol"]}
        )
        db.commit()
        return {"message": "Account created", "username": request.username,
                "currency": currency_info}
    finally:
        db.close()

@app.post("/login")
def login(request: LoginRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=401, detail="Username not found")
        if not user.password_hash:
            raise HTTPException(status_code=401, detail="Please sign up first")
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Wrong password")
        personality = get_travel_personality(dict(user.category_weights))
        return {
            "message": "Login successful",
            "username": request.username,
            "country": user.country,
            "currency_code": user.currency_code,
            "currency_symbol": user.currency_symbol,
            "travel_personality": personality,
            "category_weights": dict(user.category_weights)
        }
    finally:
        db.close()

@app.get("/countries")
def get_countries():
    return {"countries": get_all_countries()}

@app.get("/cities")
def get_cities():
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT DISTINCT city, country FROM spots ORDER BY city")
        ).fetchall()
        return {"cities": [{"city": r.city, "country": r.country}
                           for r in result]}
    finally:
        db.close()

@app.post("/parse-trip")
def parse_trip(request: NaturalLanguageRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = extract_trip_details(
            request.message, user.country or "India"
        )
        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail="Could not understand the trip request"
            )
        return result
    finally:
        db.close()

@app.post("/generate-itinerary")
def generate_itinerary(request: ItineraryRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        currency_info = get_currency_for_country(user.country or "India")
        usd_rate = currency_info["usd_rate"]
        currency_symbol = currency_info["currency_symbol"]
        category_weights = dict(user.category_weights)

        spots = db.execute(
            text("SELECT * FROM spots WHERE LOWER(city) = LOWER(:city)"),
            {"city": request.city}
        ).fetchall()

        if not spots:
            raise HTTPException(
                status_code=404, detail="No spots found for this city"
            )

        ranked = rank_spots(
            spots, category_weights, request.budget_per_day_usd
        )

        if not ranked:
            ranked = rank_spots(spots, category_weights, 99999)

        timed_itinerary = build_timed_itinerary(ranked, request.days)

        result = {}
        total_cost_usd = 0
        all_trip_spots = []

        for day, slots in timed_itinerary.items():
            result[str(day)] = []
            for slot in slots:
                spot = slot["spot"]
                cost_local = convert_to_local(
                    float(spot.cost_usd), usd_rate
                )
                total_cost_usd += float(spot.cost_usd)
                all_trip_spots.append(spot)

                slot_dict = {
                    "start_time": slot["start_time"],
                    "end_time": slot["end_time"],
                    "duration_hours": slot["duration_hours"],
                    "time_label": slot["time_label"],
                    "spot": {
                        "id": spot.id,
                        "name": spot.name,
                        "category": spot.category,
                        "cost_usd": float(spot.cost_usd),
                        "cost_local": cost_local,
                        "currency_symbol": currency_symbol,
                        "rating": float(spot.rating),
                        "description": spot.description,
                        "duration_hours": float(
                            spot.duration_hours or 2.0
                        ),
                        "latitude": float(spot.latitude)
                        if spot.latitude else None,
                        "longitude": float(spot.longitude)
                        if spot.longitude else None,
                        "opening_time": spot.opening_time or "09:00",
                        "closing_time": spot.closing_time or "18:00",
                        "closed_day": spot.closed_day or "",
                        "afternoon_break": spot.afternoon_break or False,
                        "local_tip": spot.local_tip or ""
                    }
                }
                result[str(day)].append(slot_dict)

        center_lat, center_lon = get_center(all_trip_spots)

        all_hotels = db.execute(
            text("""SELECT * FROM hotels
                    WHERE LOWER(city) = LOWER(:city)
                    ORDER BY rating DESC"""),
            {"city": request.city}
        ).fetchall()

        hotels_with_distance = []
        for h in all_hotels:
            dist = haversine(
                center_lat, center_lon,
                float(h.latitude) if h.latitude else None,
                float(h.longitude) if h.longitude else None
            )
            if dist < 999:
                walk_min = int(dist * 12)
                if walk_min < 10:
                    proximity = f"{walk_min} min walk from your trip spots"
                elif walk_min < 30:
                    proximity = f"{int(dist * 1000)}m from your trip spots"
                else:
                    proximity = f"{dist:.1f} km from your trip spots"
            else:
                proximity = f"Located in {h.neighborhood or request.city}"

            if float(h.price_per_night_usd) <= request.budget_per_day_usd * 2:
                budget_note = "Within your budget"
            elif float(h.price_per_night_usd) <= request.budget_per_day_usd * 3:
                budget_note = "Slightly above budget"
            else:
                budget_note = "Premium option"

            why_recommend = f"{proximity} · {budget_note} · ⭐ {h.rating} rated"

            hotels_with_distance.append({
                "id": h.id,
                "name": h.name,
                "type": h.type,
                "neighborhood": h.neighborhood or request.city,
                "bedrooms": h.bedrooms,
                "rooms_available": h.rooms_available or 10,
                "price_per_night_usd": float(h.price_per_night_usd),
                "price_per_night_local": convert_to_local(
                    float(h.price_per_night_usd), usd_rate
                ),
                "currency_symbol": currency_symbol,
                "rating": float(h.rating),
                "amenities": h.amenities,
                "description": h.description,
                "best_for": h.best_for or "All travelers",
                "contact_number": h.contact_number or "Contact directly",
                "google_maps_url": h.google_maps_url or
                    f"https://maps.google.com/?q={h.name}+{request.city}",
                "distance_km": round(dist, 2) if dist < 999 else None,
                "proximity_text": proximity,
                "why_recommend": why_recommend
            })

        hotels_with_distance.sort(
            key=lambda x: (
                x["distance_km"] if x["distance_km"] else 999,
                -x["rating"]
            )
        )

        day_centers = {}
        for day, slots in timed_itinerary.items():
            day_spots = [slot["spot"] for slot in slots]
            if day_spots:
                lats = [float(s.latitude) for s in day_spots if s.latitude]
                lons = [float(s.longitude) for s in day_spots if s.longitude]
                if lats:
                    day_centers[day] = (sum(lats)/len(lats), sum(lons)/len(lons))

        all_restaurants = db.execute(
            text("""SELECT * FROM restaurants
                    WHERE LOWER(city) = LOWER(:city)
                    ORDER BY rating DESC"""),
            {"city": request.city}
        ).fetchall()

        restaurants_data = []
        for r in all_restaurants:
            nearest_day_label = ""
            best_day_dist = float('inf')
            for d, (d_lat, d_lon) in day_centers.items():
                d_dist = haversine(d_lat, d_lon,
                                float(r.latitude) if r.latitude else None,
                                float(r.longitude) if r.longitude else None)
                if d_dist < best_day_dist:
                    best_day_dist = d_dist
                    nearest_day_label = f"Near Day {d} spots"
            dist = haversine(
                center_lat, center_lon,
                float(r.latitude) if r.latitude else None,
                float(r.longitude) if r.longitude else None
            )
            if dist < 999:
                walk_min = int(dist * 12)
                if walk_min < 10:
                    proximity = f"{walk_min} min walk from your spots"
                else:
                    proximity = f"{dist:.1f} km from city center"
            else:
                proximity = f"Located in {r.neighborhood or request.city}"

            why_recommend = (
                f"{proximity} · "
                f"{'🥦 Vegetarian' if r.food_type == 'veg' else '🍖 Non-veg'}"
                f" · ⭐ {r.rating} rated"
            )

            restaurants_data.append({
                "id": r.id,
                "name": r.name,
                "cuisine": r.cuisine,
                "food_type": r.food_type,
                "neighborhood": r.neighborhood or request.city,
                "price_per_meal_usd": float(r.price_per_meal_usd),
                "price_per_meal_local": convert_to_local(
                    float(r.price_per_meal_usd), usd_rate
                ),
                "nearest_day_label": nearest_day_label,
                "currency_symbol": currency_symbol,
                "rating": float(r.rating),
                "description": r.description,
                "best_meal": r.best_meal or "Chef's special",
                "best_time": r.best_time or "Open daily",
                "crowd_level": r.crowd_level or "Moderate",
                "google_maps_url": r.google_maps_url or
                    f"https://maps.google.com/?q={r.name}+{request.city}",
                "distance_km": round(dist, 2) if dist < 999 else None,
                "proximity_text": proximity,
                "why_recommend": why_recommend
            })

        restaurants_data.sort(
            key=lambda x: (
                x["distance_km"] if x["distance_km"] else 999,
                -x["rating"]
            )
        )

        collab_recs = get_collaborative_recommendations(
            request.username, request.city
        )
        personality = get_travel_personality(category_weights)

        db.execute(
            text("UPDATE users SET travel_personality = :p WHERE username = :u"),
            {"p": personality, "u": request.username}
        )
        db.commit()

        weather = get_weather_forecast(request.city, request.days)
        
        return {
            "itinerary": result,
            "city": request.city,
            "days": request.days,
            "total_cost_usd": round(total_cost_usd, 2),
            "total_cost_local": convert_to_local(total_cost_usd, usd_rate),
            "currency_symbol": currency_symbol,
            "hotels": hotels_with_distance,
            "restaurants": restaurants_data,
            "collaborative_recommendations": collab_recs,
            "travel_personality": personality,
            "weather_forecast": weather or []
        }
    finally:
        db.close()

@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        spot = db.execute(
            text("SELECT * FROM spots WHERE id = :id"),
            {"id": request.spot_id}
        ).fetchone()
        if not spot:
            raise HTTPException(status_code=404, detail="Spot not found")
        updated_weights = update_category_weights(
            request.username, spot.category, request.direction
        )
        db.execute(
            text("""INSERT INTO feedback_events (user_id, spot_id, direction)
                    VALUES (:uid, :sid, :dir)"""),
            {"uid": user.id, "sid": request.spot_id,
             "dir": request.direction}
        )
        db.commit()
        personality = get_travel_personality(updated_weights)
        return {
            "message": "Feedback recorded",
            "updated_weights": updated_weights,
            "travel_personality": personality
        }
    finally:
        db.close()

@app.post("/smart-replan")
def smart_replan_endpoint(request: SmartReplanRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        currency_info = get_currency_for_country(user.country or "India")
        category_weights = dict(user.category_weights)

        spots = db.execute(
            text("SELECT * FROM spots WHERE LOWER(city) = LOWER(:city)"),
            {"city": request.city}
        ).fetchall()

        if not spots:
            raise HTTPException(status_code=404, detail="No spots found")

        new_itinerary = smart_replan(
            request.current_itinerary,
            spots,
            category_weights,
            request.budget_per_day_usd,
            request.locked_spot_ids,
            request.disliked_spot_ids
        )

        return {
            "itinerary": new_itinerary,
            "city": request.city,
            "currency_symbol": currency_info["currency_symbol"]
        }
    finally:
        db.close()

@app.post("/midtrip-assist")
def midtrip_assist(request: MidTripRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        currency_info = get_currency_for_country(user.country or "India")
        usd_rate = currency_info["usd_rate"]
        currency_symbol = currency_info["currency_symbol"]

        ai_response = handle_midtrip_request(
            request.message,
            request.current_itinerary,
            request.city,
            request.day,
            request.chat_history
        )

        suggestions = []
        if ai_response.get("action") == "replace_spot":
            category_weights = dict(user.category_weights)
            spots = db.execute(
                text("SELECT * FROM spots WHERE LOWER(city) = LOWER(:city)"),
                {"city": request.city}
            ).fetchall()

            category_pref = ai_response.get("category_preference")
            indoor_pref = ai_response.get("indoor_preferred", False)

            filtered_spots = spots
            if category_pref:
                cat_filtered = [
                    s for s in spots if s.category == category_pref
                ]
                if cat_filtered:
                    filtered_spots = cat_filtered

            ranked = rank_spots(filtered_spots, category_weights, 99999)

            current_ids = set()
            for day_slots in request.current_itinerary.values():
                if isinstance(day_slots, list):
                    for slot in day_slots:
                        if isinstance(slot, dict):
                            spot = slot.get("spot", {})
                            if spot:
                                current_ids.add(spot.get("id"))

            suggestion_spots = [
                s for s in ranked if s.id not in current_ids
            ][:3]

            suggestions = []
            for s in suggestion_spots:
                cost_local = convert_to_local(float(s.cost_usd), usd_rate)
                suggestions.append({
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "cost_usd": float(s.cost_usd),
                    "cost_local": cost_local,
                    "currency_symbol": currency_symbol,
                    "rating": float(s.rating),
                    "description": s.description,
                    "duration_hours": float(s.duration_hours or 2.0),
                    "time_of_day": s.time_of_day,
                    "latitude": float(s.latitude) if s.latitude else None,
                    "longitude": float(s.longitude) if s.longitude else None
                })

        return {
            "ai_response": ai_response,
            "suggestions": suggestions,
            "target_day": ai_response.get("day"),
            "target_time_slot": ai_response.get("time_slot")
        }
    finally:
        db.close()

@app.post("/save-trip")
def save_trip(request: SaveTripRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        db.execute(
            text("""UPDATE trips SET status = 'past'
                    WHERE user_id = :uid AND status = 'active'"""),
            {"uid": user.id}
        )

        trip_name = request.trip_name or generate_trip_name(
            request.city, request.days
        )

        result = db.execute(
            text("""INSERT INTO trips
                    (user_id, city, country, days, budget_per_day_usd,
                     budget_per_day_local, currency_code, currency_symbol,
                     hotel_type, bedrooms, food_type, trip_name)
                    VALUES (:uid, :city, :country, :days, :budget_usd,
                            :budget_local, :cc, :cs, :ht, :br, :ft, :tn)
                    RETURNING id"""),
            {"uid": user.id, "city": request.city,
             "country": request.country, "days": request.days,
             "budget_usd": request.budget_per_day_usd,
             "budget_local": request.budget_per_day_local,
             "cc": request.currency_code, "cs": request.currency_symbol,
             "ht": request.hotel_type, "br": request.bedrooms,
             "ft": request.food_type, "tn": trip_name}
        )
        trip_id = result.fetchone()[0]

        db.execute(
            text("""INSERT INTO trip_itineraries
                    (trip_id, itinerary_data, hotel_data, restaurant_data)
                    VALUES (:tid, :idata, :hdata, :rdata)"""),
            {"tid": trip_id,
             "idata": json.dumps(request.itinerary_data),
             "hdata": json.dumps(request.hotel_data),
             "rdata": json.dumps(request.restaurant_data)}
        )
        db.commit()
        return {"message": "Trip saved", "trip_id": trip_id,
                "trip_name": trip_name}
    finally:
        db.close()

@app.put("/trip/{trip_id}/itinerary")
def update_trip_itinerary(trip_id: int, username: str,
                          itinerary_data: dict):
    db = SessionLocal()
    try:
        user = get_user(db, username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.execute(
            text("""UPDATE trip_itineraries
                    SET itinerary_data = :idata, updated_at = NOW()
                    WHERE trip_id = :tid"""),
            {"idata": json.dumps(itinerary_data), "tid": trip_id}
        )
        db.commit()
        return {"message": "Itinerary updated"}
    finally:
        db.close()

@app.get("/dashboard/{username}")
def get_dashboard(username: str):
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT * FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        trips = db.execute(
            text("""SELECT t.*, ti.itinerary_data, ti.hotel_data,
                    ti.restaurant_data
                    FROM trips t
                    LEFT JOIN trip_itineraries ti ON t.id = ti.trip_id
                    WHERE t.user_id = :uid
                    ORDER BY t.created_at DESC"""),
            {"uid": user.id}
        ).fetchall()

        personality = get_travel_personality(dict(user.category_weights))
        active_trip = None
        past_trips = []

        for trip in trips:
            trip_data = {
                "id": trip.id,
                "trip_name": trip.trip_name,
                "city": trip.city,
                "country": trip.country,
                "days": trip.days,
                "budget_per_day_usd": float(trip.budget_per_day_usd)
                    if trip.budget_per_day_usd else 50,
                "budget_per_day_local": float(trip.budget_per_day_local)
                    if trip.budget_per_day_local else 0,
                "currency_symbol": trip.currency_symbol,
                "hotel_type": trip.hotel_type,
                "food_type": trip.food_type,
                "status": trip.status,
                "created_at": str(trip.created_at),
                "notes": trip.notes or "",
                "itinerary_data": trip.itinerary_data,
                "hotel_data": trip.hotel_data,
                "restaurant_data": trip.restaurant_data
            }
            if trip.status == "active":
                active_trip = trip_data
            else:
                past_trips.append(trip_data)

        return {
            "username": username,
            "country": user.country,
            "currency_symbol": user.currency_symbol,
            "travel_personality": personality,
            "category_weights": dict(user.category_weights),
            "active_trip": active_trip,
            "past_trips": past_trips,
            "total_trips": len(trips)
        }
    finally:
        db.close()

@app.delete("/trip/{trip_id}")
def delete_trip(trip_id: int, username: str):
    db = SessionLocal()
    try:
        user = get_user(db, username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.execute(
            text("DELETE FROM trip_chats WHERE trip_id = :tid"),
            {"tid": trip_id}
        )
        db.execute(
            text("DELETE FROM trip_notes WHERE trip_id = :tid"),
            {"tid": trip_id}
        )
        db.execute(
            text("DELETE FROM trip_itineraries WHERE trip_id = :tid"),
            {"tid": trip_id}
        )
        db.execute(
            text("""DELETE FROM trips WHERE id = :tid
                    AND user_id = :uid"""),
            {"tid": trip_id, "uid": user.id}
        )
        db.commit()
        return {"message": "Trip deleted"}
    finally:
        db.close()

@app.put("/trip/{trip_id}/notes")
def update_notes(trip_id: int, username: str, notes: str):
    db = SessionLocal()
    try:
        user = get_user(db, username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.execute(
            text("""UPDATE trips SET notes = :notes
                    WHERE id = :tid AND user_id = :uid"""),
            {"notes": notes, "tid": trip_id, "uid": user.id}
        )
        db.commit()
        return {"message": "Notes saved"}
    finally:
        db.close()

@app.get("/trip/{trip_id}/trip-notes")
def get_trip_notes(trip_id: int):
    db = SessionLocal()
    try:
        notes = db.execute(
            text("""SELECT id, title, content, created_at
                    FROM trip_notes WHERE trip_id = :tid
                    ORDER BY created_at DESC"""),
            {"tid": trip_id}
        ).fetchall()
        return {"notes": [
            {"id": n.id, "title": n.title,
             "content": n.content, "created_at": str(n.created_at)}
            for n in notes
        ]}
    finally:
        db.close()

@app.post("/trip/{trip_id}/trip-notes")
def add_trip_note(trip_id: int, title: str, content: str):
    db = SessionLocal()
    try:
        result = db.execute(
            text("""INSERT INTO trip_notes (trip_id, title, content)
                    VALUES (:tid, :title, :content)
                    RETURNING id"""),
            {"tid": trip_id, "title": title, "content": content}
        )
        note_id = result.fetchone()[0]
        db.commit()
        return {"message": "Note added", "note_id": note_id}
    finally:
        db.close()

@app.delete("/trip-note/{note_id}")
def delete_trip_note(note_id: int):
    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM trip_notes WHERE id = :nid"),
            {"nid": note_id}
        )
        db.commit()
        return {"message": "Note deleted"}
    finally:
        db.close()

@app.get("/trip/{trip_id}/chat")
def get_chat(trip_id: int):
    db = SessionLocal()
    try:
        messages = db.execute(
            text("""SELECT role, content FROM trip_chats
                    WHERE trip_id = :tid
                    ORDER BY created_at ASC"""),
            {"tid": trip_id}
        ).fetchall()
        return {"messages": [
            {"role": m.role, "content": m.content}
            for m in messages
        ]}
    finally:
        db.close()

@app.post("/trip/{trip_id}/chat")
def save_chat(trip_id: int, role: str, content: str):
    db = SessionLocal()
    try:
        db.execute(
            text("""INSERT INTO trip_chats (trip_id, role, content)
                    VALUES (:tid, :role, :content)"""),
            {"tid": trip_id, "role": role, "content": content}
        )
        db.commit()
        return {"message": "Chat saved"}
    finally:
        db.close()

@app.delete("/trip/{trip_id}/chat")
def clear_chat(trip_id: int):
    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM trip_chats WHERE trip_id = :tid"),
            {"tid": trip_id}
        )
        db.commit()
        return {"message": "Chat cleared"}
    finally:
        db.close()

@app.get("/spot-insight/{spot_name}/{city}")
def spot_insight(spot_name: str, city: str):
    insight = get_spot_insight(spot_name, city)
    return {"insight": insight}

@app.get("/weather/{city}/{days}")
def weather_forecast(city: str, days: int):
    forecast = get_weather_forecast(city, days)
    if not forecast:
        return {"forecast": [], "available": False}
    return {"forecast": forecast, "available": True}

@app.get("/local-tip/{spot_id}")
def get_local_tip_endpoint(spot_id: int):
    db = SessionLocal()
    try:
        spot = db.execute(
            text("SELECT name, city, local_tip FROM spots WHERE id = :id"),
            {"id": spot_id}
        ).fetchone()
        if not spot:
            return {"tip": ""}
        if spot.local_tip:
            return {"tip": spot.local_tip}
        tip = get_spot_insight(spot.name, spot.city)
        db.execute(
            text("UPDATE spots SET local_tip = :tip WHERE id = :id"),
            {"tip": tip, "id": spot_id}
        )
        db.commit()
        return {"tip": tip}
    finally:
        db.close()
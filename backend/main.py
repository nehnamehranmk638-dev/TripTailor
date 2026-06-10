from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.database import SessionLocal
from backend.models import (SignupRequest, LoginRequest, ItineraryRequest,
                            FeedbackRequest, SmartReplanRequest,
                            NaturalLanguageRequest, MidTripRequest,
                            SaveTripRequest)
from backend.ranker import rank_spots, build_itinerary, smart_replan
from backend.auth import hash_password, verify_password
from backend.currency import get_currency_for_country, convert_to_local, get_all_countries
from backend.ml_engine import update_category_weights, get_travel_personality, get_collaborative_recommendations
from backend.ai_planner import extract_trip_details, generate_trip_name, handle_midtrip_request, get_spot_insight
from sqlalchemy import text
import json

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
        "longitude": float(spot.longitude) if spot.longitude else None
    }

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
            text("""INSERT INTO users (username, password_hash, country, currency_code, currency_symbol)
                    VALUES (:u, :p, :c, :cc, :cs)"""),
            {"u": request.username, "p": hashed, "c": request.country,
             "cc": currency_info["currency_code"], "cs": currency_info["currency_symbol"]}
        )
        db.commit()
        return {
            "message": "Account created",
            "username": request.username,
            "currency": currency_info
        }
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
        return {"cities": [{"city": r.city, "country": r.country} for r in result]}
    finally:
        db.close()

@app.post("/parse-trip")
def parse_trip(request: NaturalLanguageRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = extract_trip_details(request.message, user.country or "India")
        if "error" in result:
            raise HTTPException(status_code=400, detail="Could not understand the trip request")
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
            raise HTTPException(status_code=404, detail="No spots found for this city")

        ranked = rank_spots(spots, category_weights, request.budget_per_day_usd)
        itinerary = build_itinerary(ranked, request.days)

        result = {}
        total_cost_usd = 0

        for day, slots in itinerary.items():
            result[str(day)] = {}
            for time_slot, spot in slots.items():
                if spot:
                    spot_dict = spot_to_dict(spot, usd_rate, currency_symbol)
                    total_cost_usd += float(spot.cost_usd)
                    result[str(day)][time_slot] = spot_dict
                else:
                    result[str(day)][time_slot] = None

        hotels = db.execute(
            text("""SELECT * FROM hotels
                    WHERE LOWER(city) = LOWER(:city)
                    AND LOWER(type) = LOWER(:type)
                    AND price_per_night_usd <= :budget
                    ORDER BY rating DESC LIMIT 3"""),
            {"city": request.city,
             "type": request.hotel_type or "Hotel",
             "budget": request.budget_per_day_usd}
        ).fetchall()

        if not hotels:
            hotels = db.execute(
                text("SELECT * FROM hotels WHERE LOWER(city) = LOWER(:city) ORDER BY rating DESC LIMIT 3"),
                {"city": request.city}
            ).fetchall()

        restaurants = db.execute(
            text("""SELECT * FROM restaurants
                    WHERE LOWER(city) = LOWER(:city)
                    ORDER BY rating DESC LIMIT 5"""),
            {"city": request.city}
        ).fetchall()

        if request.food_type:
            filtered = [r for r in restaurants if r.food_type == request.food_type]
            if filtered:
                restaurants = filtered

        collab_recs = get_collaborative_recommendations(request.username, request.city)
        personality = get_travel_personality(category_weights)

        db.execute(
            text("UPDATE users SET travel_personality = :p WHERE username = :u"),
            {"p": personality, "u": request.username}
        )
        db.commit()

        return {
            "itinerary": result,
            "city": request.city,
            "days": request.days,
            "total_cost_usd": round(total_cost_usd, 2),
            "total_cost_local": convert_to_local(total_cost_usd, usd_rate),
            "currency_symbol": currency_symbol,
            "hotels": [
                {
                    "id": h.id,
                    "name": h.name,
                    "type": h.type,
                    "bedrooms": h.bedrooms,
                    "price_per_night_usd": float(h.price_per_night_usd),
                    "price_per_night_local": convert_to_local(float(h.price_per_night_usd), usd_rate),
                    "rating": float(h.rating),
                    "amenities": h.amenities,
                    "description": h.description
                } for h in hotels
            ],
            "restaurants": [
                {
                    "id": r.id,
                    "name": r.name,
                    "cuisine": r.cuisine,
                    "food_type": r.food_type,
                    "price_per_meal_usd": float(r.price_per_meal_usd),
                    "price_per_meal_local": convert_to_local(float(r.price_per_meal_usd), usd_rate),
                    "rating": float(r.rating),
                    "description": r.description
                } for r in restaurants
            ],
            "collaborative_recommendations": collab_recs,
            "travel_personality": personality
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
            {"uid": user.id, "sid": request.spot_id, "dir": request.direction}
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

        ai_response = handle_midtrip_request(
            request.message,
            request.current_itinerary,
            request.city,
            request.day
        )

        if ai_response.get("action") == "replace_spot":
            category_weights = dict(user.category_weights)
            spots = db.execute(
                text("SELECT * FROM spots WHERE LOWER(city) = LOWER(:city)"),
                {"city": request.city}
            ).fetchall()

            category_pref = ai_response.get("category_preference")
            indoor_pref = ai_response.get("indoor_preferred", False)

            if category_pref:
                filtered = [s for s in spots if s.category == category_pref]
                if filtered:
                    spots = filtered

            ranked = rank_spots(spots, category_weights, 999)
            current_ids = set()
            for day_slots in request.current_itinerary.values():
                for spot in day_slots.values():
                    if spot:
                        current_ids.add(spot.get("id"))

            suggestions = [s for s in ranked if s.id not in current_ids][:3]

            return {
                "ai_response": ai_response,
                "suggestions": [spot_to_dict(s) for s in suggestions]
            }

        return {"ai_response": ai_response, "suggestions": []}
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
            text("UPDATE trips SET status = 'past' WHERE user_id = :uid AND status = 'active'"),
            {"uid": user.id}
        )

        trip_name = request.trip_name or generate_trip_name(request.city, request.days)

        result = db.execute(
            text("""INSERT INTO trips
                    (user_id, city, country, days, budget_per_day_usd, budget_per_day_local,
                     currency_code, currency_symbol, hotel_type, bedrooms, food_type, trip_name)
                    VALUES (:uid, :city, :country, :days, :budget_usd, :budget_local,
                            :cc, :cs, :ht, :br, :ft, :tn)
                    RETURNING id"""),
            {"uid": user.id, "city": request.city, "country": request.country,
             "days": request.days, "budget_usd": request.budget_per_day_usd,
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
        return {"message": "Trip saved", "trip_id": trip_id, "trip_name": trip_name}
    finally:
        db.close()

@app.get("/dashboard/{username}")
def get_dashboard(username: str):
    db = SessionLocal()
    try:
        user = get_user(db, request.username) if False else db.execute(
            text("SELECT * FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        trips = db.execute(
            text("""SELECT t.*, ti.itinerary_data, ti.hotel_data, ti.restaurant_data
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
                "budget_per_day_local": float(trip.budget_per_day_local) if trip.budget_per_day_local else 0,
                "currency_symbol": trip.currency_symbol,
                "hotel_type": trip.hotel_type,
                "food_type": trip.food_type,
                "status": trip.status,
                "created_at": str(trip.created_at),
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

@app.get("/spot-insight/{spot_name}/{city}")
def spot_insight(spot_name: str, city: str):
    insight = get_spot_insight(spot_name, city)
    return {"insight": insight}
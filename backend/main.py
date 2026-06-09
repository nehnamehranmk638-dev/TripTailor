from backend.ranker import rank_spots, build_itinerary, smart_replan
from backend.models import UserCreate, ItineraryRequest, FeedbackRequest, ReplanRequest, SmartReplanRequest
from fastapi import FastAPI, HTTPException
from backend.database import SessionLocal
from backend.models import UserCreate, ItineraryRequest, FeedbackRequest, ReplanRequest
from backend.ranker import rank_spots, build_itinerary
from sqlalchemy import text
import json

app = FastAPI()

def get_user(db, username):
    result = db.execute(
        text("SELECT * FROM users WHERE username = :u"),
        {"u": username}
    ).fetchone()
    return result

@app.post("/users/create")
def create_user(request: UserCreate):
    db = SessionLocal()
    try:
        existing = get_user(db, request.username)
        if existing:
            return {"message": "User already exists", "username": request.username}
        db.execute(
            text("INSERT INTO users (username) VALUES (:u)"),
            {"u": request.username}
        )
        db.commit()
        return {"message": "User created", "username": request.username}
    finally:
        db.close()

@app.post("/generate-itinerary")
def generate_itinerary(request: ItineraryRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        category_weights = user.category_weights

        spots = db.execute(
            text("SELECT * FROM spots WHERE LOWER(city) = LOWER(:city)"),
            {"city": request.city}
        ).fetchall()

        if not spots:
            raise HTTPException(status_code=404, detail="No spots found for this city")

        ranked = rank_spots(spots, category_weights, request.budget_per_day)
        itinerary = build_itinerary(ranked, request.days)

        result = {}
        for day, slots in itinerary.items():
            result[day] = {}
            for time_slot, spot in slots.items():
                if spot:
                    result[day][time_slot] = {
                        "id": spot.id,
                        "name": spot.name,
                        "category": spot.category,
                        "cost_usd": spot.cost_usd,
                        "rating": float(spot.rating),
                        "description": spot.description
                    }
                else:
                    result[day][time_slot] = None

        return {"itinerary": result, "city": request.city}
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

        weights = dict(user.category_weights)
        category = spot.category

        if request.direction == "up":
            weights[category] = round(min(weights.get(category, 1.0) + 0.2, 2.0), 2)
        elif request.direction == "down":
            weights[category] = round(max(weights.get(category, 1.0) - 0.6, 0.0), 2)

        db.execute(
            text("UPDATE users SET category_weights = :w WHERE username = :u"),
            {"w": json.dumps(weights), "u": request.username}
        )

        db.execute(
            text("INSERT INTO feedback_events (user_id, spot_id, direction) VALUES (:uid, :sid, :dir)"),
            {"uid": user.id, "sid": request.spot_id, "dir": request.direction}
        )

        db.commit()
        return {"message": "Feedback recorded", "updated_weights": weights}
    finally:
        db.close()

@app.post("/replan")
def replan(request: ReplanRequest):
    return generate_itinerary(
        ItineraryRequest(
            username=request.username,
            city=request.city,
            budget_per_day=request.budget_per_day,
            days=request.days
        )
    )
@app.post("/smart-replan")
def smart_replan_endpoint(request: SmartReplanRequest):
    db = SessionLocal()
    try:
        user = get_user(db, request.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        category_weights = user.category_weights

        spots = db.execute(
            text("SELECT * FROM spots WHERE LOWER(city) = LOWER(:city)"),
            {"city": request.city}
        ).fetchall()

        if not spots:
            raise HTTPException(status_code=404, detail="No spots found for this city")

        new_itinerary = smart_replan(
            request.current_itinerary,
            spots,
            category_weights,
            request.budget_per_day,
            request.locked_spot_ids,
            request.disliked_spot_ids
        )

        return {"itinerary": new_itinerary, "city": request.city}
    finally:
        db.close()
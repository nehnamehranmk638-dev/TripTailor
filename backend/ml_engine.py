from backend.database import SessionLocal
from sqlalchemy import text
import json

def update_category_weights(username: str, category: str, direction: str):
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT category_weights FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
        if not user:
            return
        weights = dict(user.category_weights)
        if direction == "up":
            weights[category] = round(min(weights.get(category, 1.0) + 0.2, 2.0), 2)
        elif direction == "down":
            weights[category] = round(max(weights.get(category, 1.0) - 0.6, 0.0), 2)
        db.execute(
            text("UPDATE users SET category_weights = :w WHERE username = :u"),
            {"w": json.dumps(weights), "u": username}
        )
        db.commit()
        return weights
    finally:
        db.close()

def get_travel_personality(category_weights: dict) -> str:
    if not category_weights:
        return "Explorer"
    top_category = max(category_weights, key=category_weights.get)
    personality_map = {
        "Culture": "Culture Seeker",
        "Food": "Food Explorer",
        "Nature": "Nature Lover",
        "Shopping": "Shopaholic",
        "Art": "Art Enthusiast",
        "Nightlife": "Night Owl"
    }
    return personality_map.get(top_category, "Explorer")

def get_collaborative_recommendations(username: str, city: str, limit: int = 3):
    db = SessionLocal()
    try:
        current_user = db.execute(
            text("SELECT id, category_weights FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
        if not current_user:
            return []

        current_weights = dict(current_user.category_weights)
        top_category = max(current_weights, key=current_weights.get)

        similar_users = db.execute(
            text("""
                SELECT DISTINCT u.id, u.username
                FROM users u
                JOIN feedback_events fe ON u.id = fe.user_id
                JOIN spots s ON fe.spot_id = s.id
                WHERE s.category = :cat
                AND fe.direction = 'up'
                AND u.username != :username
                LIMIT 10
            """),
            {"cat": top_category, "username": username}
        ).fetchall()

        if not similar_users:
            return []

        similar_user_ids = [u.id for u in similar_users]
        placeholders = ",".join([str(uid) for uid in similar_user_ids])

        already_seen = db.execute(
            text("""
                SELECT DISTINCT spot_id FROM feedback_events
                WHERE user_id = :uid
            """),
            {"uid": current_user.id}
        ).fetchall()
        seen_ids = [r.spot_id for r in already_seen]

        recommended = db.execute(
            text(f"""
                SELECT s.*, COUNT(*) as like_count
                FROM spots s
                JOIN feedback_events fe ON s.id = fe.spot_id
                WHERE fe.user_id IN ({placeholders})
                AND fe.direction = 'up'
                AND LOWER(s.city) = LOWER(:city)
                AND s.id NOT IN ({','.join([str(i) for i in seen_ids]) if seen_ids else '0'})
                GROUP BY s.id
                ORDER BY like_count DESC
                LIMIT :limit
            """),
            {"city": city, "limit": limit}
        ).fetchall()

        return [{"id": r.id, "name": r.name, "category": r.category,
                "rating": float(r.rating), "reason": f"Loved by travelers with similar taste"
                } for r in recommended]
    finally:
        db.close()
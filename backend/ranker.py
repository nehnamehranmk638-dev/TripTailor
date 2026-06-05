def calculate_score(spot, category_weights, budget_per_day):
    base_rating = float(spot.rating)
    weight = category_weights.get(spot.category, 1.0)
    budget_fit = 1.0 if spot.cost_usd <= budget_per_day else 0.0
    return base_rating * weight * budget_fit

def rank_spots(spots, category_weights, budget_per_day):
    scored = []
    for spot in spots:
        score = calculate_score(spot, category_weights, budget_per_day)
        scored.append((spot, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [spot for spot, score in scored if score > 0]

def build_itinerary(ranked_spots, days):
    time_slots = ["Morning", "Afternoon", "Evening"]
    itinerary = {}
    used_ids = set()

    for day in range(1, days + 1):
        itinerary[day] = {}
        for slot in time_slots:
            slot_spots = [s for s in ranked_spots
                         if s.time_of_day == slot and s.id not in used_ids]
            if slot_spots:
                chosen = slot_spots[0]
                itinerary[day][slot] = chosen
                used_ids.add(chosen.id)
            else:
                itinerary[day][slot] = None

    return itinerary
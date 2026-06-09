def calculate_score(spot, category_weights, budget_per_day):
    base_rating = float(spot.rating)
    weight = category_weights.get(spot.category, 1.0)

    if weight <= 0.0:
        return 0.0

    budget_fit = 1.0 if spot.cost_usd <= budget_per_day else 0.0
    return base_rating * weight * budget_fit

def rank_spots(spots, category_weights, budget_per_day, excluded_ids=None):
    if excluded_ids is None:
        excluded_ids = set()

    scored = []
    for spot in spots:
        if spot.id in excluded_ids:
            continue
        score = calculate_score(spot, category_weights, budget_per_day)
        if score > 0:
            scored.append((spot, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [spot for spot, score in scored]

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
                any_unused = [s for s in ranked_spots if s.id not in used_ids]
                if any_unused:
                    chosen = any_unused[0]
                    itinerary[day][slot] = chosen
                    used_ids.add(chosen.id)
                else:
                    itinerary[day][slot] = None

    return itinerary

def smart_replan(current_itinerary, all_spots, category_weights,
                 budget_per_day, locked_spot_ids, disliked_spot_ids):
    time_slots = ["Morning", "Afternoon", "Evening"]

    locked_ids = set(locked_spot_ids)
    disliked_ids = set(disliked_spot_ids)

    spot_lookup = {spot.id: spot for spot in all_spots}

    used_ids = set()
    for day_slots in current_itinerary.values():
        for spot in day_slots.values():
            if spot and spot["id"] in locked_ids:
                used_ids.add(spot["id"])

    excluded = disliked_ids | used_ids
    available_spots = [s for s in all_spots
                      if s.id not in excluded]

    scored = []
    for spot in available_spots:
        score = calculate_score(spot, category_weights, budget_per_day)
        if score > 0:
            scored.append((spot, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    ranked_replacements = [spot for spot, score in scored]

    new_itinerary = {}

    for day_num, day_slots in current_itinerary.items():
        new_itinerary[day_num] = {}
        for slot in time_slots:
            spot = day_slots.get(slot)

            if spot and spot["id"] in locked_ids:
                new_itinerary[day_num][slot] = spot
                continue

            if spot and spot["id"] not in disliked_ids:
                new_itinerary[day_num][slot] = spot
                continue

            slot_replacements = [s for s in ranked_replacements
                                 if s.time_of_day == slot
                                 and s.id not in used_ids]

            if not slot_replacements:
                slot_replacements = [s for s in ranked_replacements
                                    if s.id not in used_ids]

            if slot_replacements:
                chosen = slot_replacements[0]
                new_itinerary[day_num][slot] = {
                    "id": chosen.id,
                    "name": chosen.name,
                    "category": chosen.category,
                    "cost_usd": chosen.cost_usd,
                    "rating": float(chosen.rating),
                    "description": chosen.description
                }
                used_ids.add(chosen.id)
                ranked_replacements = [s for s in ranked_replacements
                                      if s.id not in used_ids]
            else:
                new_itinerary[day_num][slot] = None

    return new_itinerary
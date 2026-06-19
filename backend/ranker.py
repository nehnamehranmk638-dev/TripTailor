import math
from collections import defaultdict

def _round_to_quarter_hour(minutes):
    return int(round(minutes / 15) * 15)

def _haversine_distance_km(lat1, lon1, lat2, lon2):
    if not all([lat1, lon1, lat2, lon2]):
        return None
    R = 6371
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _travel_time_minutes(dist_km):
    if dist_km is None:
        return 30
    BUFFER = 15
    if dist_km <= 0.3:
        raw = max(5, int(dist_km * 1000 / 80))
    elif dist_km <= 1.0:
        raw = int(dist_km * 1000 / 70)
    else:
        road_km = dist_km * 1.4
        if road_km < 20:
            avg_speed = 30
        elif road_km < 80:
            avg_speed = 45
        else:
            avg_speed = 25
        raw = int((road_km / avg_speed) * 60)
    return raw + BUFFER


def _transport_mode(dist_km):
    if dist_km is None:
        return "drive"
    if dist_km <= 1.0:
        return "walk"
    if dist_km <= 5.0:
        return "auto"
    return "drive"


def _format_transport(dist_km, travel_mins):
    display = max(travel_mins - 15, 1)
    if display >= 60:
        h = display // 60
        m = display % 60
        return None, (f"{h}h {m}m" if m else f"{h}h")
    return None, f"{display} min"


def calculate_score(spot, category_weights, budget_per_day):
    base_rating = float(spot.rating)
    weight = category_weights.get(spot.category, 1.0)
    if weight <= 0.0:
        return 0.0
    return base_rating * weight


def rank_spots(spots, category_weights, budget_per_day,
               excluded_ids=None):
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


def _reorder_by_proximity(spots):
    if len(spots) <= 1:
        return spots
    remaining = list(spots)
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        last_lat = getattr(last, 'latitude', None)
        last_lon = getattr(last, 'longitude', None)
        best_idx = 0
        best_dist = float('inf')
        for i, spot in enumerate(remaining):
            dist = _haversine_distance_km(
                last_lat, last_lon,
                getattr(spot, 'latitude', None),
                getattr(spot, 'longitude', None)
            )
            if dist is None:
                dist = 50
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        ordered.append(remaining.pop(best_idx))
    return ordered


def _preferred_time_window(spot):
    tod = (getattr(spot, 'time_of_day', None) or '').strip().lower()
    if tod == 'morning':
        return (9 * 60, 13 * 60)
    if tod == 'afternoon':
        return (12 * 60, 18 * 60)
    if tod == 'evening':
        return (17 * 60, 23 * 60)
    return (9 * 60, 20 * 60)


def _distribute_spots_across_days(ranked_spots, days, max_hours_per_day=9):
    day_buckets = {d: [] for d in range(1, days + 1)}
    day_hours = {d: 0.0 for d in range(1, days + 1)}
    day_categories = {d: defaultdict(int) for d in range(1, days + 1)}
    MAX_PER_CATEGORY_PER_DAY = 2

    for spot in ranked_spots:
        dur = float(spot.duration_hours or 2.0)
        cat = spot.category

        best_day = None
        best_hours = float('inf')

        for d in range(1, days + 1):
            if day_hours[d] + dur > max_hours_per_day:
                continue
            if day_categories[d][cat] >= MAX_PER_CATEGORY_PER_DAY:
                continue
            if day_hours[d] < best_hours:
                best_hours = day_hours[d]
                best_day = d

        if best_day is None:
            for d in range(1, days + 1):
                if day_hours[d] + dur <= max_hours_per_day:
                    if day_hours[d] < best_hours:
                        best_hours = day_hours[d]
                        best_day = d

        if best_day is not None:
            day_buckets[best_day].append(spot)
            day_hours[best_day] += dur
            day_categories[best_day][cat] += 1

    return day_buckets


def build_timed_itinerary(ranked_spots, days):
    DAY_START = 9 * 60
    DAY_END = 20 * 60
    MAX_DAY_HOURS = 9

    day_buckets = _distribute_spots_across_days(
        ranked_spots, days, MAX_DAY_HOURS
    )

    itinerary = {}

    for day in range(1, days + 1):
        day_pool = day_buckets.get(day, [])
        if not day_pool:
            itinerary[day] = []
            continue

        morning = [s for s in day_pool
                  if (getattr(s, 'time_of_day', '') or '').lower() == 'morning']
        afternoon = [s for s in day_pool
                    if (getattr(s, 'time_of_day', '') or '').lower() == 'afternoon']
        evening = [s for s in day_pool
                  if (getattr(s, 'time_of_day', '') or '').lower() == 'evening']
        flexible = [s for s in day_pool
                   if (getattr(s, 'time_of_day', '') or '').lower()
                   not in ('morning', 'afternoon', 'evening')]

        if len(morning) > 1:
            morning = _reorder_by_proximity(morning)
        if len(afternoon) > 1:
            afternoon = _reorder_by_proximity(afternoon)
        if len(evening) > 1:
            evening = _reorder_by_proximity(evening)
        if len(flexible) > 1:
            flexible = _reorder_by_proximity(flexible)

        ordered_pool = morning + flexible + afternoon + evening

        current_time = DAY_START
        prev_spot = None
        day_slots = []

        for spot in ordered_pool:
            dur = float(spot.duration_hours or 2.0)
            duration_mins = int(dur * 60)

            if prev_spot is not None:
                dist_km = _haversine_distance_km(
                    getattr(prev_spot, 'latitude', None),
                    getattr(prev_spot, 'longitude', None),
                    getattr(spot, 'latitude', None),
                    getattr(spot, 'longitude', None)
                )
                travel_mins = _travel_time_minutes(dist_km)
                mode, transport_label = _format_transport(
                    dist_km, travel_mins
                )
            else:
                dist_km = None
                travel_mins = 0
                mode = None
                transport_label = None

            arrival_time = _round_to_quarter_hour(current_time + travel_mins)

            win_start, win_end = _preferred_time_window(spot)
            if arrival_time < win_start:
                arrival_time = _round_to_quarter_hour(win_start)
            elif arrival_time > win_end - 30:
                arrival_time = _round_to_quarter_hour(
                    max(arrival_time, win_start)
                )

            if arrival_time >= DAY_END - 45:
                break

            if arrival_time + duration_mins > DAY_END:
                remaining = DAY_END - arrival_time
                if remaining >= 45:
                    duration_mins = remaining
                    dur = round(duration_mins / 60, 1)
                else:
                    break

            end_time = arrival_time + duration_mins
            time_label = (
                "Morning" if arrival_time < 12 * 60
                else "Afternoon" if arrival_time < 17 * 60
                else "Evening"
            )

            day_slots.append({
                "spot": spot,
                "start_time": _format_time(arrival_time),
                "end_time": _format_time(end_time),
                "duration_hours": dur,
                "time_label": time_label,
                "travel_mins": travel_mins,
                "dist_km": round(dist_km, 2) if dist_km else None,
                "transport_mode": mode,
                "transport_label": transport_label
            })

            prev_spot = spot
            current_time = end_time

        itinerary[day] = day_slots

    return itinerary


def smart_replan(current_itinerary, all_spots, category_weights,
                budget_per_day, locked_spot_ids, disliked_spot_ids):
    locked_ids = set(locked_spot_ids)
    disliked_ids = set(disliked_spot_ids)
    DAY_START = 9 * 60

    used_ids = set()
    for day_slots in current_itinerary.values():
        if isinstance(day_slots, list):
            for slot in day_slots:
                if isinstance(slot, dict):
                    spot = slot.get("spot", {})
                    if isinstance(spot, dict):
                        spot_id = spot.get("id")
                        if spot_id and spot_id not in disliked_ids:
                            used_ids.add(spot_id)

    excluded = disliked_ids | used_ids
    available_spots = [s for s in all_spots if s.id not in excluded]

    scored = [(s, calculate_score(s, category_weights, budget_per_day))
              for s in available_spots]
    scored = [(s, sc) for s, sc in scored if sc > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    ranked_replacements = [s for s, _ in scored]

    new_itinerary = {}

    for day_num, day_slots in current_itinerary.items():
        new_day = []
        current_time = DAY_START
        prev_spot_data = None

        if not isinstance(day_slots, list):
            new_itinerary[day_num] = []
            continue

        for slot in day_slots:
            if not isinstance(slot, dict):
                continue
            spot_data = slot.get("spot", {})
            if not isinstance(spot_data, dict):
                continue

            spot_id = spot_data.get("id")
            duration_hours = slot.get("duration_hours", 2.0)
            duration_mins = int(duration_hours * 60)

            if prev_spot_data:
                dist_km = _haversine_distance_km(
                    prev_spot_data.get("latitude"),
                    prev_spot_data.get("longitude"),
                    spot_data.get("latitude"),
                    spot_data.get("longitude")
                )
                travel_mins = _travel_time_minutes(dist_km)
                mode, transport_label = _format_transport(
                    dist_km, travel_mins
                )
            else:
                dist_km = None
                travel_mins = 0
                mode = None
                transport_label = None

            arrival = _round_to_quarter_hour(current_time + travel_mins)

            if spot_id in locked_ids or spot_id not in disliked_ids:
                new_day.append({
                    **slot,
                    "start_time": _format_time(arrival),
                    "end_time": _format_time(arrival + duration_mins),
                    "travel_mins": travel_mins,
                    "dist_km": round(dist_km, 2) if dist_km else None,
                    "transport_mode": mode,
                    "transport_label": transport_label
                })
                prev_spot_data = spot_data
                current_time = arrival + duration_mins
            else:
                replacement = next(
                    (r for r in ranked_replacements
                     if r.id not in used_ids), None
                )
                if replacement:
                    r_dur = float(replacement.duration_hours or 2.0)
                    r_dur_mins = int(r_dur * 60)
                    r_dist = _haversine_distance_km(
                        prev_spot_data.get("latitude")
                        if prev_spot_data else None,
                        prev_spot_data.get("longitude")
                        if prev_spot_data else None,
                        float(replacement.latitude)
                        if replacement.latitude else None,
                        float(replacement.longitude)
                        if replacement.longitude else None
                    )
                    r_travel = _travel_time_minutes(r_dist)
                    r_mode, r_label = _format_transport(r_dist, r_travel)
                    r_arrival = _round_to_quarter_hour(current_time + r_travel)
                    r_spot_dict = _spot_to_dict(replacement)

                    new_day.append({
                        "spot": r_spot_dict,
                        "start_time": _format_time(r_arrival),
                        "end_time": _format_time(r_arrival + r_dur_mins),
                        "duration_hours": r_dur,
                        "time_label": _get_time_label(r_arrival),
                        "travel_mins": r_travel,
                        "dist_km": round(r_dist, 2) if r_dist else None,
                        "transport_mode": r_mode,
                        "transport_label": r_label
                    })
                    used_ids.add(replacement.id)
                    ranked_replacements = [
                        s for s in ranked_replacements
                        if s.id not in used_ids
                    ]
                    prev_spot_data = r_spot_dict
                    current_time = r_arrival + r_dur_mins

        new_itinerary[day_num] = new_day

    return new_itinerary


def _format_time(minutes):
    minutes = max(0, min(int(minutes), 23 * 60 + 59))
    hour = minutes // 60
    minute = minutes % 60
    am_pm = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:{minute:02d} {am_pm}"


def _get_time_label(minutes):
    if minutes < 12 * 60:
        return "Morning"
    elif minutes < 17 * 60:
        return "Afternoon"
    return "Evening"


def _spot_to_dict(spot):
    return {
        "id": spot.id,
        "name": spot.name,
        "category": spot.category,
        "cost_usd": float(spot.cost_usd),
        "rating": float(spot.rating),
        "description": spot.description,
        "duration_hours": float(spot.duration_hours or 2.0),
        "time_of_day": spot.time_of_day,
        "latitude": float(spot.latitude) if spot.latitude else None,
        "longitude": float(spot.longitude) if spot.longitude else None,
        "opening_time": getattr(spot, 'opening_time', '09:00') or '09:00',
        "closing_time": getattr(spot, 'closing_time', '18:00') or '18:00',
        "closed_day": getattr(spot, 'closed_day', '') or '',
        "afternoon_break": getattr(spot, 'afternoon_break', False) or False,
        "local_tip": getattr(spot, 'local_tip', '') or ''
    }
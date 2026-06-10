import folium
from streamlit_folium import st_folium

CITY_CENTERS = {
    "Mumbai": [19.0760, 72.8777],
    "Jaipur": [26.9124, 75.7873],
    "Agra": [27.1767, 78.0081],
    "Mysore": [12.3052, 76.6552],
    "Delhi": [28.6139, 77.2090],
    "Goa": [15.2993, 74.1240],
    "Kerala": [9.9312, 76.2673],
    "Chennai": [13.0827, 80.2707],
    "Dubai": [25.2048, 55.2708],
    "Singapore": [1.3521, 103.8198],
    "Bangkok": [13.7563, 100.5018]
}

CATEGORY_COLORS = {
    "Culture": "red",
    "Food": "orange",
    "Nature": "green",
    "Shopping": "purple",
    "Art": "blue",
    "Nightlife": "darkblue"
}

TIME_ORDER = ["Morning", "Afternoon", "Evening"]

def build_map(itinerary, city):
    center = CITY_CENTERS.get(city, [20.5937, 78.9629])
    m = folium.Map(location=center, zoom_start=13,
                  tiles="CartoDB positron")

    all_spots_ordered = []
    for day_num in sorted(itinerary.keys(), key=lambda x: int(x)):
        day_data = itinerary[day_num]
        for time_slot in TIME_ORDER:
            spot = day_data.get(time_slot)
            if spot and spot.get("latitude") and spot.get("longitude"):
                all_spots_ordered.append((day_num, time_slot, spot))

    for i, (day_num, time_slot, spot) in enumerate(all_spots_ordered):
        lat = spot["latitude"]
        lng = spot["longitude"]
        color = CATEGORY_COLORS.get(spot["category"], "gray")
        cost_str = "Free" if spot["cost_usd"] == 0 else f"${spot['cost_usd']}"
        local_cost = f" ({spot.get('currency_symbol', '')}{spot.get('cost_local', 0)})" if spot.get('cost_local') else ""

        popup_html = f"""
        <div style="width:220px; font-family:Arial; padding:8px">
            <div style="background:#1D9E75; color:white; padding:4px 8px;
                        border-radius:4px; font-size:11px; margin-bottom:6px">
                Day {day_num} — {time_slot}
            </div>
            <h3 style="margin:4px 0; font-size:14px">{spot['name']}</h3>
            <p style="margin:2px 0; font-size:12px">🏷️ {spot['category']}</p>
            <p style="margin:2px 0; font-size:12px">💰 {cost_str}{local_cost}</p>
            <p style="margin:2px 0; font-size:12px">⭐ {spot['rating']} | ⏱️ {spot.get('duration_hours', 2)}h</p>
            <p style="margin:6px 0 2px; font-size:11px; color:#666">{spot['description']}</p>
        </div>
        """

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=240),
            tooltip=f"Day {day_num} {time_slot}: {spot['name']}",
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

        folium.Marker(
            location=[lat, lng],
            icon=folium.DivIcon(
                html=f"""<div style="font-size:11px; font-weight:bold; color:white;
                            background:#1D9E75; border-radius:50%; width:22px; height:22px;
                            display:flex; align-items:center; justify-content:center;
                            border:2px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.3)">
                            {i+1}</div>""",
                icon_size=(22, 22),
                icon_anchor=(11, 11)
            )
        ).add_to(m)

    if len(all_spots_ordered) > 1:
        route_coords = [
            [spot["latitude"], spot["longitude"]]
            for _, _, spot in all_spots_ordered
        ]
        folium.PolyLine(
            route_coords,
            color="#1D9E75",
            weight=2.5,
            opacity=0.7,
            dash_array="6 6"
        ).add_to(m)

    return m

def show_map(itinerary, city):
    m = build_map(itinerary, city)
    st_folium(m, width=None, height=480, returned_objects=[])
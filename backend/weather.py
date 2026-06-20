import requests
from datetime import datetime, timedelta

CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777),
    "Jaipur": (26.9124, 75.7873),
    "Agra": (27.1767, 78.0081),
    "Mysore": (12.3052, 76.6552),
    "Delhi": (28.6139, 77.2090),
    "Goa": (15.2993, 74.1240),
    "Kerala": (9.9312, 76.2673),
    "Chennai": (13.0827, 80.2707)
}

WEATHER_CODES = {
    0: ("☀️", "Clear skies", False),
    1: ("🌤️", "Mainly clear", False),
    2: ("⛅", "Partly cloudy", False),
    3: ("☁️", "Overcast", False),
    45: ("🌫️", "Foggy", False),
    48: ("🌫️", "Icy fog", False),
    51: ("🌦️", "Light drizzle", True),
    53: ("🌦️", "Drizzle", True),
    55: ("🌧️", "Heavy drizzle", True),
    61: ("🌧️", "Light rain", True),
    63: ("🌧️", "Moderate rain", True),
    65: ("⛈️", "Heavy rain", True),
    71: ("🌨️", "Light snow", False),
    73: ("🌨️", "Moderate snow", False),
    75: ("❄️", "Heavy snow", False),
    80: ("🌦️", "Rain showers", True),
    81: ("🌧️", "Heavy showers", True),
    82: ("⛈️", "Violent showers", True),
    95: ("⛈️", "Thunderstorm", True),
    96: ("⛈️", "Thunderstorm with hail", True),
    99: ("⛈️", "Heavy thunderstorm", True),
}

def get_weather_forecast(city: str, days: int = 7):
    coords = CITY_COORDS.get(city)
    if not coords:
        return None

    lat, lon = coords

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min,"
            f"precipitation_sum,windspeed_10m_max"
            f"&timezone=auto&forecast_days={min(days + 1, 7)}"
        )
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return None

        data = response.json()
        daily = data.get("daily", {})

        dates = daily.get("time", [])
        codes = daily.get("weathercode", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])

        forecasts = []
        for i in range(min(len(dates), days)):
            code = codes[i] if i < len(codes) else 0
            emoji, description, is_rainy = WEATHER_CODES.get(
                code, ("🌤️", "Partly cloudy", False)
            )
            max_t = round(max_temps[i]) if i < len(max_temps) else None
            min_t = round(min_temps[i]) if i < len(min_temps) else None
            rain = round(precip[i], 1) if i < len(precip) else 0

            forecasts.append({
                "date": dates[i],
                "day_number": i + 1,
                "emoji": emoji,
                "description": description,
                "is_rainy": is_rainy,
                "max_temp": max_t,
                "min_temp": min_t,
                "precipitation_mm": rain
            })

        return forecasts

    except Exception as e:
        return None


def get_indoor_suggestion(is_rainy: bool, description: str) -> str:
    if not is_rainy:
        return ""
    return (
        f"🌧️ {description} expected. Consider prioritizing "
        f"indoor spots like museums, galleries, temples and "
        f"shopping areas today. Carry an umbrella!"
    )
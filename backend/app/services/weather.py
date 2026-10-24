import asyncio
import time
import httpx

_cache = {}
CACHE_SECONDS = 3 * 60 * 60


async def get_forecast(lat: float, lon: float):
    key = (round(lat, 2), round(lon, 2))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "timezone": "auto",
        "forecast_days": 7,
    }

    delay = 2
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                daily = r.json()["daily"]
            days = []
            for i, date in enumerate(daily["time"]):
                days.append({
                    "date": date,
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "rain_chance": daily["precipitation_probability_max"][i],
                    "weather_code": daily["weathercode"][i],
                })
            _cache[key] = (time.time(), days)
            return days
        except Exception as e:
            print(f"Weather lookup failed (attempt {attempt + 1}):", repr(e))
            if attempt < 2:
                await asyncio.sleep(delay)
                delay *= 2
    return []
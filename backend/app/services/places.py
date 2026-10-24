import os
import httpx

async def get_attractions(lat: float, lon: float, limit: int = 15):
    key = os.getenv("OPENTRIPMAP_API_KEY")
    if not key or key == "your_key_here":
        return []
    url = "https://api.opentripmap.com/0.1/en/places/radius"
    params = {
        "radius": 15000,
        "lon": lon,
        "lat": lat,
        "rate": 2,
        "format": "json",
        "limit": 50,
        "apikey": key,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        items = r.json()
    places = []
    for p in items:
        if p.get("name"):
            places.append({
                "name": p["name"],
                "lat": p["point"]["lat"],
                "lon": p["point"]["lon"],
                "kinds": p.get("kinds", "").split(",")[:3],
            })
    return places[:limit]
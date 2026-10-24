import httpx

async def geocode(destination: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": destination, "format": "json", "limit": 1}
    headers = {"User-Agent": "ai-travel-planner/1.0"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
    if not data:
        return None
    d = data[0]
    return {"name": d["display_name"], "lat": float(d["lat"]), "lon": float(d["lon"])}
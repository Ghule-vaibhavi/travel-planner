import os
import re
import asyncio
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

load_dotenv()

from app.schemas import ChatRequest
from app.services.geocode import geocode
from app.services.weather import get_forecast
from app.services.places import get_attractions
from app.services.pdf_export import build_trip_pdf
from app.agents.graph import build_graph
from app.agents.chat import chat_with_plan
from app.storage.store import get_cached, save_plan, get_trip, update_itinerary

app = FastAPI(title="AI Travel Planner")
trip_graph = build_graph()

origins = [
    o.strip().rstrip("/")
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/explore")
async def explore(destination: str):
    destination = destination.strip()
    if len(destination) < 2:
        raise HTTPException(status_code=400, detail="Please enter a destination.")
    try:
        loc = await geocode(destination)
        if not loc:
            raise HTTPException(status_code=404, detail="Destination not found.")
        weather = await get_forecast(loc["lat"], loc["lon"])
        attractions = await get_attractions(loc["lat"], loc["lon"])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="A data service is unavailable. Try again.")
    return {
        "location": loc,
        "weather": {"source": "Open-Meteo (verified live)", "forecast": weather},
        "attractions": {"source": "OpenTripMap (verified live)", "items": attractions},
    }


@app.get("/api/plan")
async def plan(destination: str, days: int = Query(3, ge=1, le=10), refresh: bool = False):
    destination = destination.strip()
    if len(destination) < 2:
        raise HTTPException(status_code=400, detail="Please enter a destination.")
    try:
        loc = await geocode(destination)
        if not loc:
            raise HTTPException(status_code=404, detail="Destination not found.")
        weather = await get_forecast(loc["lat"], loc["lon"])
        attractions = await get_attractions(loc["lat"], loc["lon"])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="A data service is unavailable. Try again.")

    ai = None if refresh else get_cached(destination, days)
    from_cache = ai is not None

    if ai is None:
        try:
            result = await asyncio.to_thread(trip_graph.invoke, {
                "destination": destination,
                "days": days,
                "weather": weather,
                "attractions": attractions,
            })
        except Exception as e:
            print("AI error:", e)
            traceback.print_exc()
            raise HTTPException(status_code=502, detail="AI service error. Please try again.")
        ai = {
            "label": "AI suggestions and estimates, not live data",
            "explore": result.get("explore"),
            "transport": result.get("transport"),
            "hotels": result.get("hotels"),
            "weather_advice": result.get("weather_advice"),
            "budget": result.get("budget"),
            "itinerary": result.get("itinerary"),
        }

    response = {
        "from_cache": from_cache,
        "verified_live": {
            "location": loc,
            "weather": {"source": "Open-Meteo", "forecast": weather},
            "attractions": {"source": "OpenTripMap", "items": attractions},
        },
        "ai_generated": ai,
    }
    response["trip_id"] = save_plan(destination, days, response)
    return response


@app.post("/api/chat")
async def chat(req: ChatRequest):
    trip = get_trip(req.trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found. Please generate the plan again.")
    history = [t.model_dump() for t in req.history]
    try:
        data = await asyncio.to_thread(chat_with_plan, trip, req.message, history)
    except Exception as e:
        print("Chat error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=502, detail="The assistant is unavailable. Please try again.")

    reply = str(data.get("reply") or "Sorry, I could not answer that.")
    new_itinerary = data.get("itinerary")
    changed = False
    if isinstance(new_itinerary, dict) and isinstance(new_itinerary.get("days"), list) and new_itinerary["days"]:
        if not isinstance(new_itinerary.get("tips"), dict):
            old = trip["ai_generated"].get("itinerary") or {}
            new_itinerary["tips"] = old.get("tips", {})
        changed = update_itinerary(req.trip_id, new_itinerary)
    return {"reply": reply, "itinerary": new_itinerary if changed else None}


@app.get("/api/trips/{trip_id}/pdf")
def trip_pdf(trip_id: str):
    trip = get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found. Please generate the plan again.")
    try:
        pdf_bytes = build_trip_pdf(trip)
    except Exception as e:
        print("PDF error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Could not create the PDF.")
    place = ((trip.get("verified_live") or {}).get("location") or {}).get("name", "trip").split(",")[0]
    safe = re.sub(r"[^a-z0-9]+", "-", place.lower()).strip("-") or "trip"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="trip-{safe}.pdf"'},
    )
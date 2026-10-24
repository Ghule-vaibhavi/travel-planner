from typing import TypedDict
from urllib.parse import quote
from langgraph.graph import StateGraph, START, END
from app.agents.llm import ask_json

RULES = (
    "Return ONLY a single valid JSON object (never a top-level list). "
    "Never invent live prices, schedules, ratings, or availability. "
    "Any cost must be an approximate range in INR and is an estimate."
)


class TripState(TypedDict, total=False):
    destination: str
    days: int
    attractions: list
    weather: list
    explore: dict
    transport: dict
    hotels: dict
    weather_advice: dict
    budget: dict
    itinerary: dict


def destination_agent(state: TripState):
    names = [a["name"] for a in state.get("attractions", [])]
    prompt = f"""{RULES}
Destination: {state['destination']}
Verified attraction names from a real database (may be empty): {names}
Return JSON with keys: famous_attractions, hidden_gems, local_food,
activities, cultural_experiences. Each is a list of objects
with "name" and "description" (one short sentence)."""
    return {"explore": ask_json(prompt)}


def transport_agent(state: TripState):
    d = state["destination"]
    prompt = f"""{RULES}
Destination: {d}
Return JSON with keys: how_to_reach (list of objects with mode, approx_duration,
approx_fare_inr, tip) covering flight, train, and bus where realistic, and
local_transport (list of objects with mode, approx_cost_inr, tip).
Do not give exact schedules or train/flight numbers."""
    data = ask_json(prompt)
    q = quote(d)
    data["booking_links"] = [
        {"label": "Search flights", "url": f"https://www.google.com/travel/flights?q=Flights%20to%20{q}"},
        {"label": "Search trains (IRCTC)", "url": "https://www.irctc.co.in"},
        {"label": "Search buses (redBus)", "url": "https://www.redbus.in"},
    ]
    return {"transport": data}


def hotel_agent(state: TripState):
    d = state["destination"]
    prompt = f"""{RULES}
Destination: {d}
Return JSON with keys: budget, mid_range, luxury. Each is a list of 2 objects with
area (a real neighbourhood to stay in), stay_type, approx_price_inr_per_night,
amenities (list), why. Do NOT name specific hotels and do NOT give ratings."""
    data = ask_json(prompt)
    data["booking_links"] = [
        {"label": "Browse on Booking.com", "url": f"https://www.booking.com/searchresults.html?ss={quote(d)}"},
        {"label": "Browse on Google Hotels", "url": f"https://www.google.com/travel/hotels/{quote(d)}"},
    ]
    return {"hotels": data}


def weather_agent(state: TripState):
    prompt = f"""{RULES}
Destination: {state['destination']}
Real 7-day forecast (verified): {state.get('weather', [])}
Return JSON with keys: best_season_to_visit (string), clothing (list of strings),
weather_based_alternatives (list of strings for rainy or very hot days)."""
    return {"weather_advice": ask_json(prompt)}


def budget_agent(state: TripState):
    prompt = f"""{RULES}
Destination: {state['destination']}, Days: {state['days']}, per person.
Transport ideas: {state.get('transport', {}).get('how_to_reach', [])}
Hotel ideas: {state.get('hotels', {})}
Return JSON with keys: transportation_inr, accommodation_inr, food_inr,
activities_inr, total_inr (all numbers, a realistic middle estimate for a
mid-range trip), and note (string)."""
    return {"budget": ask_json(prompt)}


def itinerary_agent(state: TripState):
    prompt = f"""{RULES}
Destination: {state['destination']}, Days: {state['days']}
Verified attractions (use these first): {state.get('attractions', [])}
Ideas: {state.get('explore', {})}
Return JSON with keys:
days: list of {{day (number), title, stops: list of {{time, place, duration, notes}}}}
tips: object with packing_checklist, safety_tips, money_saving, alternative_activities
(each a list of strings).
Group nearby places on the same day. Times are suggestions only."""
    return {"itinerary": ask_json(prompt)}


def build_graph():
    g = StateGraph(TripState)
    g.add_node("destination_agent", destination_agent)
    g.add_node("transport_agent", transport_agent)
    g.add_node("hotel_agent", hotel_agent)
    g.add_node("weather_agent", weather_agent)
    g.add_node("budget_agent", budget_agent)
    g.add_node("itinerary_agent", itinerary_agent)

    first = ["destination_agent", "transport_agent", "hotel_agent", "weather_agent"]
    for name in first:
        g.add_edge(START, name)
    g.add_edge(first, "budget_agent")
    g.add_edge(first, "itinerary_agent")
    g.add_edge("budget_agent", END)
    g.add_edge("itinerary_agent", END)
    return g.compile()
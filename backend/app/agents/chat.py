import json
from app.agents.llm import ask_json
from app.agents.graph import RULES


def chat_with_plan(trip: dict, message: str, history: list) -> dict:
    ai = trip.get("ai_generated", {})
    live = trip.get("verified_live", {})
    plan = {
        "destination": (live.get("location") or {}).get("name"),
        "itinerary": ai.get("itinerary"),
        "budget": ai.get("budget"),
        "verified_forecast": (live.get("weather") or {}).get("forecast"),
    }
    convo = "\n".join(f"{h['role']}: {h['text']}" for h in history[-6:])

    prompt = f"""{RULES}
You are a friendly travel assistant. Here is the traveller's current plan as JSON:
{json.dumps(plan, ensure_ascii=False)}

Recent conversation:
{convo}

Traveller's new message: {message}

Return a JSON object with exactly these keys:
- "reply": a short, helpful answer (string). Be honest that costs are estimates.
- "itinerary": if the traveller asked to change the itinerary, the COMPLETE updated
  itinerary using the same structure as above (keys "days" and "tips").
  Otherwise null.
Only change what the traveller asked for."""
    return ask_json(prompt)
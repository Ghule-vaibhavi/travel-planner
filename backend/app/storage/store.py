import json
import threading
import uuid
from pathlib import Path

FILE = Path(__file__).parent / "trips.json"
_lock = threading.Lock()
MAX_ITEMS = 200


def _read():
    if not FILE.exists():
        return {"cache": {}, "trips": {}}
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"cache": {}, "trips": {}}


def _write(data):
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(destination: str, days: int) -> str:
    return f"{destination.strip().lower()}|{days}"


def get_cached(destination: str, days: int):
    with _lock:
        return _read()["cache"].get(_key(destination, days))


def save_plan(destination: str, days: int, plan: dict) -> str:
    trip_id = uuid.uuid4().hex[:10]
    with _lock:
        data = _read()
        data["cache"][_key(destination, days)] = plan["ai_generated"]
        data["trips"][trip_id] = plan
        for section in ("cache", "trips"):
            while len(data[section]) > MAX_ITEMS:
                data[section].pop(next(iter(data[section])))
        _write(data)
    return trip_id


def get_trip(trip_id: str):
    with _lock:
        return _read()["trips"].get(trip_id)


def update_itinerary(trip_id: str, itinerary: dict) -> bool:
    with _lock:
        data = _read()
        trip = data["trips"].get(trip_id)
        if not trip:
            return False
        trip["ai_generated"]["itinerary"] = itinerary
        _write(data)
        return True
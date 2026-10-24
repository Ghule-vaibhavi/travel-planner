from fpdf import FPDF
from fpdf.enums import XPos, YPos

DISCLAIMER = (
    "Weather forecast and attraction names come from public APIs (Open-Meteo, OpenTripMap). "
    "Itinerary, costs, hotel areas and tips are AI estimates and are not live prices or availability. "
    "Please check current prices on the booking sites."
)


def _t(value) -> str:
    text = str(value if value is not None else "")
    for old, new in {"₹": "Rs. ", "–": "-", "—": "-", "‘": "'", "’": "'",
                     "“": '"', "”": '"', "•": "-"}.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def _dicts(value):
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _strs(value):
    return [str(x) for x in value] if isinstance(value, list) else []


def _rs(value) -> str:
    if isinstance(value, (int, float)):
        return f"Rs. {value:,.0f}"
    return str(value) if value not in (None, "") else "n/a"


def _line(pdf, h, text, style="", size=11, indent=0):
    pdf.set_font("Helvetica", style, size)
    pdf.set_x(pdf.l_margin + indent)
    pdf.multi_cell(0, h, _t(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _heading(pdf, text):
    pdf.ln(3)
    _line(pdf, 8, text, "B", 14)


def build_trip_pdf(trip: dict) -> bytes:
    live = trip.get("verified_live") or {}
    ai = trip.get("ai_generated") or {}
    name = ", ".join(((live.get("location") or {}).get("name") or "Your trip").split(",")[:2])

    pdf = FPDF()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()
    _line(pdf, 10, f"Travel Plan: {name}", "B", 20)
    _line(pdf, 5, DISCLAIMER, "I", 9)

    itin = ai.get("itinerary") if isinstance(ai.get("itinerary"), dict) else {}
    _heading(pdf, "Itinerary (AI suggestion)")
    for d in _dicts(itin.get("days")):
        _line(pdf, 7, f"Day {d.get('day', '')}: {d.get('title', '')}", "B", 12)
        for s in _dicts(d.get("stops")):
            _line(pdf, 6, f"{s.get('time', '')} - {s.get('place', '')} ({s.get('duration', '')})")
            if s.get("notes"):
                _line(pdf, 5, s["notes"], "", 10, indent=6)
        pdf.ln(2)

    b = ai.get("budget") if isinstance(ai.get("budget"), dict) else {}
    _heading(pdf, "Budget estimate per person (AI estimate)")
    for label, key in [("Transportation", "transportation_inr"), ("Accommodation", "accommodation_inr"),
                       ("Food", "food_inr"), ("Activities", "activities_inr")]:
        _line(pdf, 6, f"{label}: {_rs(b.get(key))}")
    _line(pdf, 7, f"Total: {_rs(b.get('total_inr'))}", "B", 12)
    if b.get("note"):
        _line(pdf, 5, b["note"], "I", 9)

    t = ai.get("transport") if isinstance(ai.get("transport"), dict) else {}
    _heading(pdf, "How to reach (AI estimate)")
    for r in _dicts(t.get("how_to_reach")):
        _line(pdf, 6, f"- {r.get('mode', '')}: {r.get('approx_duration', '')}, approx fare {_rs(r.get('approx_fare_inr'))}")

    h = ai.get("hotels") if isinstance(ai.get("hotels"), dict) else {}
    _heading(pdf, "Where to stay (AI estimate)")
    for key, title in [("budget", "Budget"), ("mid_range", "Mid-range"), ("luxury", "Luxury")]:
        _line(pdf, 6, title, "B")
        for x in _dicts(h.get(key)):
            _line(pdf, 6, f"- {x.get('area', '')} ({x.get('stay_type', '')}), approx "
                          f"{_rs(x.get('approx_price_inr_per_night'))} per night", indent=4)

    _heading(pdf, "Weather")
    _line(pdf, 6, "7-day forecast (verified live, Open-Meteo)", "B")
    for d in _dicts((live.get("weather") or {}).get("forecast")):
        _line(pdf, 6, f"{d.get('date', '')}: {d.get('temp_max', '')}/{d.get('temp_min', '')} C, "
                      f"rain chance {d.get('rain_chance', '')}%", indent=4)
    wa = ai.get("weather_advice") if isinstance(ai.get("weather_advice"), dict) else {}
    if wa.get("best_season_to_visit"):
        _line(pdf, 6, f"Best season (AI): {wa['best_season_to_visit']}")
    for c in _strs(wa.get("clothing")):
        _line(pdf, 6, f"- {c}", indent=4)

    tips = itin.get("tips") if isinstance(itin.get("tips"), dict) else {}
    _heading(pdf, "Smart suggestions (AI)")
    for key, title in [("packing_checklist", "Packing checklist"), ("safety_tips", "Safety tips"),
                       ("money_saving", "Money-saving tips"), ("alternative_activities", "Alternative activities")]:
        items = _strs(tips.get(key))
        if items:
            _line(pdf, 6, title, "B")
            for i in items:
                _line(pdf, 6, f"- {i}", indent=4)

    return bytes(pdf.output())
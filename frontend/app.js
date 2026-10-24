// Backend address. Change this when you deploy (Step 6).
const API_URL = "http://127.0.0.1:8000";

const form = document.getElementById("search-form");
const goBtn = document.getElementById("go-btn");
const loadingEl = document.getElementById("loading");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");

let map = null;
let markersLayer = null;

const LIVE = '<span class="badge live">Verified live</span>';
const AI = '<span class="badge ai">AI estimate</span>';

// ---------- helpers ----------
function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
}

function arr(x) {
    return Array.isArray(x) ? x : [];
}

function inr(n) {
    return typeof n === "number" ? "₹" + n.toLocaleString("en-IN") : esc(n ?? "n/a");
}

function weatherIcon(code) {
    if (code === 0) return "☀️";
    if (code <= 3) return "⛅";
    if (code === 45 || code === 48) return "🌫️";
    if (code >= 51 && code <= 57) return "🌦️";
    if (code >= 61 && code <= 67) return "🌧️";
    if (code >= 71 && code <= 77) return "❄️";
    if (code >= 80 && code <= 82) return "🌧️";
    if (code >= 95) return "⛈️";
    return "🌤️";
}

function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove("hidden");
}

// ---------- form ----------
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const destination = document.getElementById("destination").value.trim();
    const days = document.getElementById("days").value;
    if (destination.length < 2) return;

    errorEl.classList.add("hidden");
    resultsEl.classList.add("hidden");
    loadingEl.classList.remove("hidden");
    goBtn.disabled = true;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 150000);

    try {
        const url = `${API_URL}/api/plan?destination=${encodeURIComponent(destination)}&days=${days}`;
        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) {
            let detail = "Something went wrong. Please try again.";
            try {
                const body = await res.json();
                if (body.detail) detail = body.detail;
            } catch (_) { }
            throw new Error(detail);
        }
        const data = await res.json();
        renderAll(data);
    } catch (err) {
        if (err.name === "AbortError") {
            showError("The request took too long. Please try again.");
        } else if (err instanceof TypeError) {
            showError("Cannot reach the server. Is the backend running?");
        } else {
            showError(err.message);
        }
    } finally {
        clearTimeout(timer);
        loadingEl.classList.add("hidden");
        goBtn.disabled = false;
    }
});

// ---------- tabs ----------
document.getElementById("tabs").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
});

// ---------- render ----------
function renderAll(data) {
    const live = data.verified_live || {};
    const ai = data.ai_generated || {};
    const loc = live.location || {};

    document.getElementById("place-name").textContent = (loc.name || "").split(",").slice(0, 2).join(",");
    document.getElementById("place-coords").textContent =
        loc.lat !== undefined ? `Location: ${loc.lat.toFixed(3)}, ${loc.lon.toFixed(3)}` : "";

    renderMap(loc, arr(live.attractions && live.attractions.items));

    document.getElementById("tab-overview").innerHTML = renderOverview(ai.explore);
    document.getElementById("tab-itinerary").innerHTML = renderItinerary(ai.itinerary);
    document.getElementById("tab-transport").innerHTML = renderTransport(ai.transport);
    document.getElementById("tab-hotels").innerHTML = renderHotels(ai.hotels);
    document.getElementById("tab-weather").innerHTML = renderWeather(live.weather, ai.weather_advice);
    document.getElementById("tab-budget").innerHTML = renderBudget(ai.budget);
    document.getElementById("tab-tips").innerHTML = renderTips(ai.itinerary);
    if (typeof onPlanReady === "function") onPlanReady(data);
    resultsEl.classList.remove("hidden");
    setTimeout(() => map && map.invalidateSize(), 150);
    resultsEl.scrollIntoView({ behavior: "smooth" });
}

function renderMap(loc, attractions) {
    if (loc.lat === undefined) return;
    if (!map) {
        map = L.map("map");
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        markersLayer = L.layerGroup().addTo(map);
    }
    markersLayer.clearLayers();

    const points = [[loc.lat, loc.lon]];
    L.marker([loc.lat, loc.lon]).addTo(markersLayer).bindPopup("<b>Destination</b>");

    attractions.forEach((a) => {
        L.marker([a.lat, a.lon]).addTo(markersLayer).bindPopup(esc(a.name));
        points.push([a.lat, a.lon]);
    });

    if (points.length > 1) {
        map.fitBounds(points, { padding: [30, 30] });
    } else {
        map.setView(points[0], 12);
    }

    document.getElementById("map-note").innerHTML = attractions.length
        ? `${LIVE} Attraction pins come from OpenTripMap.`
        : "No attraction pins yet. Add your OpenTripMap key to backend/.env to see them.";
}

function renderOverview(explore) {
    const e = explore || {};
    const sections = [
        ["famous_attractions", "🏛️ Famous attractions"],
        ["hidden_gems", "💎 Hidden gems"],
        ["local_food", "🍛 Local food"],
        ["activities", "🎯 Activities"],
        ["cultural_experiences", "🎭 Cultural experiences"],
    ];
    return `<p>${AI}</p>` + sections.map(([key, title]) => {
        const cards = arr(e[key]).map((it) => {
            if (typeof it === "string") return `<div class="card"><p>${esc(it)}</p></div>`;
            return `<div class="card"><h4>${esc(it.name)}</h4><p>${esc(it.description)}</p></div>`;
        }).join("");
        return `<h3>${title}</h3><div class="grid">${cards || '<p class="muted">No data.</p>'}</div>`;
    }).join("");
}

function renderItinerary(it) {
    const days = arr(it && it.days);
    if (!days.length) return '<p class="muted">No itinerary was generated.</p>';
    return `<p>${AI} Times are suggestions only.</p>` + days.map((d) => `
    <div class="day">
      <h3>Day ${esc(d.day)}: ${esc(d.title)}</h3>
      ${arr(d.stops).map((s) => `
        <div class="stop">
          <div class="time">${esc(s.time)}</div>
          <div>
            <strong>${esc(s.place)}</strong>
            ${s.duration ? `<span class="muted"> · ${esc(s.duration)}</span>` : ""}
            <p>${esc(s.notes)}</p>
          </div>
        </div>`).join("")}
    </div>`).join("");
}

function linkButtons(links) {
    return arr(links).map((l) =>
        `<a class="btn-link" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)}</a>`
    ).join("");
}

function renderTransport(t) {
    if (!t) return '<p class="muted">No transport data.</p>';
    const reach = arr(t.how_to_reach).map((r) => `
    <div class="card">
      <h4>${esc(r.mode)}</h4>
      <p>Time: ${esc(r.approx_duration)}</p>
      <p>Fare: ${inr(r.approx_fare_inr)}</p>
      <p class="muted">${esc(r.tip)}</p>
    </div>`).join("");
    const local = arr(t.local_transport).map((r) => `
    <div class="card">
      <h4>${esc(r.mode)}</h4>
      <p>Cost: ${inr(r.approx_cost_inr)}</p>
      <p class="muted">${esc(r.tip)}</p>
    </div>`).join("");
    return `
    <p>${AI} Fares and times are approximate. Check live schedules and prices on the booking sites.</p>
    <h3>🚆 How to reach</h3><div class="grid">${reach}</div>
    <h3>🚕 Local transport</h3><div class="grid">${local}</div>
    <h3>Booking links</h3>${linkButtons(t.booking_links)}`;
}

function renderHotels(h) {
    if (!h) return '<p class="muted">No hotel data.</p>';
    const tiers = [["budget", "💰 Budget"], ["mid_range", "🏨 Mid-range"], ["luxury", "✨ Luxury"]];
    const body = tiers.map(([key, title]) => {
        const cards = arr(h[key]).map((x) => `
      <div class="card">
        <h4>${esc(x.area)}</h4>
        <p>${esc(x.stay_type)}</p>
        <p>Approx. per night: ${inr(x.approx_price_inr_per_night)}</p>
        <p class="muted">${arr(x.amenities).map(esc).join(", ")}</p>
        <p>${esc(x.why)}</p>
      </div>`).join("");
        return `<h3>${title}</h3><div class="grid">${cards}</div>`;
    }).join("");
    return `
    <p>${AI} These are areas and stay types, not live availability, prices, or ratings.</p>
    ${body}
    <h3>Find real hotels</h3>${linkButtons(h.booking_links)}`;
}

function renderWeather(liveWeather, advice) {
    const forecast = arr(liveWeather && liveWeather.forecast);
    const cards = forecast.map((d) => `
    <div class="card weather-card">
      <div class="icon">${weatherIcon(d.weather_code)}</div>
      <strong>${esc(d.date)}</strong>
      <p>${esc(d.temp_max)}° / ${esc(d.temp_min)}°C</p>
      <p class="muted">Rain chance: ${esc(d.rain_chance)}%</p>
    </div>`).join("");
    const a = advice || {};
    const list = (items) => `<ul>${arr(items).map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`;
    return `
    <h3>7-day forecast ${LIVE}</h3>
    <div class="grid">${cards || '<p class="muted">Forecast unavailable.</p>'}</div>
    <h3>Weather advice ${AI}</h3>
    <div class="card"><h4>Best season to visit</h4><p>${esc(a.best_season_to_visit)}</p></div>
    <h3>What to wear</h3>${list(a.clothing)}
    <h3>If the weather turns bad</h3>${list(a.weather_based_alternatives)}`;
}

function renderBudget(b) {
    if (!b) return '<p class="muted">No budget data.</p>';
    return `
    <p>${AI} Approximate cost per person for a mid-range trip, not a quote.</p>
    <table class="budget">
      <tr><td>🚆 Transportation</td><td>${inr(b.transportation_inr)}</td></tr>
      <tr><td>🏨 Accommodation</td><td>${inr(b.accommodation_inr)}</td></tr>
      <tr><td>🍽️ Food</td><td>${inr(b.food_inr)}</td></tr>
      <tr><td>🎟️ Activities</td><td>${inr(b.activities_inr)}</td></tr>
      <tr class="total"><td>Total estimate</td><td>${inr(b.total_inr)}</td></tr>
    </table>
    <p class="muted">${esc(b.note)}</p>`;
}

function renderTips(it) {
    const t = (it && it.tips) || {};
    const checklist = (items) =>
        `<ul class="checklist">${arr(items).map((i) => `<li><label><input type="checkbox"> ${esc(i)}</label></li>`).join("")}</ul>`;
    const list = (items) => `<ul>${arr(items).map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`;
    return `
    <p>${AI}</p>
    <h3>🎒 Packing checklist</h3>${checklist(t.packing_checklist)}
    <h3>🛡️ Safety tips</h3>${list(t.safety_tips)}
    <h3>💸 Money-saving tips</h3>${list(t.money_saving)}
    <h3>🔄 Alternative activities</h3>${list(t.alternative_activities)}`;
}
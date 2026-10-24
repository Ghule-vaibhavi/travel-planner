// Chatbot + PDF button. Loaded after app.js, so it can reuse API_URL, renderItinerary, renderTips.

let currentTripId = null;
let chatHistory = [];

const chatLogEl = document.getElementById("chat-log");
const chatFormEl = document.getElementById("chat-form");
const chatInputEl = document.getElementById("chat-input");
const chatSendEl = document.getElementById("chat-send");
const pdfBtnEl = document.getElementById("pdf-btn");
const cacheNoteEl = document.getElementById("cache-note");

// app.js calls this every time a new plan is shown
function onPlanReady(data) {
    currentTripId = data.trip_id || null;
    chatHistory = [];
    chatLogEl.innerHTML = "";

    if (currentTripId) {
        pdfBtnEl.href = `${API_URL}/api/trips/${currentTripId}/pdf`;
        pdfBtnEl.classList.remove("hidden");
    } else {
        pdfBtnEl.classList.add("hidden");
    }

    if (data.from_cache) {
        cacheNoteEl.textContent =
            "The AI part of this plan was reused from a saved copy. The weather and map data are fresh.";
        cacheNoteEl.classList.remove("hidden");
    } else {
        cacheNoteEl.classList.add("hidden");
    }

    addMessage("bot", "Hi! Ask me anything about this trip, or tell me what to change in your itinerary.");
}

function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = text;
    chatLogEl.appendChild(div);
    chatLogEl.scrollTop = chatLogEl.scrollHeight;
    return div;
}

chatFormEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = chatInputEl.value.trim();
    if (!message || !currentTripId) return;

    addMessage("user", message);
    chatInputEl.value = "";
    chatSendEl.disabled = true;
    const bubble = addMessage("bot", "Thinking...");

    try {
        const res = await fetch(`${API_URL}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                trip_id: currentTripId,
                message: message,
                history: chatHistory.slice(-6),
            }),
        });

        if (!res.ok) {
            let detail = "Something went wrong. Please try again.";
            try {
                const body = await res.json();
                if (typeof body.detail === "string") detail = body.detail;
            } catch (_) { }
            throw new Error(detail);
        }

        const data = await res.json();
        bubble.textContent = data.reply;
        chatHistory.push({ role: "user", text: message.slice(0, 900) });
        chatHistory.push({ role: "assistant", text: String(data.reply).slice(0, 900) });

        if (data.itinerary) {
            document.getElementById("tab-itinerary").innerHTML = renderItinerary(data.itinerary);
            document.getElementById("tab-tips").innerHTML = renderTips(data.itinerary);
            bubble.textContent += "\n\n(Your itinerary was updated. See the Itinerary tab.)";
        }
    } catch (err) {
        bubble.classList.add("err");
        bubble.textContent = err instanceof TypeError
            ? "Cannot reach the server. Is the backend running?"
            : err.message;
    } finally {
        chatSendEl.disabled = false;
        chatInputEl.focus();
    }
});
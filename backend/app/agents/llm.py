import os
import json
import time
from google import genai
from google.genai import errors


def _models():
    raw = os.getenv("GEMINI_MODELS") or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    return [m.strip() for m in raw.split(",") if m.strip()]


def _as_dict(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return data[0]
        return {"items": data}
    return {"items": [data]}


def ask_json(prompt: str) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    last_error = None
    for model in _models():
        delay = 2
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                return _as_dict(json.loads(resp.text))
            except errors.ServerError as e:
                last_error = e
                print(f"{model} busy (attempt {attempt + 1}), retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            except errors.ClientError as e:
                last_error = e
                if e.code == 429 and "PerDay" in str(e):
                    print(f"{model}: daily quota used up, trying next model")
                    break
                if e.code == 429:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
    raise last_error
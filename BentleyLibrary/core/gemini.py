import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


def extract_json_object(text):
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def first_text_part(payload):
    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            if "text" in part:
                return part["text"]
    return ""


def gemini_enabled():
    return bool(settings.GEMINI_API_KEY)


def gemini_intent(prompt):
    if not gemini_enabled():
        return None

    instruction = {
        "role": "user",
        "parts": [
            {
                "text": (
                    "You are helping a school library interpret a student request.\n"
                    "Return only valid JSON with keys: search_query, course_focus, mood, "
                    "reading_level, explanation, tags.\n"
                    "tags must be an array of short strings.\n"
                    "search_query should be concise and grounded in books a library could actually have.\n"
                    f"Student request: {prompt}"
                )
            }
        ],
    }

    body = json.dumps(
        {
            "contents": [instruction],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
    ).encode("utf-8")

    request = Request(
        GEMINI_ENDPOINT.format(model=settings.GEMINI_MODEL, key=settings.GEMINI_API_KEY),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    text = first_text_part(payload)
    parsed = extract_json_object(text)
    if not isinstance(parsed, dict):
        return None

    parsed["search_query"] = str(parsed.get("search_query", "")).strip()
    parsed["course_focus"] = str(parsed.get("course_focus", "")).strip()
    parsed["mood"] = str(parsed.get("mood", "")).strip()
    parsed["reading_level"] = str(parsed.get("reading_level", "")).strip()
    parsed["explanation"] = str(parsed.get("explanation", "")).strip()
    tags = parsed.get("tags") or []
    parsed["tags"] = [str(tag).strip() for tag in tags if str(tag).strip()][:6]
    return parsed

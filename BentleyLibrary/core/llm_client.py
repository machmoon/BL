import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from .gemini import gemini_intent


INTENT_SYSTEM_PROMPT = """You are a library retrieval planner for students.
Convert the user's request into grounded search intent for a school library catalog.
Return only valid JSON with these keys:
- search_query: short lexical query for database retrieval
- course_focus: short label like "History paper" or "Independent reading"
- reading_goal: "reading" or "research"
- mood: short optional descriptor
- reading_level: short optional descriptor
- explanation: one sentence explaining the interpretation
- tags: array of 1 to 5 lowercase topic tags
- filters: object with optional fields audience and available_only
Never include books that are not provided. Never add markdown.
"""


def llm_enabled():
    provider = settings.LLM_PROVIDER
    if provider == "gemini":
        return bool(settings.GEMINI_API_KEY)
    if provider == "openai_compatible":
        return bool(settings.LLM_BASE_URL and settings.LLM_MODEL)
    return False


def _extract_json_object(text):
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _first_choice_content(payload):
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )
    return content or ""


def _openai_compatible_json(prompt, system_prompt=INTENT_SYSTEM_PROMPT):
    endpoint = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    body = {
        "model": settings.LLM_MODEL,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return _extract_json_object(_first_choice_content(payload))


def _normalize_intent(payload, reading_goal="reading"):
    if not isinstance(payload, dict):
        return None
    search_query = str(payload.get("search_query", "")).strip()
    if not search_query:
        return None

    filters = payload.get("filters")
    if not isinstance(filters, dict):
        filters = {}

    tags = payload.get("tags")
    if not isinstance(tags, list):
        tags = []

    available_only = filters.get("available_only")
    if isinstance(available_only, str):
        available_only = available_only.strip().lower() in {"1", "true", "yes", "on"}
    return {
        "search_query": search_query,
        "course_focus": str(payload.get("course_focus", "")).strip(),
        "reading_goal": (
            "research" if str(payload.get("reading_goal", reading_goal)).strip().lower() == "research" else "reading"
        ),
        "mood": str(payload.get("mood", "")).strip(),
        "reading_level": str(payload.get("reading_level", "")).strip(),
        "explanation": str(payload.get("explanation", "")).strip(),
        "tags": [str(tag).strip().lower() for tag in tags if str(tag).strip()],
        "filters": {
            "audience": str(filters.get("audience", "")).strip(),
            "available_only": bool(available_only) if available_only is not None else False,
        },
    }


def llm_intent(prompt, reading_goal="reading"):
    if not prompt:
        return None

    provider = settings.LLM_PROVIDER
    if provider == "gemini":
        return _normalize_intent(gemini_intent(prompt), reading_goal=reading_goal)
    if provider == "openai_compatible":
        user_prompt = (
            f"Student request: {prompt}\n"
            f"Preferred mode: {reading_goal}\n"
            "Interpret this request for a school library search experience."
        )
        return _normalize_intent(
            _openai_compatible_json(user_prompt),
            reading_goal=reading_goal,
        )
    return None

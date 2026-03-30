import json
import re
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return TOKEN_RE.findall((text or "").lower())


def candidate_payload(book):
    subjects = []
    if isinstance(book.metadata, dict):
        subjects = book.metadata.get("subjects") or []
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "summary": book.summary,
        "description": book.description,
        "available_quantity": book.available_quantity,
        "quantity": book.quantity,
        "published_year": book.published_date.year if book.published_date else 0,
        "subjects": subjects[:8],
    }


def fallback_rank(query, intent, books):
    query_tokens = Counter(tokenize(query))
    intent_tokens = Counter(tokenize(" ".join(intent.get("tags", [])) + " " + intent.get("course_focus", "")))
    ranked = []
    for book in books:
        haystack = " ".join(
            [
                book.title,
                book.author,
                book.genre,
                book.summary,
                book.description,
                " ".join((book.metadata or {}).get("subjects", [])[:6]) if isinstance(book.metadata, dict) else "",
            ]
        )
        document_tokens = Counter(tokenize(haystack))
        lexical = sum(min(query_tokens[token], document_tokens[token]) for token in query_tokens)
        intent_score = sum(min(intent_tokens[token], document_tokens[token]) for token in intent_tokens)
        availability = 1.5 if book.available_quantity > 0 else 0.2
        freshness = 0.2 if book.published_date and book.published_date.year >= 2010 else 0.0
        score = lexical * 1.4 + intent_score * 1.1 + availability + freshness
        reason = "Strong topic match"
        if book.available_quantity > 0:
            reason += " and available now"
        else:
            reason += " with strong shelf relevance"
        ranked.append((book, score, reason))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def go_rank(query, intent, books):
    if not settings.GO_RERANKER_URL:
        return None

    body = json.dumps(
        {
            "query": query,
            "intent": intent,
            "books": [candidate_payload(book) for book in books],
        }
    ).encode("utf-8")
    request = Request(
        settings.GO_RERANKER_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    items = payload.get("ranked") or []
    by_id = {book.id: book for book in books}
    ranked = []
    for item in items:
        book = by_id.get(item.get("id"))
        if not book:
            continue
        ranked.append((book, float(item.get("score", 0.0)), str(item.get("reason", "")).strip()))
    return ranked or None


def rank_candidates(query, intent, books):
    return go_rank(query, intent, books) or fallback_rank(query, intent, books)

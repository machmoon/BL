from .llm_client import llm_intent
from .reranker import rank_candidates
from .search import search_books


KEYWORD_MAP = {
    "college essay": {"query": "writing biography", "headline": "Here are books that help with research and strong nonfiction voice.", "reason": "Good for students looking for strong ideas, research material, and memorable writing."},
    "fantasy": {"query": "fantasy magic", "headline": "Try a few immersive fantasy picks that move fast and have strong worlds.", "reason": "These tend to work well when students want escapist fiction with momentum."},
    "sci-fi": {"query": "science fiction dystopia", "headline": "If you want future-facing stories, these are a great place to start.", "reason": "These are solid for readers who want ideas, worldbuilding, and speculative themes."},
    "history": {"query": "history", "headline": "These history titles are strong for class projects and deeper reading.", "reason": "These are useful for classes, papers, and students who want reliable context quickly."},
    "poetry": {"query": "poetry literature", "headline": "Here are a few poetic and literary books worth browsing next.", "reason": "Best for English-heavy reading, reflection, and slower literary browsing."},
    "research": {"query": "history science biography", "headline": "These books should give you a solid research starting point.", "reason": "These titles are more likely to give you a useful angle for a class assignment."},
    "fast read": {"query": "young adult fiction", "headline": "These are quick, engaging picks that students can get into fast.", "reason": "These are easier to get through quickly without feeling throwaway."},
}


RESCUE_TOPICS = {
    "history": ["primary sources", "biography", "world history"],
    "science": ["biology", "space", "scientific discovery"],
    "english": ["literary fiction", "poetry", "essay collections"],
    "computer": ["technology", "artificial intelligence", "programming"],
    "ai": ["artificial intelligence", "technology ethics", "computer science"],
}


def search_rescue(query, reading_goal="reading"):
    lowered = (query or "").lower()
    for keyword, suggestions in RESCUE_TOPICS.items():
        if keyword in lowered:
            return {
                "headline": "Try a nearby angle",
                "reason": "The catalog may match a narrower class topic better than the exact phrasing you used.",
                "suggestions": suggestions,
            }

    if reading_goal == "research":
        suggestions = ["biography", "history", "science", "essay collections"]
        reason = "Research searches work better when they name a topic, field, or source type."
    else:
        suggestions = ["young adult fiction", "fantasy", "mystery", "memoir"]
        reason = "Reading searches usually improve when they describe mood, genre, or pace."

    return {
        "headline": "Try one of these shelf-friendly searches",
        "reason": reason,
        "suggestions": suggestions,
    }


def fallback_concierge(prompt, reading_goal="reading"):
    parsed_intent = llm_intent(prompt, reading_goal=reading_goal)
    if parsed_intent and parsed_intent.get("search_query"):
        llm_filters = {}
        audience = parsed_intent.get("filters", {}).get("audience")
        if audience:
            llm_filters["audience"] = audience
        if parsed_intent.get("filters", {}).get("available_only"):
            llm_filters["available_quantity"] = "1"

        strategy = "indexed" if parsed_intent.get("reading_goal") == "research" else "hybrid"
        response = search_books(
            query=parsed_intent["search_query"],
            filters=llm_filters,
            strategy=strategy,
            limit=12,
        )
        candidates = list(response.queryset[:12])
        ranked = rank_candidates(parsed_intent["search_query"], parsed_intent, candidates)
        books = []
        for book, _score, reason in ranked[:4]:
            books.append(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "genre": book.genre,
                    "image_url": book.image_url,
                    "summary": book.summary,
                    "reason": reason,
                }
            )
        return {
            "mode": "grounded-open-model-rag",
            "headline": parsed_intent.get("explanation") or "Here are the best grounded matches from the Bentley catalog.",
            "reason": (
                f"Interpreted this as {parsed_intent.get('course_focus') or 'general discovery'}"
                f" in {parsed_intent.get('reading_goal', reading_goal)} mode"
                f"{' with a ' + parsed_intent.get('mood') + ' tone' if parsed_intent.get('mood') else ''}."
            ),
            "suggested_query": parsed_intent["search_query"],
            "books": books,
            "intent": parsed_intent,
        }

    lowered = (prompt or "").lower()
    selected = None
    for keyword, config in KEYWORD_MAP.items():
        if keyword in lowered:
            selected = config
            break

    if not selected:
        selected = {
            "query": prompt or "student favorites",
            "headline": "Here are a few likely matches from the catalog.",
            "reason": "These are the closest matches based on the way you described what you need.",
        }

    strategy = "indexed" if reading_goal == "research" else "indexed"
    response = search_books(query=selected["query"], strategy=strategy, limit=4)
    books = []
    for book in response.queryset[:4]:
        books.append(
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "genre": book.genre,
                "image_url": book.image_url,
                "summary": book.summary,
                "reason": (
                    f"Good for {book.genre.lower() if book.genre else 'general reading'}"
                    f"{' and available now' if book.available_quantity > 0 else ' with hold-worthy demand'}."
                ),
            }
        )

    return {
        "mode": "local-guide",
        "headline": selected["headline"],
        "reason": selected["reason"],
        "suggested_query": selected["query"],
        "books": books,
        "goal": reading_goal,
    }

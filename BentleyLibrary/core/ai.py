from .gemini import gemini_intent
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


def fallback_concierge(prompt):
    parsed_intent = gemini_intent(prompt)
    if parsed_intent and parsed_intent.get("search_query"):
        response = search_books(query=parsed_intent["search_query"], strategy="hybrid", limit=12)
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
            "mode": "grounded-gemini-rag",
            "headline": parsed_intent.get("explanation") or "Here are the best grounded matches from the Bentley catalog.",
            "reason": (
                f"Interpreted this as {parsed_intent.get('course_focus') or 'general discovery'}"
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

    response = search_books(query=selected["query"], strategy="indexed", limit=4)
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
    }

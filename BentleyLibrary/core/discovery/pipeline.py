from dataclasses import dataclass
from typing import Optional

from core.ai import search_rescue
from core.search import search_books


@dataclass
class SearchPipelineResponse:
    response: object
    reading_goal: str
    filters: dict
    rescue: Optional[dict]


def run_search_pipeline(query="", reading_goal="reading", filters=None, limit=200):
    reading_goal = (reading_goal or "reading").strip().lower()
    if reading_goal not in {"reading", "research"}:
        reading_goal = "reading"

    filters = dict(filters or {})
    if reading_goal == "research" and not filters.get("audience"):
        filters["audience"] = "Upper School"

    strategy = "indexed" if reading_goal == "research" else "auto"
    response = search_books(query=query, filters=filters, strategy=strategy, limit=limit)
    rescue = search_rescue(query, reading_goal=reading_goal) if query else None
    return SearchPipelineResponse(
        response=response,
        reading_goal=reading_goal,
        filters=filters,
        rescue=rescue,
    )

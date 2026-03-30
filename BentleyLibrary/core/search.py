import math
import re
import time
from collections import Counter
from dataclasses import dataclass

from django.db import connection
from django.db.models import Case, IntegerField, Q, Value, When

from .models import Bookinventory


TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class SearchResponse:
    queryset: object
    strategy: str
    latency_ms: float
    ranked_ids: list


def postgres_search_vector():
    from django.contrib.postgres.search import SearchVector

    return (
        SearchVector("title", weight="A", config="english")
        + SearchVector("author", weight="A", config="english")
        + SearchVector("publisher", weight="B", config="english")
        + SearchVector("genre", weight="B", config="english")
        + SearchVector("description", weight="C", config="english")
        + SearchVector("summary", weight="C", config="english")
        + SearchVector("search_document", weight="D", config="english")
    )


def tokenize(text):
    return TOKEN_RE.findall((text or "").lower())


def semantic_score(query, document):
    query_tokens = tokenize(query)
    document_tokens = tokenize(document)
    if not query_tokens or not document_tokens:
        return 0.0

    query_counts = Counter(query_tokens)
    document_counts = Counter(document_tokens)
    overlap = sum(min(query_counts[token], document_counts[token]) for token in query_counts)
    norm = math.sqrt(sum(count * count for count in query_counts.values())) * math.sqrt(
        sum(count * count for count in document_counts.values())
    )
    if not norm:
        return 0.0
    return overlap / norm


def apply_filters(queryset, filters):
    published_date_start = filters.get("published_date_start")
    published_date_end = filters.get("published_date_end")
    available_quantity = filters.get("available_quantity")
    title = filters.get("title")
    author = filters.get("author")
    publisher = filters.get("publisher")
    isbn = filters.get("isbn")
    genre = filters.get("genre")
    audience = filters.get("audience")

    if published_date_start:
        queryset = queryset.filter(published_date__gte=published_date_start)
    if published_date_end:
        queryset = queryset.filter(published_date__lte=published_date_end)
    if available_quantity:
        queryset = queryset.filter(available_quantity=available_quantity)
    if title:
        queryset = queryset.filter(title__icontains=title)
    if author:
        queryset = queryset.filter(author__icontains=author)
    if publisher:
        queryset = queryset.filter(publisher__icontains=publisher)
    if isbn:
        queryset = queryset.filter(isbn__icontains=isbn)
    if genre:
        queryset = queryset.filter(genre__icontains=genre)
    if audience:
        queryset = queryset.filter(audience__iexact=audience)
    return queryset


def order_by_ranked_ids(queryset, ranked_ids):
    if not ranked_ids:
        return queryset.none()

    preserved = Case(
        *[When(pk=pk, then=Value(position)) for position, pk in enumerate(ranked_ids)],
        output_field=IntegerField(),
    )
    return queryset.filter(pk__in=ranked_ids).order_by(preserved)


def baseline_queryset(query, filters):
    queryset = apply_filters(Bookinventory.objects.all(), filters)
    if not query:
        return queryset.order_by("title")

    filter_query = (
        Q(title__icontains=query)
        | Q(subtitle__icontains=query)
        | Q(author__icontains=query)
        | Q(publisher__icontains=query)
        | Q(description__icontains=query)
        | Q(summary__icontains=query)
        | Q(isbn__icontains=query)
        | Q(genre__icontains=query)
    )
    return queryset.filter(filter_query).order_by("title")


def sqlite_fts_ids(query, limit):
    sql = """
        SELECT rowid
        FROM bookinventory_fts
        WHERE bookinventory_fts MATCH ?
        ORDER BY bm25(bookinventory_fts)
        LIMIT ?
    """
    terms = tokenize(query)
    if not terms:
        return []

    match_query = " OR ".join(terms)
    with connection.cursor() as cursor:
        cursor.execute(sql, [match_query, limit])
        return [row[0] for row in cursor.fetchall()]


def indexed_queryset(query, filters, limit=50):
    queryset = apply_filters(Bookinventory.objects.all(), filters)
    if not query:
        return queryset.order_by("title"), []

    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchRank

        if not any(filters.values()):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM bookinventory
                    WHERE search_vector @@ plainto_tsquery('english', %s)
                    ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC, title ASC
                    LIMIT %s
                    """,
                    [query, query, limit],
                )
                ids = [row[0] for row in cursor.fetchall()]
            return order_by_ranked_ids(queryset, ids), ids

        vector = postgres_search_vector()
        search_query = SearchQuery(query, search_type="plain", config="english")
        ranked = queryset.annotate(rank=SearchRank(vector, search_query)).filter(rank__gt=0.0)
        ranked = ranked.order_by("-rank", "title")
        ids = list(ranked.values_list("id", flat=True)[:limit])
        return order_by_ranked_ids(queryset, ids), ids

    if connection.vendor == "sqlite":
        try:
            ids = sqlite_fts_ids(query, limit)
        except Exception:
            ids = []
        if ids:
            return order_by_ranked_ids(queryset, ids), ids

    prefix_query = (
        Q(title__istartswith=query)
        | Q(author__istartswith=query)
        | Q(publisher__istartswith=query)
        | Q(genre__istartswith=query)
        | Q(isbn__iexact=query)
    )
    ranked = queryset.filter(prefix_query).order_by("title")
    ids = list(ranked.values_list("id", flat=True)[:limit])
    return ranked, ids


def hybrid_queryset(query, filters, limit=50):
    queryset = apply_filters(Bookinventory.objects.all(), filters)
    indexed, indexed_ids = indexed_queryset(query, filters, limit=limit)
    candidates = list(indexed[:limit]) if indexed_ids else list(baseline_queryset(query, filters)[:limit])

    if not query:
        ids = [book.id for book in candidates]
        return order_by_ranked_ids(queryset, ids), ids

    scored = []
    total_candidates = len(candidates) or 1
    for position, book in enumerate(candidates):
        lexical_score = 1 - (position / total_candidates)
        meaning_score = semantic_score(query, book.search_document)
        freshness_score = 0.1 if book.available_quantity > 0 else 0.0
        scored.append((book.id, lexical_score * 0.65 + meaning_score * 0.3 + freshness_score * 0.05))

    scored.sort(key=lambda item: item[1], reverse=True)
    ranked_ids = [book_id for book_id, _score in scored]
    return order_by_ranked_ids(queryset, ranked_ids), ranked_ids


def search_books(query="", filters=None, strategy="auto", limit=50):
    filters = filters or {}
    requested_strategy = strategy or "auto"
    started = time.perf_counter()

    if requested_strategy == "baseline":
        queryset = baseline_queryset(query, filters)
        ranked_ids = list(queryset.values_list("id", flat=True)[:limit])
        queryset = order_by_ranked_ids(queryset, ranked_ids) if ranked_ids else queryset.none()
        actual_strategy = "baseline"
    elif requested_strategy == "indexed":
        queryset, ranked_ids = indexed_queryset(query, filters, limit=limit)
        actual_strategy = "indexed"
    else:
        actual_strategy = "hybrid" if requested_strategy in {"auto", "hybrid"} else "baseline"
        queryset, ranked_ids = hybrid_queryset(query, filters, limit=limit)

    latency_ms = (time.perf_counter() - started) * 1000
    return SearchResponse(
        queryset=queryset,
        strategy=actual_strategy,
        latency_ms=latency_ms,
        ranked_ids=ranked_ids,
    )

import json
from dataclasses import dataclass
from datetime import date
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import urlopen


OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_SEARCH = "https://www.googleapis.com/books/v1/volumes"


@dataclass
class OpenLibraryBook:
    title: str
    subtitle: str
    author: str
    isbn: str
    published_date: date
    publisher: str
    genre: str
    language: str
    audience: str
    description: str
    summary: str
    image_url: str
    metadata: dict


def fetch_json(url):
    with urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def sanitize_isbn(isbn):
    cleaned = "".join(character for character in (isbn or "") if character.isdigit())
    return cleaned[:13]


def cover_url(cover_id):
    if not cover_id:
        return ""
    return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


def parse_publish_date(first_publish_year):
    year = first_publish_year or 2020
    return date(int(year), 1, 1)


def parse_doc(doc, fallback_genre="", fallback_audience="General"):
    isbn_candidates = doc.get("isbn") or doc.get("isbn_13") or []
    isbn = ""
    for candidate in isbn_candidates:
        isbn = sanitize_isbn(candidate)
        if len(isbn) >= 10:
            break

    if not isbn:
        return None

    author_names = doc.get("author_name") or []
    publishers = doc.get("publisher") or []
    subjects = doc.get("subject") or []
    language_codes = doc.get("language") or []
    language = "English"
    if "spa" in language_codes:
        language = "Spanish"
    elif "fre" in language_codes:
        language = "French"

    title = doc.get("title") or "Untitled"
    subtitle = doc.get("subtitle") or ""
    description = (
        f"{title} is part of a student-facing collection centered on "
        f"{fallback_genre or 'library discovery'}."
    )
    summary = ", ".join(subjects[:6]) or "Student library title"

    return OpenLibraryBook(
        title=title[:255],
        subtitle=subtitle[:255],
        author=", ".join(author_names[:3])[:255] or "Unknown Author",
        isbn=isbn,
        published_date=parse_publish_date(doc.get("first_publish_year")),
        publisher=publishers[0][:255] if publishers else "Unknown Publisher",
        genre=(fallback_genre or (subjects[0] if subjects else "General"))[:120],
        language=language,
        audience=fallback_audience,
        description=description,
        summary=summary[:600],
        image_url=cover_url(doc.get("cover_i")),
        metadata={
            "subjects": subjects[:10],
            "openlibrary_key": doc.get("key", ""),
            "ratings_average": doc.get("ratings_average"),
            "ratings_count": doc.get("ratings_count"),
            "first_sentence": doc.get("first_sentence"),
        },
    )


def parse_google_item(item, fallback_genre="", fallback_audience="General"):
    volume = item.get("volumeInfo", {})
    identifiers = volume.get("industryIdentifiers") or []
    isbn = ""
    for identifier in identifiers:
        isbn = sanitize_isbn(identifier.get("identifier"))
        if len(isbn) >= 10:
            break

    if not isbn:
        return None

    authors = volume.get("authors") or []
    categories = volume.get("categories") or []
    image_links = volume.get("imageLinks") or {}
    published = volume.get("publishedDate", "")
    published_year = published[:4] if published else None

    return OpenLibraryBook(
        title=(volume.get("title") or "Untitled")[:255],
        subtitle=(volume.get("subtitle") or "")[:255],
        author=", ".join(authors[:3])[:255] or "Unknown Author",
        isbn=isbn,
        published_date=parse_publish_date(published_year),
        publisher=(volume.get("publisher") or "Unknown Publisher")[:255],
        genre=(fallback_genre or (categories[0] if categories else "General"))[:120],
        language=(volume.get("language") or "en").upper(),
        audience=fallback_audience,
        description=(volume.get("description") or "")[:2000],
        summary=", ".join(categories[:5]) or (volume.get("description") or "Student library title")[:600],
        image_url=image_links.get("thumbnail", "").replace("http://", "https://"),
        metadata={
            "google_books_id": item.get("id", ""),
            "subjects": categories[:10],
            "page_count": volume.get("pageCount"),
            "ratings_average": volume.get("averageRating"),
            "ratings_count": volume.get("ratingsCount"),
            "preview_link": volume.get("previewLink"),
        },
    )


def search_openlibrary(query, limit=12, subject=None):
    params = [f"q={quote_plus(query)}", f"limit={limit}", "language=eng"]
    if subject:
        params.append(f"subject={quote_plus(subject)}")
    url = f"{OPEN_LIBRARY_SEARCH}?{'&'.join(params)}"
    try:
        payload = fetch_json(url)
    except (HTTPError, URLError, TimeoutError):
        return []
    return payload.get("docs", [])


def search_google_books(query, limit=12, subject=None):
    composed_query = query
    if subject:
        composed_query = f"{query} subject:{subject}"
    url = (
        f"{GOOGLE_BOOKS_SEARCH}?q={quote_plus(composed_query)}"
        f"&maxResults={limit}&printType=books&langRestrict=en"
    )
    try:
        payload = fetch_json(url)
    except (HTTPError, URLError, TimeoutError):
        return []
    return payload.get("items", [])


def search_real_books(query, limit=12, subject=None, fallback_genre="", fallback_audience="General"):
    parsed = []
    seen = set()

    for doc in search_openlibrary(query, limit=limit * 2, subject=subject):
        book = parse_doc(doc, fallback_genre=fallback_genre, fallback_audience=fallback_audience)
        if not book or book.isbn in seen:
            continue
        parsed.append(book)
        seen.add(book.isbn)
        if len(parsed) >= limit:
            return parsed

    for item in search_google_books(query, limit=limit * 2, subject=subject):
        book = parse_google_item(item, fallback_genre=fallback_genre, fallback_audience=fallback_audience)
        if not book or book.isbn in seen:
            continue
        parsed.append(book)
        seen.add(book.isbn)
        if len(parsed) >= limit:
            break

    return parsed


def lookup_by_isbn(isbn):
    cleaned = sanitize_isbn(isbn)
    if not cleaned:
        return None

    docs = search_openlibrary(cleaned, limit=5)
    for doc in docs:
        parsed = parse_doc(doc)
        if parsed and parsed.isbn.endswith(cleaned[-10:]):
            return parsed
    for doc in docs:
        parsed = parse_doc(doc)
        if parsed:
            return parsed
    for item in search_google_books(f"isbn:{cleaned}", limit=5):
        parsed = parse_google_item(item)
        if parsed:
            return parsed
    return None

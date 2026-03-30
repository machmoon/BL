from collections import Counter

from core.models import LibraryRole


COURSE_TOPICS = {
    "history": "History paper",
    "biography": "Humanities research",
    "science": "Science class",
    "technology": "CS / AI",
    "computer": "CS / AI",
    "fiction": "Independent reading",
    "fantasy": "Fast fiction",
    "young adult": "Fast read",
    "poetry": "English seminar",
    "writing": "Essay inspiration",
}


ROLE_MANAGE_LOANS = {
    LibraryRole.LIBRARIAN,
    LibraryRole.CURATOR,
    LibraryRole.ADMIN,
}


def metadata_subjects(book):
    if not isinstance(book.metadata, dict):
        return []
    subjects = book.metadata.get("subjects") or []
    if isinstance(subjects, list):
        return [str(subject).strip() for subject in subjects if subject]
    return []


def infer_course_tag(book):
    haystack = " ".join(
        [
            book.genre or "",
            book.summary or "",
            book.description or "",
            " ".join(metadata_subjects(book)[:6]),
        ]
    ).lower()
    for keyword, label in COURSE_TOPICS.items():
        if keyword in haystack:
            return label
    return "Student pick"


def estimate_wait_label(book):
    active_loans = max(book.quantity - book.available_quantity, 0)
    if book.available_quantity > 0:
        return "Available now"
    if active_loans <= 1:
        return "Likely back soon"
    if active_loans <= 3:
        return "About 1 to 2 weeks"
    return "Waitlist moving slowly"


def present_book(book):
    tags = []
    course_tag = infer_course_tag(book)
    tags.append(course_tag)
    tags.append("Available now" if book.available_quantity > 0 else "Waitlist")
    if book.audience:
        tags.append(book.audience)
    lowered_genre = (book.genre or "").lower()
    lowered_summary = (book.summary or "").lower()
    if "young adult" in lowered_genre or "fiction" in lowered_genre:
        tags.append("Fast read")
    if any(keyword in lowered_summary for keyword in ["history", "science", "biography", "research"]):
        tags.append("Research friendly")

    return {
        "instance": book,
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "image_url": book.image_url,
        "summary": book.summary,
        "description": book.description,
        "publisher": book.publisher,
        "isbn": book.isbn,
        "quantity": book.quantity,
        "available_quantity": book.available_quantity,
        "published_date": book.published_date,
        "language": book.language,
        "audience": book.audience,
        "course_tag": course_tag,
        "quick_tags": tags[:4],
        "wait_label": estimate_wait_label(book),
        "primary_cta": "Borrow now" if book.available_quantity > 0 else "Place hold",
        "secondary_cta": "See details",
    }


def present_books(books):
    return [present_book(book) for book in books]


def genre_counts(books):
    counts = Counter(genre for genre in books if genre)
    return [{"name": name, "count": count} for name, count in counts.most_common(4)]

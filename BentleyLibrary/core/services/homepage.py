from collections import Counter

from core.models import Bookinventory, HoldRequest, HoldStatus, Loan, LoanStatus
from core.presenters.books import present_books


def build_homepage_context(user):
    featured_books = present_books(
        Bookinventory.objects.exclude(image_url="").order_by("?")[:6]
    )
    latest_books = present_books(
        Bookinventory.objects.order_by("-published_date", "title")[:5]
    )
    student_picks = present_books(
        Bookinventory.objects.filter(
            audience__in=["Upper School", "Middle School", "General"]
        ).order_by("?")[:6]
    )
    available_now = present_books(
        Bookinventory.objects.filter(available_quantity__gt=0).exclude(image_url="").order_by("?")[:6]
    )

    most_wanted_ids = (
        HoldRequest.objects.filter(status__in=[HoldStatus.PENDING, HoldStatus.READY])
        .values_list("inventory_id", flat=True)
    )
    most_wanted = present_books(
        Bookinventory.objects.filter(id__in=most_wanted_ids).distinct()[:4]
    )

    genre_counts = Counter(
        genre for genre in Bookinventory.objects.values_list("genre", flat=True) if genre
    )
    trending_genres = [{"name": name, "count": count} for name, count in genre_counts.most_common(4)]
    if not trending_genres:
        trending_genres = [
            {"name": "Student Favorites", "count": len(featured_books)},
            {"name": "Research", "count": len(latest_books)},
            {"name": "Fiction", "count": len(student_picks)},
        ]

    context = {
        "featured_books": featured_books,
        "latest_books": latest_books,
        "student_picks": student_picks,
        "available_now": available_now,
        "most_wanted": most_wanted,
        "trending_genres": trending_genres,
        "library_news": [
            {
                "title": "Research sprint season is here",
                "body": "Use the advanced search builder to find stronger sources faster for seminar papers and capstones.",
                "tag": "Study Tip",
            },
            {
                "title": "New arrivals in the catalog",
                "body": "Fresh fantasy, biography, and tech books are now mixed into the main collection.",
                "tag": "New Shelf",
            },
            {
                "title": "Try the AI librarian",
                "body": "Ask for a quick recommendation and convert the answer into a deeper catalog search.",
                "tag": "Beta",
            },
        ],
        "active_loans": Loan.objects.filter(status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]).count(),
        "active_holds": HoldRequest.objects.filter(status__in=[HoldStatus.PENDING, HoldStatus.READY]).count(),
        "continue_loans": [],
    }
    if user.is_authenticated:
        continue_loans = user.loans.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        ).select_related("inventory")[:3]
        context["continue_loans"] = present_books([loan.inventory for loan in continue_loans])
    return context

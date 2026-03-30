import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView

from .models import (
    BookCopy,
    Bookinventory,
    CopyStatus,
    HoldRequest,
    HoldStatus,
    LibraryRole,
    Loan,
    LoanStatus,
    Log,
)
from .search import search_books

logger = logging.getLogger(__name__)

CHECKOUT_TEMPLATE = "core/checkout.html"
CHECKIN_TEMPLATE = "core/checkin.html"
SEARCH_RESULTS_TEMPLATE = "core/search_results.html"
BOOK_PAGE_TEMPLATE = "core/book_page.html"
RESOURCE_TEMPLATE = "core/resource.html"
ADVANCED_SEARCH_TEMPLATE = "core/advanced_search_results.html"
ACCOUNT_TEMPLATE = "core/account.html"
INDEX_TEMPLATE = "core/index.html"

ADVANCED_SEARCH_FIELDS = {
    "any_field": "any_field",
    "title": "title",
    "author": "author",
    "publisher": "publisher",
    "isbn": "isbn",
    "ISBN": "isbn",
    "description": "description",
    "genre": "genre",
    "audience": "audience",
}
ADVANCED_SEARCH_OPERATORS = {
    "contains",
    "icontains",
    "exact",
    "iexact",
    "startswith",
    "istartswith",
    "endswith",
    "iendswith",
}
LOAN_PERIOD_DAYS = 21
ROLE_MANAGE_LOANS = {
    LibraryRole.LIBRARIAN,
    LibraryRole.CURATOR,
    LibraryRole.ADMIN,
}


def extract_user_identity(request):
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip()

    if request.user.is_authenticated:
        first_name = first_name or request.user.first_name or request.user.username
        last_name = last_name or request.user.last_name or "Library User"
        email = email or request.user.email

    return first_name, last_name, email


def ensure_copy_records(book):
    existing = book.copies.count()
    if existing >= book.quantity:
        return

    for index in range(existing + 1, book.quantity + 1):
        BookCopy.objects.create(
            inventory=book,
            barcode=f"LIB-{book.isbn}-{index:04d}",
        )


def sync_inventory_counts(book):
    total_copies = book.copies.count()
    available_copies = book.copies.filter(status=CopyStatus.AVAILABLE).count()
    desired_quantity = max(book.quantity, total_copies)

    Bookinventory.objects.filter(pk=book.pk).update(
        quantity=desired_quantity,
        available_quantity=available_copies,
    )
    book.refresh_from_db(fields=["quantity", "available_quantity"])


def grant_ready_hold(book):
    ready_hold = book.holds.filter(status=HoldStatus.PENDING).order_by("requested_at").first()
    available_copy = book.copies.filter(status=CopyStatus.AVAILABLE).order_by("barcode").first()
    if not ready_hold or not available_copy:
        return

    ready_hold.status = HoldStatus.READY
    ready_hold.expires_at = timezone.now() + timedelta(days=3)
    ready_hold.save(update_fields=["status", "expires_at"])

    available_copy.status = CopyStatus.ON_HOLD
    available_copy.due_back_date = ready_hold.expires_at.date()
    available_copy.save(update_fields=["status", "due_back_date"])


def checkout(request, isbn):
    if request.method == "POST":
        first_name, last_name, email = extract_user_identity(request)

        if not all([first_name, last_name, email]):
            messages.error(request, "Please fill in all required fields.")
            return render(
                request,
                CHECKOUT_TEMPLATE,
                {"error_message": "Please fill in all required fields."},
            )

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Please enter a valid email address.")
            return render(
                request,
                CHECKOUT_TEMPLATE,
                {"error_message": "Please enter a valid email address."},
            )

        try:
            with transaction.atomic():
                book = Bookinventory.objects.select_for_update().get(isbn=isbn)
                ensure_copy_records(book)
                available_copy = book.copies.select_for_update().filter(
                    status=CopyStatus.AVAILABLE
                ).order_by("barcode").first()

                if not available_copy:
                    sync_inventory_counts(book)
                    messages.error(request, "No copies available to check out.")
                    return render(
                        request,
                        CHECKOUT_TEMPLATE,
                        {"error_message": "No copies available to check out."},
                    )

                if request.user.is_authenticated and hasattr(request.user, "library_profile"):
                    active_loans = request.user.loans.filter(
                        status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
                    ).count()
                    if active_loans >= request.user.library_profile.max_active_loans:
                        messages.error(request, "You have reached your active loan limit.")
                        return render(
                            request,
                            CHECKOUT_TEMPLATE,
                            {"error_message": "You have reached your active loan limit."},
                        )

                timestamp = timezone.localtime()
                due_at = timestamp + timedelta(days=LOAN_PERIOD_DAYS)
                loan = Loan.objects.create(
                    inventory=book,
                    copy=available_copy,
                    borrower=request.user if request.user.is_authenticated else None,
                    processed_by=request.user if request.user.is_authenticated else None,
                    borrower_email_snapshot=email,
                    checked_out_at=timestamp,
                    due_at=due_at,
                    status=LoanStatus.ACTIVE,
                )
                Log.objects.create(
                    book=book,
                    loan=loan,
                    title=book.title,
                    author=book.author,
                    publisher=book.publisher,
                    publication_date=book.published_date,
                    isbn=book.isbn,
                    borrower_first_name=first_name,
                    borrower_last_name=last_name,
                    borrower_email=email,
                    borrowed_date=timestamp.date(),
                    borrowed_time=timestamp.time().replace(microsecond=0),
                )

                available_copy.status = CopyStatus.ON_LOAN
                available_copy.due_back_date = due_at.date()
                available_copy.last_circulated_at = timestamp
                available_copy.save(
                    update_fields=["status", "due_back_date", "last_circulated_at"]
                )
                sync_inventory_counts(book)

                logger.info("Book %s checked out by %s", isbn, email)
                messages.success(
                    request,
                    f"Thanks for checking out the book. Due back on {due_at.date().isoformat()}.",
                )
                return redirect("index")

        except ObjectDoesNotExist:
            logger.warning("Checkout attempted for non-existent ISBN: %s", isbn)
            messages.error(request, "Book not found in inventory.")
            return render(
                request,
                CHECKOUT_TEMPLATE,
                {"error_message": "Book not found in inventory."},
            )
        except Exception as exc:
            logger.error("Error during checkout: %s", str(exc))
            messages.error(request, "An error occurred during checkout. Please try again.")
            return render(
                request,
                CHECKOUT_TEMPLATE,
                {
                    "error_message": "An error occurred during checkout. Please try again."
                },
            )

    initial_context = {}
    if request.user.is_authenticated:
        initial_context = {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        }
    return render(request, CHECKOUT_TEMPLATE, initial_context)


def checkin(request):
    if request.method == "POST":
        isbn = request.POST.get("isbn", "").strip()

        if not isbn:
            messages.error(request, "Please provide an ISBN.")
            return render(
                request,
                CHECKIN_TEMPLATE,
                {"error_message": "Please provide an ISBN."},
            )

        try:
            with transaction.atomic():
                book = Bookinventory.objects.select_for_update().get(isbn=isbn)
                expected_checked_out = book.available_quantity < book.quantity
                ensure_copy_records(book)
                loan = book.loans.select_for_update().filter(
                    status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE],
                    returned_at__isnull=True,
                ).select_related("copy").order_by("checked_out_at").first()

                if not loan:
                    sync_inventory_counts(book)
                    if expected_checked_out:
                        messages.error(request, "No check-out record found for this book.")
                        return render(
                            request,
                            CHECKIN_TEMPLATE,
                            {"error_message": "No check-out record found for this book."},
                        )
                    messages.error(request, "This book is not checked out.")
                    return render(
                        request,
                        CHECKIN_TEMPLATE,
                        {"error_message": "This book is not checked out."},
                    )

                timestamp = timezone.localtime()
                loan.status = LoanStatus.RETURNED
                loan.returned_at = timestamp
                loan.save(update_fields=["status", "returned_at"])

                loan.copy.status = CopyStatus.AVAILABLE
                loan.copy.due_back_date = None
                loan.copy.last_circulated_at = timestamp
                loan.copy.save(update_fields=["status", "due_back_date", "last_circulated_at"])

                log_entry = Log.objects.filter(
                    loan=loan,
                    returned_date__isnull=True,
                ).order_by("-borrowed_date", "-borrowed_time").first()
                if not log_entry:
                    log_entry = Log.objects.filter(
                        book=book,
                        returned_date__isnull=True,
                    ).order_by("-borrowed_date", "-borrowed_time").first()

                if log_entry:
                    log_entry.returned_date = timestamp.date()
                    log_entry.returned_time = timestamp.time().replace(microsecond=0)
                    log_entry.save(update_fields=["returned_date", "returned_time"])

                sync_inventory_counts(book)
                grant_ready_hold(book)
                sync_inventory_counts(book)

                logger.info("Book %s checked in", isbn)
                messages.success(request, "Book checked in successfully.")
                return redirect("index")

        except ObjectDoesNotExist:
            logger.warning("Checkin attempted for non-existent ISBN: %s", isbn)
            messages.error(request, "Book not found in inventory.")
            return render(
                request,
                CHECKIN_TEMPLATE,
                {"error_message": "Book not found in inventory."},
            )
        except Exception as exc:
            logger.error("Error during checkin: %s", str(exc))
            messages.error(request, "An error occurred during checkin. Please try again.")
            return render(
                request,
                CHECKIN_TEMPLATE,
                {"error_message": "An error occurred during checkin. Please try again."},
            )

    return render(request, CHECKIN_TEMPLATE)


class AdvancedSearchResults(ListView):
    model = Bookinventory
    template_name = ADVANCED_SEARCH_TEMPLATE
    context_object_name = "results"

    def get_queryset(self):
        queryset = super().get_queryset()
        search_type = self.request.GET.get("search_type")
        field = self.request.GET.getlist("field[]")
        operator = self.request.GET.getlist("operator[]")
        search_term = self.request.GET.getlist("search_term[]")
        logical_operator = self.request.GET.getlist("logical_operator[]")
        filter_query = Q()

        if search_type in ["everything", "catalog"] and field:
            queries = []
            for i in range(len(field)):
                if i >= len(search_term) or not search_term[i]:
                    continue

                field_name = ADVANCED_SEARCH_FIELDS.get(field[i])
                if not field_name:
                    continue

                if field_name == "any_field":
                    sub_query = (
                        Q(title__icontains=search_term[i])
                        | Q(author__icontains=search_term[i])
                        | Q(publisher__icontains=search_term[i])
                        | Q(isbn__icontains=search_term[i])
                        | Q(description__icontains=search_term[i])
                        | Q(genre__icontains=search_term[i])
                    )
                    queries.append(sub_query)
                else:
                    operator_name = operator[i] if i < len(operator) else ""
                    if operator_name not in ADVANCED_SEARCH_OPERATORS:
                        operator_name = "icontains"
                    queries.append(Q(**{f"{field_name}__{operator_name}": search_term[i]}))

            if queries:
                filter_query = queries[0]
                for i in range(1, len(queries)):
                    logical = logical_operator[i - 1] if i - 1 < len(logical_operator) else "OR"
                    if logical == "AND":
                        filter_query &= queries[i]
                    elif logical == "NOT":
                        filter_query &= ~queries[i]
                    else:
                        filter_query |= queries[i]

        published_date_start_filter = self.request.GET.get("published_date_start", "")
        published_date_end_filter = self.request.GET.get("published_date_end", "")

        if published_date_start_filter:
            filter_query &= Q(published_date__gte=published_date_start_filter)
        if published_date_end_filter:
            filter_query &= Q(published_date__lte=published_date_end_filter)

        if any(
            [
                search_type,
                field,
                operator,
                search_term,
                logical_operator,
                published_date_start_filter,
                published_date_end_filter,
            ]
        ):
            queryset = queryset.filter(filter_query)
        else:
            queryset = queryset.none()

        return queryset.order_by("title")


def resource_view(request):
    return render(request, RESOURCE_TEMPLATE)


def search_results(request):
    query = request.GET.get("q", "").strip()
    strategy = request.GET.get("strategy", "auto").strip() or "auto"
    filters = {
        "published_date_start": request.GET.get("published_date_start", ""),
        "published_date_end": request.GET.get("published_date_end", ""),
        "available_quantity": request.GET.get("available_quantity", ""),
        "title": request.GET.get("title", ""),
        "author": request.GET.get("author", ""),
        "publisher": request.GET.get("publisher", ""),
        "isbn": request.GET.get("isbn", "") or request.GET.get("ISBN", ""),
        "genre": request.GET.get("genre", ""),
        "audience": request.GET.get("audience", ""),
    }

    response = search_books(query=query, filters=filters, strategy=strategy, limit=200)
    results = response.queryset
    active_loans = Loan.objects.filter(
        inventory_id__in=results.values("id"),
        status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE],
        returned_at__isnull=True,
    )
    borrowed_book_ids = list(active_loans.values_list("inventory_id", flat=True))

    context = {
        "results": results,
        "query": query,
        "published_date_start_filter": filters["published_date_start"],
        "published_date_end_filter": filters["published_date_end"],
        "available_quantity_filter": filters["available_quantity"],
        "title": filters["title"],
        "author": filters["author"],
        "publisher": filters["publisher"],
        "isbn": filters["isbn"],
        "genre": filters["genre"],
        "audience": filters["audience"],
        "borrowed_books": active_loans,
        "borrowed_book_ids": borrowed_book_ids,
        "search_strategy": response.strategy,
        "search_elapsed_ms": round(response.latency_ms, 2),
    }
    return render(request, SEARCH_RESULTS_TEMPLATE, context)


def book_page(request, book_id):
    book = get_object_or_404(Bookinventory.objects.prefetch_related("copies", "holds"), id=book_id)
    active_loans = book.loans.filter(
        status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE],
        returned_at__isnull=True,
    ).select_related("borrower", "copy")
    holds = book.holds.filter(status__in=[HoldStatus.PENDING, HoldStatus.READY]).select_related(
        "requester"
    )
    context = {
        "book": book,
        "borrowed_books": active_loans,
        "borrowed_book_ids": [book.id] if active_loans else [],
        "holds": holds,
        "copies": book.copies.order_by("barcode"),
    }
    return render(request, BOOK_PAGE_TEMPLATE, context)


@login_required
def place_hold(request, book_id):
    book = get_object_or_404(Bookinventory, id=book_id)
    existing_hold = HoldRequest.objects.filter(
        inventory=book,
        requester=request.user,
        status__in=[HoldStatus.PENDING, HoldStatus.READY],
    ).exists()

    if existing_hold:
        messages.info(request, "You already have an active hold for this title.")
        return redirect("book_page", book_id=book_id)

    HoldRequest.objects.create(inventory=book, requester=request.user)
    messages.success(request, "Hold placed successfully.")
    return redirect("book_page", book_id=book_id)


@login_required
def account_overview(request):
    role = getattr(getattr(request.user, "library_profile", None), "role", LibraryRole.PATRON)
    can_manage_loans = role in ROLE_MANAGE_LOANS or request.user.has_perm("core.manage_loans")

    context = {
        "profile": getattr(request.user, "library_profile", None),
        "active_loans": request.user.loans.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        ).select_related("inventory", "copy"),
        "hold_requests": request.user.hold_requests.filter(
            status__in=[HoldStatus.PENDING, HoldStatus.READY]
        ).select_related("inventory"),
        "can_manage_loans": can_manage_loans,
    }
    return render(request, ACCOUNT_TEMPLATE, context)


def index(request):
    featured_books = Bookinventory.objects.order_by("title")[:8]
    context = {
        "featured_books": featured_books,
        "active_loans": Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        ).count(),
        "active_holds": HoldRequest.objects.filter(
            status__in=[HoldStatus.PENDING, HoldStatus.READY]
        ).count(),
    }
    return render(request, INDEX_TEMPLATE, context)

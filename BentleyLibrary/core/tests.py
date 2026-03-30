import json
from datetime import date, timedelta
from io import StringIO
from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import BookCopy, Bookinventory, CopyStatus, Loan, LoanStatus, Log


class LibraryViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def create_book(self, **overrides):
        data = {
            "title": "Python 101",
            "author": "Jane Author",
            "isbn": str(uuid4().int)[:13],
            "published_date": date(2020, 1, 1),
            "publisher": "Example Press",
            "quantity": 3,
            "available_quantity": 3,
            "description": "Introductory Python book",
            "image_url": "https://example.com/python-101.jpg",
        }
        data.update(overrides)
        book = Bookinventory.objects.create(**data)
        available_quantity = book.available_quantity
        for index in range(1, book.quantity + 1):
            BookCopy.objects.create(
                inventory=book,
                barcode=f"LIB-{book.isbn}-{index:04d}",
                status=CopyStatus.AVAILABLE if index <= available_quantity else CopyStatus.ON_LOAN,
            )
        return book

    def create_log(self, book, **overrides):
        copy = book.copies.filter(status=CopyStatus.ON_LOAN).order_by("barcode").first()
        if not copy:
            copy = book.copies.order_by("barcode").first()
            if copy:
                copy.status = CopyStatus.ON_LOAN
                copy.save(update_fields=["status"])
        loan = None
        if copy:
            loan = Loan.objects.create(
                inventory=book,
                copy=copy,
                borrower_email_snapshot=overrides.get("borrower_email", "john@example.com"),
                checked_out_at=timezone.now(),
                due_at=timezone.now() + timedelta(days=21),
                status=LoanStatus.ACTIVE,
            )

        data = {
            "book": book,
            "loan": loan,
            "title": book.title,
            "author": book.author,
            "publisher": book.publisher,
            "publication_date": book.published_date,
            "isbn": book.isbn,
            "borrower_first_name": "John",
            "borrower_last_name": "Doe",
            "borrower_email": "john@example.com",
            "borrowed_date": date(2024, 1, 10),
            "borrowed_time": "09:15:00",
            "returned_date": None,
            "returned_time": None,
        }
        data.update(overrides)
        if loan and data["returned_date"]:
            loan.status = LoanStatus.RETURNED
            loan.returned_at = timezone.now()
            loan.save(update_fields=["status", "returned_at"])
            loan.copy.status = CopyStatus.AVAILABLE
            loan.copy.save(update_fields=["status"])
        return Log.objects.create(**data)


class CheckoutViewTests(LibraryViewTestCase):
    def test_checkout_get_renders_template(self):
        response = self.client.get(reverse("checkout", args=["1234567890123"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/checkout.html")

    def test_checkout_requires_all_fields(self):
        response = self.client.post(
            reverse("checkout", args=["1234567890123"]),
            {"first_name": "John"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please fill in all required fields.")

    def test_checkout_validates_email(self):
        response = self.client.post(
            reverse("checkout", args=["1234567890123"]),
            {"first_name": "John", "last_name": "Doe", "email": "not-an-email"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a valid email address.")

    def test_checkout_rejects_when_no_copies_are_available(self):
        book = self.create_book(available_quantity=0)

        response = self.client.post(
            reverse("checkout", args=[book.isbn]),
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No copies available to check out.")
        self.assertEqual(Log.objects.count(), 0)

    def test_checkout_creates_log_and_reduces_available_quantity(self):
        book = self.create_book(available_quantity=2)

        response = self.client.post(
            reverse("checkout", args=[book.isbn]),
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
            follow=True,
        )

        book.refresh_from_db()
        log = Log.objects.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(book.available_quantity, 1)
        self.assertEqual(log.book, book)
        self.assertContains(response, "Thanks for checking out the book.")

    def test_checkout_unknown_book_shows_error(self):
        response = self.client.post(
            reverse("checkout", args=["9999999999999"]),
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Book not found in inventory.")


class CheckinViewTests(LibraryViewTestCase):
    def test_checkin_get_renders_template(self):
        response = self.client.get(reverse("checkin"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/checkin.html")

    def test_checkin_requires_isbn(self):
        response = self.client.post(reverse("checkin"), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide an ISBN.")

    def test_checkin_unknown_book_shows_error(self):
        response = self.client.post(reverse("checkin"), {"isbn": "9999999999999"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Book not found in inventory.")

    def test_checkin_rejects_when_book_is_not_checked_out(self):
        book = self.create_book(quantity=2, available_quantity=2)

        response = self.client.post(reverse("checkin"), {"isbn": book.isbn})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This book is not checked out.")

    def test_checkin_requires_matching_log_entry(self):
        book = self.create_book(quantity=2, available_quantity=1)

        response = self.client.post(reverse("checkin"), {"isbn": book.isbn})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No check-out record found for this book.")

    def test_checkin_updates_log_and_increases_available_quantity(self):
        book = self.create_book(quantity=2, available_quantity=1)
        log = self.create_log(book)

        response = self.client.post(reverse("checkin"), {"isbn": book.isbn}, follow=True)

        book.refresh_from_db()
        log.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(book.available_quantity, 2)
        self.assertIsNotNone(log.returned_date)
        self.assertIsNotNone(log.returned_time)
        self.assertContains(response, "Book checked in successfully.")


class SearchAndBrowseTests(LibraryViewTestCase):
    def test_index_page_loads(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/index.html")

    def test_search_without_query_behaves_like_browse(self):
        self.create_book(title="Python 101")
        self.create_book(
            title="Django Deep Dive",
            isbn="3210987654321",
            image_url="https://example.com/django.jpg",
        )

        response = self.client.get(reverse("search_results"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/search_results.html")
        self.assertContains(response, "Python 101")
        self.assertContains(response, "Django Deep Dive")

    def test_search_filters_by_query(self):
        self.create_book(title="Python 101")
        self.create_book(
            title="History of Rome",
            isbn="3210987654321",
            description="Roman history reference",
        )

        response = self.client.get(reverse("search_results"), {"q": "Python"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python 101")
        self.assertNotContains(response, "History of Rome")

    def test_search_filters_by_available_quantity(self):
        self.create_book(title="Available Book", available_quantity=1)
        self.create_book(
            title="Unavailable Book",
            isbn="3210987654321",
            available_quantity=0,
        )

        response = self.client.get(
            reverse("search_results"),
            {"available_quantity": "1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Available Book")
        self.assertNotContains(response, "Unavailable Book")

    def test_book_page_displays_borrower_information(self):
        book = self.create_book(quantity=2, available_quantity=1)
        self.create_log(book, borrower_email="reader@example.com")

        response = self.client.get(reverse("book_page", args=[book.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/book_page.html")
        self.assertContains(response, "reader@example.com")

    def test_book_page_missing_book_returns_404(self):
        response = self.client.get(reverse("book_page", args=[99999]))

        self.assertEqual(response.status_code, 404)


class AdvancedSearchTests(LibraryViewTestCase):
    def test_advanced_search_page_loads_without_results(self):
        response = self.client.get(reverse("advanced_search_results"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/advanced_search_results.html")
        self.assertContains(response, "No results found.")

    def test_advanced_search_by_title(self):
        self.create_book(title="Python 101")
        self.create_book(title="Roman History", isbn="3210987654321")

        response = self.client.get(
            reverse("advanced_search_results"),
            {
                "search_type": "everything",
                "field[]": ["title"],
                "operator[]": ["icontains"],
                "search_term[]": ["Python"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python 101")
        self.assertNotContains(response, "Roman History")

    def test_advanced_search_accepts_isbn_field(self):
        target = self.create_book(title="Python 101")
        self.create_book(title="Roman History", isbn="3210987654321")

        response = self.client.get(
            reverse("advanced_search_results"),
            {
                "search_type": "everything",
                "field[]": ["isbn"],
                "operator[]": ["icontains"],
                "search_term[]": [target.isbn[-4:]],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python 101")
        self.assertNotContains(response, "Roman History")


class ErrorHandlingTests(LibraryViewTestCase):
    @patch("core.views.Bookinventory.objects.select_for_update")
    def test_checkout_database_error_is_handled(self, mock_select_for_update):
        mock_select_for_update.return_value.get.side_effect = Exception("Database error")

        response = self.client.post(
            reverse("checkout", args=["1234567890123"]),
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "An error occurred during checkout. Please try again."
        )

    @patch("core.views.Bookinventory.objects.select_for_update")
    def test_checkin_database_error_is_handled(self, mock_select_for_update):
        mock_select_for_update.return_value.get.side_effect = Exception("Database error")

        response = self.client.post(reverse("checkin"), {"isbn": "1234567890123"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "An error occurred during checkin. Please try again."
        )


class RoutingTests(TestCase):
    def test_named_routes_use_clean_paths(self):
        self.assertEqual(reverse("resource"), "/resources/")
        self.assertEqual(reverse("advanced_search_results"), "/advanced-search/")

    def test_legacy_paths_still_resolve(self):
        client = Client()

        self.assertEqual(client.get("/resource.html").status_code, 200)
        self.assertEqual(client.get("/advanced_search_results/").status_code, 200)


class AuthAndWorkflowTests(LibraryViewTestCase):
    def test_account_overview_requires_login(self):
        response = self.client.get(reverse("account_overview"))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_place_hold(self):
        user = get_user_model().objects.create_user(
            username="reader",
            email="reader@example.com",
            password="test-pass",
        )
        book = self.create_book()

        self.client.force_login(user)
        response = self.client.post(reverse("place_hold", args=[book.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hold placed successfully.")
        self.assertContains(response, user.username)

    @override_settings(GO_RERANKER_URL="")
    def test_ai_concierge_returns_local_fallback_matches(self):
        self.create_book(title="Fast Fiction", genre="Young Adult Fiction")

        response = self.client.post(
            reverse("ai_concierge"),
            data=json.dumps({"prompt": "I need a fast read"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "local-guide")
        self.assertTrue(payload["books"])

    @override_settings(GO_RERANKER_URL="")
    @patch("core.ai.llm_intent")
    def test_ai_concierge_uses_grounded_llm_path_when_intent_available(self, mock_llm_intent):
        self.create_book(title="US History Reader", genre="History", summary="Primary sources and context", audience="Upper School")
        self.create_book(title="Creative Writing Essays", genre="Writing", audience="Upper School")
        mock_llm_intent.return_value = {
            "search_query": "history primary sources",
            "course_focus": "History paper",
            "reading_goal": "research",
            "mood": "serious",
            "reading_level": "upper school",
            "explanation": "These titles fit a history research assignment.",
            "tags": ["history", "research"],
            "filters": {"audience": "Upper School", "available_only": False},
        }

        response = self.client.post(
            reverse("ai_concierge"),
            data=json.dumps({"prompt": "I need a book for a history paper", "reading_goal": "research"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "grounded-open-model-rag")
        self.assertEqual(payload["suggested_query"], "history primary sources")
        self.assertTrue(payload["books"])

    def test_search_results_shows_rescue_suggestions_on_empty_state(self):
        response = self.client.get(
            reverse("search_results"),
            {"q": "history of obscure impossible shelf", "reading_goal": "research"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Try a nearby angle")
        self.assertContains(response, "primary sources")


class ManagementCommandTests(TestCase):
    def test_seed_demo_library_populates_books_and_loans(self):
        call_command(
            "seed_demo_library",
            books=12,
            users=4,
            loans=5,
            holds=3,
            wipe_existing=True,
            stdout=StringIO(),
        )

        self.assertGreaterEqual(Bookinventory.objects.count(), 12)
        self.assertGreaterEqual(BookCopy.objects.count(), 12)
        self.assertGreaterEqual(Loan.objects.count(), 5)

    def test_benchmark_search_reports_strategies(self):
        call_command(
            "seed_demo_library",
            books=8,
            users=3,
            loans=2,
            holds=1,
            wipe_existing=True,
            stdout=StringIO(),
        )
        out = StringIO()
        call_command("benchmark_search", query=["atlas"], runs=2, limit=5, stdout=out)
        output = out.getvalue()

        self.assertIn("baseline", output)
        self.assertIn("indexed", output)
        self.assertIn("hybrid", output)

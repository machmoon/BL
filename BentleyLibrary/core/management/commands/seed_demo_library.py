import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
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


GENRES = [
    "Science",
    "History",
    "Technology",
    "Mathematics",
    "Literature",
    "Art",
    "Biography",
    "Politics",
    "Philosophy",
    "Economics",
]
AUDIENCES = ["General", "Middle School", "Upper School", "Faculty"]
LANGUAGES = ["English", "Spanish", "French"]
SUBJECTS = [
    "python",
    "robotics",
    "algebra",
    "renaissance",
    "media studies",
    "data science",
    "climate",
    "ethics",
    "architecture",
    "global affairs",
]


class Command(BaseCommand):
    help = "Seed the library with realistic demo users, catalog titles, copies, loans, and holds."

    def add_arguments(self, parser):
        parser.add_argument("--books", type=int, default=1000)
        parser.add_argument("--users", type=int, default=40)
        parser.add_argument("--loans", type=int, default=250)
        parser.add_argument("--holds", type=int, default=80)
        parser.add_argument("--wipe-existing", action="store_true")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        random.seed(options["seed"])
        self.stdout.write("Seeding demo library data...")
        demo_password = make_password("library-demo")

        if options["wipe_existing"]:
            Loan.objects.all().delete()
            HoldRequest.objects.all().delete()
            Log.objects.all().delete()
            BookCopy.objects.all().delete()
            Bookinventory.objects.all().delete()

        patrons = self._create_users(options["users"], demo_password)
        books = self._create_books(options["books"])
        self._create_loans(books, patrons, options["loans"])
        self._create_holds(books, patrons, options["holds"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {Bookinventory.objects.count()} books, "
                f"{BookCopy.objects.count()} copies, "
                f"{Loan.objects.count()} loans, and "
                f"{HoldRequest.objects.count()} holds."
            )
        )

    def _create_users(self, total_users, demo_password):
        User = get_user_model()
        role_group_pairs = [
            ("librarian", LibraryRole.LIBRARIAN, "Librarian"),
            ("curator", LibraryRole.CURATOR, "Curator"),
            ("admin", LibraryRole.ADMIN, "Admin"),
        ]
        patrons = []

        for username, role, group_name in role_group_pairs:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@library.local",
                    "first_name": username.title(),
                    "last_name": "User",
                    "password": demo_password,
                    "is_staff": True,
                    "is_superuser": role == LibraryRole.ADMIN,
                },
            )
            if user.password != demo_password:
                user.password = demo_password
                user.save(update_fields=["password"])
            user.library_profile.role = role
            user.library_profile.max_active_loans = 25 if role != LibraryRole.LIBRARIAN else 50
            user.library_profile.save(update_fields=["role", "max_active_loans"])
            group = Group.objects.filter(name=group_name).first()
            if group:
                user.groups.add(group)

        for index in range(1, total_users + 1):
            username = f"patron{index:03d}"
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.edu",
                    "first_name": f"Patron{index}",
                    "last_name": "Reader",
                    "password": demo_password,
                },
            )
            if user.password != demo_password:
                user.password = demo_password
                user.save(update_fields=["password"])
            user.library_profile.role = LibraryRole.PATRON
            user.library_profile.max_active_loans = random.choice([5, 6, 7])
            user.library_profile.save(update_fields=["role", "max_active_loans"])
            patrons.append(user)

        return patrons

    def _create_books(self, total_books):
        books = []
        for index in range(1, total_books + 1):
            genre = GENRES[index % len(GENRES)]
            audience = AUDIENCES[index % len(AUDIENCES)]
            language = LANGUAGES[index % len(LANGUAGES)]
            subject_a = SUBJECTS[index % len(SUBJECTS)]
            subject_b = SUBJECTS[(index + 3) % len(SUBJECTS)]
            quantity = random.randint(1, 4)
            published_year = 2000 + (index % 24)
            isbn = f"{9780000000000 + index}"
            title = f"{genre} Atlas {index}"

            book, _ = Bookinventory.objects.get_or_create(
                isbn=isbn,
                defaults={
                    "title": title,
                    "subtitle": f"A field guide to {subject_a}",
                    "author": f"Author {index % 120:03d}",
                    "published_date": timezone.datetime(published_year, (index % 12) + 1, (index % 27) + 1).date(),
                    "publisher": f"Press {(index % 35) + 1}",
                    "genre": genre,
                    "language": language,
                    "audience": audience,
                    "shelf_location": f"A{(index % 12) + 1}-{(index % 30) + 1}",
                    "quantity": quantity,
                    "available_quantity": quantity,
                    "description": f"{title} explores {subject_a} through a {genre.lower()} lens.",
                    "summary": f"Recommended for {audience.lower()} readers interested in {subject_a} and {subject_b}.",
                    "metadata": {"subjects": [subject_a, subject_b], "source": "seed_demo_library"},
                    "image_url": "",
                },
            )
            book.quantity = max(book.quantity, quantity)
            book.available_quantity = book.quantity
            book.save()

            existing_copies = book.copies.count()
            for copy_index in range(existing_copies + 1, book.quantity + 1):
                BookCopy.objects.get_or_create(
                    inventory=book,
                    barcode=f"LIB-{book.isbn}-{copy_index:04d}",
                )
            books.append(book)

        return books

    def _create_loans(self, books, patrons, target_loans):
        if not books or not patrons:
            return

        created = 0
        book_pool = books[:]
        random.shuffle(book_pool)
        librarians = list(get_user_model().objects.filter(username__in=["librarian", "admin"]))

        while created < target_loans and book_pool:
            book = random.choice(book_pool)
            available_copy = book.copies.filter(status=CopyStatus.AVAILABLE).order_by("barcode").first()
            if not available_copy:
                book_pool.remove(book)
                continue

            patron = random.choice(patrons)
            checked_out_at = timezone.now() - timedelta(days=random.randint(1, 30))
            due_at = checked_out_at + timedelta(days=21)
            returned = random.random() < 0.35
            returned_at = checked_out_at + timedelta(days=random.randint(1, 18)) if returned else None
            status = LoanStatus.RETURNED if returned else (LoanStatus.OVERDUE if due_at < timezone.now() else LoanStatus.ACTIVE)
            processor = random.choice(librarians) if librarians else None

            loan = Loan.objects.create(
                inventory=book,
                copy=available_copy,
                borrower=patron,
                processed_by=processor,
                borrower_email_snapshot=patron.email,
                checked_out_at=checked_out_at,
                due_at=due_at,
                returned_at=returned_at,
                status=status,
            )
            Log.objects.create(
                book=book,
                loan=loan,
                title=book.title,
                author=book.author,
                publisher=book.publisher,
                publication_date=book.published_date,
                isbn=book.isbn,
                borrower_first_name=patron.first_name,
                borrower_last_name=patron.last_name,
                borrower_email=patron.email,
                borrowed_date=checked_out_at.date(),
                borrowed_time=checked_out_at.time().replace(microsecond=0),
                returned_date=returned_at.date() if returned_at else None,
                returned_time=returned_at.time().replace(microsecond=0) if returned_at else None,
            )

            if returned:
                available_copy.status = CopyStatus.AVAILABLE
                available_copy.due_back_date = None
            else:
                available_copy.status = CopyStatus.ON_LOAN
                available_copy.due_back_date = due_at.date()
                book.available_quantity = max(book.available_quantity - 1, 0)
            available_copy.last_circulated_at = checked_out_at
            available_copy.save(update_fields=["status", "due_back_date", "last_circulated_at"])
            book.save(update_fields=["available_quantity", "updated_at", "search_document"])
            created += 1

    def _create_holds(self, books, patrons, target_holds):
        if not books or not patrons:
            return

        created = 0
        while created < target_holds:
            book = random.choice(books)
            patron = random.choice(patrons)
            hold, was_created = HoldRequest.objects.get_or_create(
                inventory=book,
                requester=patron,
                status=HoldStatus.PENDING,
            )
            if not was_created:
                continue
            created += 1

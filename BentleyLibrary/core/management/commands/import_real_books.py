import random

from django.core.management.base import BaseCommand

from core.models import BookCopy, Bookinventory, HoldRequest, Loan, Log
from core.openlibrary import search_real_books


COLLECTIONS = [
    ("young adult", "Student Favorites", "Upper School"),
    ("science fiction", "Sci-Fi", "Upper School"),
    ("fantasy", "Fantasy", "Upper School"),
    ("history", "History", "Upper School"),
    ("biography", "Biography", "General"),
    ("computer science", "Technology", "General"),
]


class Command(BaseCommand):
    help = "Populate the catalog with real book metadata from Open Library."

    def add_arguments(self, parser):
        parser.add_argument("--per-topic", type=int, default=18)
        parser.add_argument("--wipe-existing", action="store_true")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        random.seed(options["seed"])
        if options["wipe_existing"]:
            HoldRequest.objects.all().delete()
            Loan.objects.all().delete()
            Log.objects.all().delete()
            BookCopy.objects.all().delete()
            Bookinventory.objects.all().delete()

        created = 0
        seen = set(Bookinventory.objects.values_list("isbn", flat=True))

        for topic, genre, audience in COLLECTIONS:
            books = search_real_books(
                topic,
                limit=options["per_topic"],
                subject=topic,
                fallback_genre=genre,
                fallback_audience=audience,
            )
            for parsed in books:
                if not parsed or parsed.isbn in seen:
                    continue

                quantity = random.randint(1, 4)
                book = Bookinventory.objects.create(
                    title=parsed.title,
                    subtitle=parsed.subtitle,
                    author=parsed.author,
                    isbn=parsed.isbn,
                    published_date=parsed.published_date,
                    publisher=parsed.publisher,
                    genre=parsed.genre,
                    language=parsed.language,
                    audience=parsed.audience,
                    shelf_location=f"{genre[:2].upper()}-{created % 24 + 1:02d}",
                    quantity=quantity,
                    available_quantity=quantity,
                    description=parsed.description,
                    summary=parsed.summary,
                    image_url=parsed.image_url,
                    metadata=parsed.metadata,
                )

                for copy_index in range(1, quantity + 1):
                    BookCopy.objects.create(
                        inventory=book,
                        barcode=f"REAL-{book.isbn}-{copy_index:04d}",
                    )

                seen.add(parsed.isbn)
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {created} real books into the catalog."))

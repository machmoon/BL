import statistics
import time

from django.core.management.base import BaseCommand, CommandError

from core.models import Bookinventory
from core.search import search_books


class Command(BaseCommand):
    help = "Benchmark baseline, indexed, and hybrid search latency."

    def add_arguments(self, parser):
        parser.add_argument("--query", action="append", dest="queries")
        parser.add_argument("--runs", type=int, default=25)
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):
        if not Bookinventory.objects.exists():
            raise CommandError("No books found. Run seed_demo_library first.")

        queries = options["queries"] or ["python", "history", "science", "ethics", "atlas"]
        runs = options["runs"]
        limit = options["limit"]

        for query in queries:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(f'Query: "{query}"'))
            for strategy in ["baseline", "indexed", "hybrid"]:
                timings = []
                hit_count = 0
                for _ in range(runs):
                    started = time.perf_counter()
                    response = search_books(query=query, strategy=strategy, limit=limit)
                    hit_count = len(list(response.queryset[:limit]))
                    timings.append((time.perf_counter() - started) * 1000)

                avg_ms = statistics.mean(timings)
                median_ms = statistics.median(timings)
                p95_ms = sorted(timings)[max(0, int(len(timings) * 0.95) - 1)]
                self.stdout.write(
                    f"{strategy:>8} | hits={hit_count:>3} | avg={avg_ms:>7.2f} ms | "
                    f"p50={median_ms:>7.2f} ms | p95={p95_ms:>7.2f} ms"
                )

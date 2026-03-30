import re
import statistics

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


BASELINE_SQL = """
EXPLAIN (ANALYZE, BUFFERS)
SELECT id
FROM bookinventory
WHERE title ILIKE %s
   OR subtitle ILIKE %s
   OR author ILIKE %s
   OR publisher ILIKE %s
   OR description ILIKE %s
   OR summary ILIKE %s
   OR isbn ILIKE %s
   OR genre ILIKE %s
ORDER BY title
LIMIT 25
"""

INDEXED_SQL = """
EXPLAIN (ANALYZE, BUFFERS)
SELECT id
FROM bookinventory
WHERE search_vector @@ plainto_tsquery('english', %s)
ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC, title ASC
LIMIT 25
"""


class Command(BaseCommand):
    help = "Benchmark in-database PostgreSQL execution time for baseline ILIKE search vs indexed full-text search."

    def add_arguments(self, parser):
        parser.add_argument("--query", action="append", dest="queries")
        parser.add_argument("--runs", type=int, default=10)

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This benchmark requires a PostgreSQL database connection.")

        queries = options["queries"] or ["python", "history"]
        runs = options["runs"]
        pattern = re.compile(r"Execution Time: ([0-9.]+) ms")

        with connection.cursor() as cursor:
            for query in queries:
                like = f"%{query}%"
                baseline_runs = []
                indexed_runs = []

                for _ in range(runs):
                    cursor.execute(BASELINE_SQL, [like] * 8)
                    baseline_plan = "\n".join(row[0] for row in cursor.fetchall())
                    baseline_runs.append(float(pattern.search(baseline_plan).group(1)))

                    cursor.execute(INDEXED_SQL, [query, query])
                    indexed_plan = "\n".join(row[0] for row in cursor.fetchall())
                    indexed_runs.append(float(pattern.search(indexed_plan).group(1)))

                baseline_avg = statistics.mean(baseline_runs)
                indexed_avg = statistics.mean(indexed_runs)
                improvement = (baseline_avg - indexed_avg) / baseline_avg * 100

                self.stdout.write("")
                self.stdout.write(self.style.MIGRATE_HEADING(f'Query: "{query}"'))
                self.stdout.write(
                    f"baseline execution avg={baseline_avg:.3f} ms median={statistics.median(baseline_runs):.3f} ms"
                )
                self.stdout.write(
                    f" indexed execution avg={indexed_avg:.3f} ms median={statistics.median(indexed_runs):.3f} ms"
                )
                self.stdout.write(f" improvement={improvement:.1f}%")

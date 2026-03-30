import json
from pathlib import Path

from django.core.management.base import BaseCommand

from core.discovery.pipeline import run_search_pipeline


def recall_at_k(results, expected_titles, k=5):
    top_titles = {item.title for item in list(results[:k])}
    expected = set(expected_titles)
    if not expected:
        return 0.0
    return len(top_titles & expected) / len(expected)


def precision_at_k(results, expected_titles, k=3):
    top_titles = [item.title for item in list(results[:k])]
    if not top_titles:
        return 0.0
    expected = set(expected_titles)
    hits = sum(1 for title in top_titles if title in expected)
    return hits / min(k, len(top_titles))


class Command(BaseCommand):
    help = "Evaluate search quality on a small labeled query set."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            default=str(Path(__file__).resolve().parents[2] / "evaluation" / "queries.json"),
        )

    def handle(self, *args, **options):
        dataset_path = Path(options["dataset"])
        queries = json.loads(dataset_path.read_text())
        recall_scores = []
        precision_scores = []

        for entry in queries:
            pipeline = run_search_pipeline(
                query=entry["query"],
                reading_goal=entry.get("reading_goal", "reading"),
                filters={},
                limit=10,
            )
            results = list(pipeline.response.queryset[:10])
            recall_scores.append(recall_at_k(results, entry.get("expected_titles", []), k=5))
            precision_scores.append(precision_at_k(results, entry.get("expected_titles", []), k=3))

        avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
        avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
        self.stdout.write(
            self.style.SUCCESS(
                f"queries={len(queries)} recall@5={avg_recall:.2f} precision@3={avg_precision:.2f}"
            )
        )

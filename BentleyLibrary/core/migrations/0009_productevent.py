from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_fix_postgres_search_trigger"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("role", models.CharField(blank=True, db_index=True, default="", max_length=32)),
                ("query_text", models.CharField(blank=True, default="", max_length=255)),
                ("book_id", models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ("reading_goal", models.CharField(blank=True, default="", max_length=32)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="product_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="productevent",
            index=models.Index(fields=["event_type", "created_at"], name="event_type_created_idx"),
        ),
        migrations.AddIndex(
            model_name="productevent",
            index=models.Index(fields=["role", "created_at"], name="event_role_created_idx"),
        ),
    ]

from django.db import migrations


POSTGRES_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS bookinventory_search_gin_idx
ON bookinventory
USING GIN (
    (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(author, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(publisher, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(genre, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'C') ||
        setweight(to_tsvector('english', coalesce(summary, '')), 'C') ||
        setweight(to_tsvector('english', coalesce(search_document, '')), 'D')
    )
);
"""

POSTGRES_INDEX_DROP_SQL = """
DROP INDEX IF EXISTS bookinventory_search_gin_idx;
"""


def create_postgres_search_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(POSTGRES_INDEX_SQL)


def drop_postgres_search_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(POSTGRES_INDEX_DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_bookcopy_holdrequest_libraryprofile_loan_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_postgres_search_index,
            drop_postgres_search_index,
        ),
    ]

from django.db import migrations


SEARCH_VECTOR_EXPRESSION = """
setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
setweight(to_tsvector('english', coalesce(author, '')), 'A') ||
setweight(to_tsvector('english', coalesce(publisher, '')), 'B') ||
setweight(to_tsvector('english', coalesce(genre, '')), 'B') ||
setweight(to_tsvector('english', coalesce(description, '')), 'C') ||
setweight(to_tsvector('english', coalesce(summary, '')), 'C') ||
setweight(to_tsvector('english', coalesce(search_document, '')), 'D')
"""

TRIGGER_SEARCH_VECTOR_EXPRESSION = """
setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
setweight(to_tsvector('english', coalesce(NEW.author, '')), 'A') ||
setweight(to_tsvector('english', coalesce(NEW.publisher, '')), 'B') ||
setweight(to_tsvector('english', coalesce(NEW.genre, '')), 'B') ||
setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C') ||
setweight(to_tsvector('english', coalesce(NEW.summary, '')), 'C') ||
setweight(to_tsvector('english', coalesce(NEW.search_document, '')), 'D')
"""


def create_search_vector_column(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute("DROP INDEX IF EXISTS bookinventory_search_gin_idx")
    schema_editor.execute(
        "ALTER TABLE bookinventory ADD COLUMN IF NOT EXISTS search_vector tsvector"
    )
    schema_editor.execute(
        f"UPDATE bookinventory SET search_vector = {SEARCH_VECTOR_EXPRESSION}"
    )
    schema_editor.execute(
        f"""
        CREATE OR REPLACE FUNCTION bookinventory_search_vector_trigger()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := {TRIGGER_SEARCH_VECTOR_EXPRESSION};
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    schema_editor.execute(
        """
        DROP TRIGGER IF EXISTS bookinventory_search_vector_update
        ON bookinventory
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER bookinventory_search_vector_update
        BEFORE INSERT OR UPDATE ON bookinventory
        FOR EACH ROW EXECUTE FUNCTION bookinventory_search_vector_trigger()
        """
    )
    schema_editor.execute(
        """
        CREATE INDEX IF NOT EXISTS bookinventory_search_vector_gin_idx
        ON bookinventory
        USING GIN (search_vector)
        """
    )


def drop_search_vector_column(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute("DROP INDEX IF EXISTS bookinventory_search_vector_gin_idx")
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS bookinventory_search_vector_update ON bookinventory"
    )
    schema_editor.execute(
        "DROP FUNCTION IF EXISTS bookinventory_search_vector_trigger"
    )
    schema_editor.execute(
        "ALTER TABLE bookinventory DROP COLUMN IF EXISTS search_vector"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_postgres_search_indexes"),
    ]

    operations = [
        migrations.RunPython(
            create_search_vector_column,
            drop_search_vector_column,
        ),
    ]

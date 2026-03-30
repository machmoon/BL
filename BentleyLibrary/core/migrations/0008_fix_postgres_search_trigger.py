from django.db import migrations


TRIGGER_SEARCH_VECTOR_EXPRESSION = """
setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
setweight(to_tsvector('english', coalesce(NEW.author, '')), 'A') ||
setweight(to_tsvector('english', coalesce(NEW.publisher, '')), 'B') ||
setweight(to_tsvector('english', coalesce(NEW.genre, '')), 'B') ||
setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C') ||
setweight(to_tsvector('english', coalesce(NEW.summary, '')), 'C') ||
setweight(to_tsvector('english', coalesce(NEW.search_document, '')), 'D')
"""


def fix_postgres_search_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

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


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_postgres_search_vector_column"),
    ]

    operations = [
        migrations.RunPython(
            fix_postgres_search_trigger,
            migrations.RunPython.noop,
        ),
    ]

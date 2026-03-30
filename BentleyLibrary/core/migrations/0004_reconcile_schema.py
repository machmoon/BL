from django.db import migrations, models
import django.db.models.deletion


def table_columns(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )
    return {column.name for column in description}


def create_bookinventory_table(schema_editor):
    vendor = schema_editor.connection.vendor
    table = schema_editor.quote_name("bookinventory")

    if vendor == "mysql":
        schema_editor.execute(
            f"""
            CREATE TABLE {table} (
                `id` bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
                `title` varchar(255) NOT NULL,
                `author` varchar(255) NOT NULL,
                `isbn` varchar(13) NOT NULL,
                `published_date` date NOT NULL,
                `publisher` varchar(255) NOT NULL,
                `quantity` integer UNSIGNED NOT NULL,
                `available_quantity` integer UNSIGNED NOT NULL,
                `description` text NOT NULL,
                `image_url` varchar(500) NOT NULL DEFAULT ''
            )
            """
        )
        return

    if vendor == "postgresql":
        schema_editor.execute(
            f"""
            CREATE TABLE {table} (
                "id" bigserial NOT NULL PRIMARY KEY,
                "title" varchar(255) NOT NULL,
                "author" varchar(255) NOT NULL,
                "isbn" varchar(13) NOT NULL,
                "published_date" date NOT NULL,
                "publisher" varchar(255) NOT NULL,
                "quantity" integer NOT NULL,
                "available_quantity" integer NOT NULL,
                "description" text NOT NULL DEFAULT '',
                "image_url" varchar(500) NOT NULL DEFAULT ''
            )
            """
        )
        return

    schema_editor.execute(
        f"""
        CREATE TABLE {table} (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "title" varchar(255) NOT NULL,
            "author" varchar(255) NOT NULL,
            "isbn" varchar(13) NOT NULL,
            "published_date" date NOT NULL,
            "publisher" varchar(255) NOT NULL,
            "quantity" integer unsigned NOT NULL,
            "available_quantity" integer unsigned NOT NULL,
            "description" text NOT NULL DEFAULT '',
            "image_url" varchar(500) NOT NULL DEFAULT ''
        )
        """
    )


def create_log_table(schema_editor):
    vendor = schema_editor.connection.vendor
    table = schema_editor.quote_name("log")
    book_table = schema_editor.quote_name("bookinventory")

    if vendor == "mysql":
        schema_editor.execute(
            f"""
            CREATE TABLE {table} (
                `id` bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
                `title` varchar(255) NOT NULL,
                `author` varchar(255) NOT NULL,
                `publisher` varchar(255) NOT NULL,
                `publication_date` date NOT NULL,
                `isbn` varchar(13) NOT NULL,
                `borrower_first_name` varchar(255) NOT NULL,
                `borrower_last_name` varchar(255) NOT NULL,
                `borrower_email` varchar(255) NOT NULL,
                `borrowed_date` date NOT NULL,
                `borrowed_time` time NOT NULL,
                `returned_date` date NULL,
                `returned_time` time NULL,
                `book_id` bigint NULL,
                CONSTRAINT `log_book_id_fk` FOREIGN KEY (`book_id`) REFERENCES {book_table} (`id`)
            )
            """
        )
        return

    if vendor == "postgresql":
        schema_editor.execute(
            f"""
            CREATE TABLE {table} (
                "id" bigserial NOT NULL PRIMARY KEY,
                "title" varchar(255) NOT NULL,
                "author" varchar(255) NOT NULL,
                "publisher" varchar(255) NOT NULL,
                "publication_date" date NOT NULL,
                "isbn" varchar(13) NOT NULL,
                "borrower_first_name" varchar(255) NOT NULL,
                "borrower_last_name" varchar(255) NOT NULL,
                "borrower_email" varchar(255) NOT NULL,
                "borrowed_date" date NOT NULL,
                "borrowed_time" time NOT NULL,
                "returned_date" date NULL,
                "returned_time" time NULL,
                "book_id" bigint NULL REFERENCES {book_table} ("id") DEFERRABLE INITIALLY DEFERRED
            )
            """
        )
        return

    schema_editor.execute(
        f"""
        CREATE TABLE {table} (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "title" varchar(255) NOT NULL,
            "author" varchar(255) NOT NULL,
            "publisher" varchar(255) NOT NULL,
            "publication_date" date NOT NULL,
            "isbn" varchar(13) NOT NULL,
            "borrower_first_name" varchar(255) NOT NULL,
            "borrower_last_name" varchar(255) NOT NULL,
            "borrower_email" varchar(255) NOT NULL,
            "borrowed_date" date NOT NULL,
            "borrowed_time" time NOT NULL,
            "returned_date" date NULL,
            "returned_time" time NULL,
            "book_id" bigint NULL REFERENCES {book_table} ("id") DEFERRABLE INITIALLY DEFERRED
        )
        """
    )


def reconcile_schema(apps, schema_editor):
    tables = set(schema_editor.connection.introspection.table_names())
    vendor = schema_editor.connection.vendor

    if "core_bookinventory" in tables and "bookinventory" not in tables:
        if vendor == "mysql":
            schema_editor.execute("RENAME TABLE core_bookinventory TO bookinventory")
        else:
            schema_editor.execute(
                'ALTER TABLE "core_bookinventory" RENAME TO "bookinventory"'
            )
        tables.remove("core_bookinventory")
        tables.add("bookinventory")

    if "bookinventory" not in tables:
        create_bookinventory_table(schema_editor)
        tables.add("bookinventory")

    book_columns = table_columns(schema_editor, "bookinventory")
    if "description" not in book_columns:
        schema_editor.execute(
            f'ALTER TABLE {schema_editor.quote_name("bookinventory")} '
            "ADD COLUMN description text NOT NULL DEFAULT ''"
        )
    if "image_url" not in book_columns:
        schema_editor.execute(
            f'ALTER TABLE {schema_editor.quote_name("bookinventory")} '
            "ADD COLUMN image_url varchar(500) NOT NULL DEFAULT ''"
        )

    if "log" not in tables:
        create_log_table(schema_editor)
        tables.add("log")

    log_columns = table_columns(schema_editor, "log")
    if "book_id" not in log_columns:
        book_column_type = "bigint NULL" if vendor in {"mysql", "postgresql"} else "integer NULL"
        schema_editor.execute(
            f'ALTER TABLE {schema_editor.quote_name("log")} '
            f"ADD COLUMN book_id {book_column_type}"
        )

    schema_editor.execute(
        """
        UPDATE log
        SET book_id = (
            SELECT id
            FROM bookinventory
            WHERE bookinventory.isbn = log.isbn
            ORDER BY id
            LIMIT 1
        )
        WHERE book_id IS NULL
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_alter_bookinventory_table"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(reconcile_schema, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AlterModelOptions(
                    name="bookinventory",
                    options={},
                ),
                migrations.AlterModelOptions(
                    name="log",
                    options={},
                ),
                migrations.AddField(
                    model_name="bookinventory",
                    name="image_url",
                    field=models.URLField(blank=True, default="", max_length=500),
                ),
                migrations.AlterField(
                    model_name="bookinventory",
                    name="available_quantity",
                    field=models.PositiveIntegerField(),
                ),
                migrations.AlterField(
                    model_name="bookinventory",
                    name="description",
                    field=models.TextField(blank=True, default=""),
                ),
                migrations.AlterField(
                    model_name="bookinventory",
                    name="quantity",
                    field=models.PositiveIntegerField(),
                ),
                migrations.AddField(
                    model_name="log",
                    name="book",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logs",
                        to="core.bookinventory",
                    ),
                ),
                migrations.AlterField(
                    model_name="log",
                    name="borrower_email",
                    field=models.EmailField(max_length=255),
                ),
            ],
        ),
    ]

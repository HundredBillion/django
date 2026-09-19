from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    operations = [
        migrations.RunSQL(
            "CREATE SCHEMA IF NOT EXISTS schema_migrations_a",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "CREATE SCHEMA IF NOT EXISTS schema_migrations_b",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "document",
                    schema="schema_migrations_a",
                ),
            },
        ),
        migrations.CreateModel(
            name="EventA",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("marker", models.IntegerField()),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "event",
                    schema="schema_migrations_a",
                ),
            },
        ),
        migrations.CreateModel(
            name="EventB",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("description", models.CharField(max_length=100)),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "event",
                    schema="schema_migrations_b",
                ),
            },
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "tag",
                    schema="schema_migrations_a",
                ),
            },
        ),
        migrations.CreateModel(
            name="Statement",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        to="migrations.document",
                    ),
                ),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "statement",
                    schema="schema_migrations_b",
                ),
            },
        ),
        migrations.CreateModel(
            name="Article",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("title", models.CharField(max_length=100)),
                ("tags", models.ManyToManyField(to="migrations.tag")),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "article",
                    schema="schema_migrations_b",
                ),
            },
        ),
    ]

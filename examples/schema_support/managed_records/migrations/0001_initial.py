import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunSQL(
            'CREATE SCHEMA IF NOT EXISTS "example_documents"',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            'CREATE SCHEMA IF NOT EXISTS "example_statements"',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="Document",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filename", models.CharField(max_length=100)),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "document", schema="example_documents"
                ),
            },
        ),
        migrations.CreateModel(
            name="Statement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("reference", models.CharField(max_length=100)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="managed_records.document",
                    ),
                ),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "statement", schema="example_statements"
                ),
            },
        ),
    ]

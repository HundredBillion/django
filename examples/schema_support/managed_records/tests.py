from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from .models import Document, Statement


class ManagedApplicationTests(TestCase):
    def test_crud_and_cross_schema_join(self):
        document = Document.objects.create(filename="synthetic.pdf")
        statement = Statement.objects.create(document=document, reference="SYN-001")
        with self.assertNumQueries(1):
            joined = Statement.objects.select_related("document").get(pk=statement.pk)
            self.assertEqual(joined.document.filename, "synthetic.pdf")
        Statement.objects.filter(pk=statement.pk).update(note="Reviewed")
        statement.refresh_from_db()
        self.assertEqual(statement.note, "Reviewed")
        document.delete()
        self.assertFalse(Statement.objects.exists())


class ManagedMigrationTests(TransactionTestCase):
    def test_reverse_and_reapply_migrations(self):
        initial = [("managed_records", "0001_initial")]
        latest = [("managed_records", "0002_statement_note")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(initial)
            apps = executor.loader.project_state(initial).apps
            old_document = apps.get_model("managed_records", "Document")
            old_statement = apps.get_model("managed_records", "Statement")
            document = old_document.objects.create(filename="synthetic.pdf")
            statement = old_statement.objects.create(
                document=document, reference="SYN-001"
            )
            with connection.cursor() as cursor:
                columns = connection.introspection.get_table_description(
                    cursor, Statement._meta.db_table
                )
            self.assertNotIn("note", [column.name for column in columns])

            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            self.assertEqual(Statement.objects.get(pk=statement.pk).note, "")
            self.assertEqual(
                Statement.objects.select_related("document")
                .get(pk=statement.pk)
                .document.filename,
                "synthetic.pdf",
            )
            self.assertEqual(MigrationExecutor(connection).migration_plan(latest), [])

            MigrationExecutor(connection).migrate([("managed_records", None)])
            for model in (Document, Statement):
                self.assertFalse(
                    connection.introspection.table_exists(model._meta.db_table)
                )
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT nspname FROM pg_namespace WHERE nspname IN (%s, %s)",
                    ["example_documents", "example_statements"],
                )
                self.assertEqual(len(cursor.fetchall()), 2)

            MigrationExecutor(connection).migrate(latest)
            document = Document.objects.create(filename="reapplied.pdf")
            Statement.objects.create(document=document, reference="SYN-REAPPLIED")
            self.assertEqual(Statement.objects.get().document.filename, "reapplied.pdf")
        finally:
            MigrationExecutor(connection).migrate(latest)

    def test_flush_removes_rows_and_tables_remain_usable(self):
        document = Document.objects.create(filename="synthetic.pdf")
        Statement.objects.create(document=document, reference="SYN-001")
        call_command("flush", interactive=False, verbosity=0)
        self.assertFalse(Document.objects.exists())
        self.assertFalse(Statement.objects.exists())
        document = Document.objects.create(filename="after-flush.pdf")
        Statement.objects.create(document=document, reference="SYN-AFTER-FLUSH")
        self.assertEqual(Statement.objects.get().document.filename, "after-flush.pdf")

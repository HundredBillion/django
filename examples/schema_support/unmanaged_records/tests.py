from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.writer import MigrationWriter
from django.test import TestCase

from .fixtures import provision, remove
from .models import Document, Statement


class UnmanagedApplicationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        provision()
        try:
            super().setUpClass()
        except Exception:
            remove()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            remove()

    def test_crud_and_cross_schema_join(self):
        document = Document.objects.create(filename="synthetic.pdf")
        statement = Statement.objects.create(document=document, reference="SYN-001")
        with self.assertNumQueries(1):
            joined = Statement.objects.select_related("document").get(pk=statement.pk)
            self.assertEqual(joined.document.filename, "synthetic.pdf")
        Statement.objects.filter(pk=statement.pk).update(reference="SYN-002")
        statement.refresh_from_db()
        self.assertEqual(statement.reference, "SYN-002")
        document.delete()
        self.assertFalse(Statement.objects.exists())

    def test_same_table_name_keeps_schema_identity(self):
        document = Document.objects.create(filename="synthetic.pdf")
        statement = Statement.objects.create(document=document, reference="SYN-001")
        self.assertEqual(Document.objects.get(pk=document.pk).filename, "synthetic.pdf")
        self.assertEqual(Statement.objects.get(pk=statement.pk).reference, "SYN-001")
        self.assertEqual(Document._meta.db_table.table, Statement._meta.db_table.table)
        self.assertNotEqual(
            Document._meta.db_table.schema, Statement._meta.db_table.schema
        )

    def test_external_foreign_key_is_enforced(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Statement.objects.create(document_id=-1, reference="SYN-INVALID")
            connection.check_constraints()

    def test_table_identity_roundtrips_through_migration_serialization(self):
        for model in (Document, Statement):
            with self.subTest(model=model.__name__):
                expression, imports = MigrationWriter.serialize(model._meta.db_table)
                namespace = {}
                for statement in imports:
                    exec(statement, namespace)
                restored = eval(expression, namespace)
                self.assertEqual(restored, model._meta.db_table)

    def test_migration_reversal_preserves_external_tables_and_rows(self):
        document = Document.objects.create(filename="externally-owned.pdf")
        statement = Statement.objects.create(
            document=document, reference="SYN-EXTERNAL"
        )
        try:
            call_command("migrate", "unmanaged_records", "zero", verbosity=0)
            self.assertEqual(
                Statement.objects.select_related("document")
                .get(pk=statement.pk)
                .document.filename,
                "externally-owned.pdf",
            )
        finally:
            call_command("migrate", "unmanaged_records", verbosity=0)

from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings, skipUnlessDBFeature

from .base import MigrationTestBase


@skipUnlessDBFeature("supports_schema_qualified_table_references")
@override_settings(
    MIGRATION_MODULES={
        "migrations": "migrations.test_schema_qualified_migrations",
    }
)
class SchemaQualifiedMigrationTests(MigrationTestBase):
    migrate_from = [("migrations", None)]
    migrate_initial = [("migrations", "0001_initial")]
    migrate_to = [("migrations", "0003_rename_field")]

    def tearDown(self):
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(self.migrate_from)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA IF EXISTS schema_migrations_a CASCADE")
                cursor.execute("DROP SCHEMA IF EXISTS schema_migrations_b CASCADE")
            super().tearDown()

    def table_exists(self, table, schema):
        return connection.introspection.table_exists(
            models.SchemaQualifiedTable(table, schema=schema)
        )

    def test_forwards_reverse_reapply_and_repeat(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)

        self.assertTrue(self.table_exists("document", "schema_migrations_a"))
        self.assertTrue(self.table_exists("event", "schema_migrations_a"))
        self.assertTrue(self.table_exists("event", "schema_migrations_b"))
        self.assertTrue(self.table_exists("statement", "schema_migrations_b"))
        self.assertTrue(self.table_exists("article_tags", "schema_migrations_b"))
        statement_table = models.SchemaQualifiedTable(
            "statement",
            schema="schema_migrations_b",
        )
        self.assertColumnExists(statement_table, "external_reference")
        self.assertIndexNameExists(
            statement_table,
            "schema_migration_reference_idx",
        )

        executor.loader.build_graph()
        self.assertEqual(executor.migration_plan(self.migrate_to), [])
        executor.migrate(self.migrate_to)

        executor.loader.build_graph()
        executor.migrate(self.migrate_initial)
        self.assertColumnNotExists(statement_table, "external_reference")
        self.assertColumnNotExists(statement_table, "reference")

        executor.loader.build_graph()
        executor.migrate(self.migrate_from)
        self.assertFalse(self.table_exists("document", "schema_migrations_a"))
        self.assertFalse(self.table_exists("event", "schema_migrations_a"))
        self.assertFalse(self.table_exists("event", "schema_migrations_b"))
        self.assertFalse(self.table_exists("statement", "schema_migrations_b"))
        self.assertFalse(self.table_exists("article_tags", "schema_migrations_b"))

        executor.loader.build_graph()
        executor.migrate(self.migrate_to)
        self.assertTrue(self.table_exists("document", "schema_migrations_a"))
        self.assertColumnExists(statement_table, "external_reference")

    def test_fake_initial(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_initial)
        executor.migrate(self.migrate_from, fake=True)

        migration = executor.loader.get_migration("migrations", "0001_initial")
        self.assertIs(executor.detect_soft_applied(None, migration)[0], True)

        state = executor.loader.project_state(
            ("migrations", "0001_initial"),
            at_end=True,
        )
        article = state.apps.get_model("migrations", "Article")
        through = article._meta.get_field("tags").remote_field.through
        with connection.schema_editor() as editor:
            editor.delete_model(through)
        self.assertIs(executor.detect_soft_applied(None, migration)[0], False)
        with connection.schema_editor() as editor:
            editor.create_model(through)

        executor.loader.build_graph()
        executor.migrate(self.migrate_initial, fake_initial=True)
        self.assertTrue(self.table_exists("document", "schema_migrations_a"))
        self.assertTrue(self.table_exists("article_tags", "schema_migrations_b"))

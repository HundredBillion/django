from unittest import mock

from django.core.management.color import no_style
from django.db import NotSupportedError, connection, models
from django.db.migrations.operations.models import CreateModel
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter
from django.db.models import sql
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps

from .models import BillingCustomer, BillingInvoice, SalesCustomer


class SchemaQualifiedTableTests(TestCase):
    def set_schema_qualified_table_references_support(self, value):
        original = connection.features.supports_schema_qualified_table_references
        connection.features.supports_schema_qualified_table_references = value
        self.addCleanup(
            setattr,
            connection.features,
            "supports_schema_qualified_table_references",
            original,
        )

    def table_sql(self, model):
        return model._meta.db_table.as_sql_name(connection)

    def test_schema_qualified_table_renders_sql_name(self):
        self.set_schema_qualified_table_references_support(True)
        table = BillingCustomer._meta.db_table
        qn = connection.ops.quote_name

        self.assertEqual(
            table.as_sql_name(connection),
            "%s.%s" % (qn("billing"), qn("customer")),
        )

    def test_schema_qualified_table_requires_backend_support(self):
        self.set_schema_qualified_table_references_support(False)

        table = BillingCustomer._meta.db_table

        with self.assertRaisesMessage(
            NotSupportedError,
            "doesn't support schema-qualified table references",
        ):
            table.as_sql_name(connection)

    @isolate_apps("schema_qualified_tables")
    def test_managed_schema_qualified_table_requires_backend_support(self):
        self.set_schema_qualified_table_references_support(False)

        class ManagedCustomer(models.Model):
            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "customer",
                    schema="billing",
                )

        editor = connection.schema_editor(collect_sql=True, atomic=False)
        editor.deferred_sql = []
        with self.assertRaisesMessage(
            NotSupportedError,
            "doesn't support schema-qualified table references",
        ):
            editor.create_model(ManagedCustomer)

    def test_select_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)

        sql_string = str(BillingCustomer.objects.all().query)

        self.assertIn(self.table_sql(BillingCustomer), sql_string)

    def test_same_table_name_can_be_qualified_by_different_schemas(self):
        self.set_schema_qualified_table_references_support(True)

        billing_sql = str(BillingCustomer.objects.all().query)
        sales_sql = str(SalesCustomer.objects.all().query)

        self.assertIn(self.table_sql(BillingCustomer), billing_sql)
        self.assertIn(self.table_sql(SalesCustomer), sales_sql)

    def test_join_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)

        sql_string = str(BillingInvoice.objects.select_related("customer").query)

        self.assertIn(self.table_sql(BillingInvoice), sql_string)
        self.assertIn(self.table_sql(BillingCustomer), sql_string)

    def test_insert_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)
        query = sql.InsertQuery(BillingCustomer)
        query.insert_values(
            [BillingCustomer._meta.get_field("name")],
            [BillingCustomer(name="Acme")],
        )

        sql_string, params = query.get_compiler(connection=connection).as_sql()[0]

        self.assertIn(
            "INSERT INTO %s" % self.table_sql(BillingCustomer),
            sql_string,
        )
        self.assertEqual(params, ("Acme",))

    @skipUnlessDBFeature("supports_schema_qualified_table_references")
    def test_returning_columns_uses_schema_qualified_table(self):
        sql_string, params = connection.ops.returning_columns(
            [BillingCustomer._meta.pk]
        )

        self.assertIn(self.table_sql(BillingCustomer), sql_string)
        self.assertEqual(params, ())

    def test_update_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)
        query = BillingCustomer.objects.all().query.chain(sql.UpdateQuery)
        query.add_update_values({"name": "Acme"})

        sql_string, params = query.get_compiler(connection=connection).as_sql()

        self.assertIn(
            "UPDATE %s %s SET"
            % (
                self.table_sql(BillingCustomer),
                connection.ops.quote_name("T1"),
            ),
            sql_string,
        )
        self.assertEqual(params, ("Acme",))

    def test_delete_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)
        query = BillingCustomer.objects.filter(name="Acme").query.chain(sql.DeleteQuery)

        sql_string, params = query.get_compiler(connection=connection).as_sql()

        self.assertIn(
            "DELETE FROM %s %s"
            % (
                self.table_sql(BillingCustomer),
                connection.ops.quote_name("T1"),
            ),
            sql_string,
        )
        self.assertEqual(params, ("Acme",))

    def test_delete_batch_uses_schema_qualified_table(self):
        compiler_class = connection.ops.compiler("SQLDeleteCompiler")
        query = sql.DeleteQuery(BillingCustomer)

        with mock.patch.object(compiler_class, "execute_sql", return_value=1):
            deleted = query.delete_batch([1], connection.alias)

        self.assertEqual(deleted, 1)
        self.assertEqual(list(query.alias_map), [query.base_table])

    def test_schema_qualified_table_can_be_serialized_in_migrations(self):
        table = BillingCustomer._meta.db_table

        serialized, imports = MigrationWriter.serialize(table)

        self.assertEqual(
            serialized,
            "models.SchemaQualifiedTable('customer', schema='billing')",
        )
        self.assertEqual(imports, {"from django.db import models"})

    @isolate_apps("schema_qualified_tables")
    def test_schema_qualified_table_allows_managed_model(self):
        class ManagedCustomer(models.Model):
            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "customer",
                    schema="billing",
                )

        self.assertEqual(ManagedCustomer.check(), [])


@skipUnlessDBFeature("supports_schema_qualified_table_references")
class SchemaQualifiedTableDatabaseTests(TransactionTestCase):
    available_apps = ["schema_qualified_tables"]

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA billing")
            cursor.execute("CREATE SCHEMA sales")
            cursor.execute("""
                CREATE TABLE billing.customer (
                    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    name varchar(100) NOT NULL
                )
                """)
            cursor.execute("""
                CREATE TABLE billing.invoice (
                    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    customer_id integer NOT NULL REFERENCES billing.customer (id),
                    reference varchar(100) NOT NULL
                )
                """)
            cursor.execute("""
                CREATE TABLE sales.customer (
                    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    name varchar(100) NOT NULL
                )
                """)
        self.addCleanup(self.drop_schemas)

    def drop_schemas(self):
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA billing CASCADE")
            cursor.execute("DROP SCHEMA sales CASCADE")

    def test_crud_and_join(self):
        billing_customer = BillingCustomer.objects.create(name="Billing customer")
        sales_customer = SalesCustomer.objects.create(name="Sales customer")
        invoice = BillingInvoice.objects.create(
            customer=billing_customer,
            reference="INV-001",
        )

        invoice = BillingInvoice.objects.select_related("customer").get(pk=invoice.pk)
        self.assertEqual(
            invoice.customer,
            billing_customer,
        )
        self.assertEqual(
            SalesCustomer.objects.get(pk=sales_customer.pk),
            sales_customer,
        )
        self.assertEqual(
            BillingCustomer.objects.filter(pk=billing_customer.pk).update(
                name="Updated customer"
            ),
            1,
        )
        billing_customer.refresh_from_db()
        self.assertEqual(billing_customer.name, "Updated customer")
        self.assertEqual(
            BillingInvoice.objects.filter(pk=invoice.pk).delete()[0],
            1,
        )


@skipUnlessDBFeature("supports_schema_qualified_table_references")
class ManagedSchemaQualifiedTableDatabaseTests(TransactionTestCase):
    available_apps = ["schema_qualified_tables"]

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA managed_schema")
            cursor.execute("CREATE SCHEMA related_schema")
        self.addCleanup(self.drop_schemas)

    def drop_schemas(self):
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS managed_schema CASCADE")
            cursor.execute("DROP SCHEMA IF EXISTS related_schema CASCADE")

    def table_exists(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass(%s)", [table_name])
            return cursor.fetchone()[0] is not None

    def column_names(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                [table_name.schema, table_name.table],
            )
            return [row[0] for row in cursor.fetchall()]

    def constraint_names(self, model):
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(
                cursor,
                model._meta.db_table,
            )

    @isolate_apps("schema_qualified_tables")
    def test_create_query_and_delete_managed_model(self):
        class ManagedCustomer(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "customer",
                    schema="managed_schema",
                )

        with connection.schema_editor() as editor:
            editor.create_model(ManagedCustomer)
        self.assertTrue(self.table_exists("managed_schema.customer"))

        customer = ManagedCustomer.objects.create(name="Acme")
        self.assertEqual(ManagedCustomer.objects.get(pk=customer.pk), customer)

        with connection.cursor() as cursor:
            sequences = connection.introspection.get_sequences(
                cursor,
                ManagedCustomer._meta.db_table,
            )
        self.assertEqual(len(sequences), 1)
        self.assertEqual(sequences[0]["table"], ManagedCustomer._meta.db_table)

        flush_sql = connection.ops.sql_flush(
            no_style(),
            [ManagedCustomer._meta.db_table],
            reset_sequences=True,
        )
        connection.ops.execute_sql_flush(flush_sql)
        self.assertFalse(ManagedCustomer.objects.exists())

        with connection.schema_editor() as editor:
            editor.delete_model(ManagedCustomer)
        self.assertFalse(self.table_exists("managed_schema.customer"))

    def test_create_model_migration_forwards_and_backwards(self):
        operation = CreateModel(
            name="ManagedCustomer",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "db_table": models.SchemaQualifiedTable(
                    "migration_customer",
                    schema="managed_schema",
                ),
            },
        )
        from_state = ProjectState()
        to_state = from_state.clone()
        operation.state_forwards("schema_qualified_tables", to_state)

        with connection.schema_editor() as editor:
            operation.database_forwards(
                "schema_qualified_tables",
                editor,
                from_state,
                to_state,
            )
        self.assertTrue(self.table_exists("managed_schema.migration_customer"))

        with connection.schema_editor() as editor:
            operation.database_backwards(
                "schema_qualified_tables",
                editor,
                to_state,
                from_state,
            )
        self.assertFalse(self.table_exists("managed_schema.migration_customer"))

    @isolate_apps("schema_qualified_tables")
    def test_add_alter_rename_and_remove_field(self):
        class ManagedCustomer(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "customer",
                    schema="managed_schema",
                )

        with connection.schema_editor() as editor:
            editor.create_model(ManagedCustomer)

        description = models.CharField(max_length=100, null=True)
        description.set_attributes_from_name("description")
        description.model = ManagedCustomer
        with connection.schema_editor() as editor:
            editor.add_field(ManagedCustomer, description)
        self.assertIn("description", self.column_names(ManagedCustomer._meta.db_table))

        longer_description = models.CharField(max_length=200, null=True)
        longer_description.set_attributes_from_name("description")
        longer_description.model = ManagedCustomer
        with connection.schema_editor() as editor:
            editor.alter_field(
                ManagedCustomer,
                description,
                longer_description,
            )

        details = models.CharField(max_length=200, null=True)
        details.set_attributes_from_name("details")
        details.model = ManagedCustomer
        with connection.schema_editor() as editor:
            editor.alter_field(ManagedCustomer, longer_description, details)
        self.assertIn("details", self.column_names(ManagedCustomer._meta.db_table))

        with connection.schema_editor() as editor:
            editor.remove_field(ManagedCustomer, details)
        self.assertNotIn("details", self.column_names(ManagedCustomer._meta.db_table))

    @isolate_apps("schema_qualified_tables")
    def test_cross_schema_foreign_key(self):
        class Document(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "document",
                    schema="managed_schema",
                )

        class Statement(models.Model):
            document = models.ForeignKey(Document, models.CASCADE)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "statement",
                    schema="related_schema",
                )

        class Review(models.Model):
            note = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "review",
                    schema="related_schema",
                )

        with connection.schema_editor() as editor:
            editor.create_model(Document)
            editor.create_model(Statement)
            editor.create_model(Review)

        document_field = models.ForeignKey(Document, models.CASCADE, null=True)
        document_field.contribute_to_class(Review, "document")
        with connection.schema_editor() as editor:
            editor.add_field(Review, document_field)

        document = Document.objects.create(name="Statement source")
        statement = Statement.objects.create(document=document)
        review = Review.objects.create(note="Checked", document=document)
        self.assertEqual(
            Statement.objects.select_related("document").get(pk=statement.pk).document,
            document,
        )
        constraints = self.constraint_names(Statement)
        self.assertTrue(
            any(
                details["foreign_key"]
                == (
                    models.SchemaQualifiedTable(
                        "document",
                        schema="managed_schema",
                    ),
                    "id",
                )
                for details in constraints.values()
            )
        )
        self.assertEqual(
            Review.objects.select_related("document").get(pk=review.pk).document,
            document,
        )
        self.assertTrue(
            any(
                details["foreign_key"]
                == (
                    models.SchemaQualifiedTable(
                        "document",
                        schema="managed_schema",
                    ),
                    "id",
                )
                for details in self.constraint_names(Review).values()
            )
        )
        with connection.cursor() as cursor:
            relations = connection.introspection.get_relations(
                cursor,
                Statement._meta.db_table,
            )
        self.assertEqual(
            relations["document_id"][1],
            models.SchemaQualifiedTable("document", schema="managed_schema"),
        )

    @isolate_apps("schema_qualified_tables")
    def test_introspection_distinguishes_same_named_tables(self):
        class ManagedEvent(models.Model):
            managed_value = models.IntegerField()

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "event",
                    schema="managed_schema",
                )

        class RelatedEvent(models.Model):
            related_value = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "event",
                    schema="related_schema",
                )

        with connection.schema_editor() as editor:
            editor.create_model(ManagedEvent)
            editor.create_model(RelatedEvent)

        with connection.cursor() as cursor:
            self.assertTrue(
                connection.introspection.table_exists(
                    ManagedEvent._meta.db_table,
                    cursor,
                )
            )
            self.assertTrue(
                connection.introspection.table_exists(
                    RelatedEvent._meta.db_table,
                    cursor,
                )
            )
            managed_columns = connection.introspection.get_table_description(
                cursor,
                ManagedEvent._meta.db_table,
            )
            related_columns = connection.introspection.get_table_description(
                cursor,
                RelatedEvent._meta.db_table,
            )
        self.assertEqual(
            [column.name for column in managed_columns],
            ["id", "managed_value"],
        )
        self.assertEqual(
            [column.name for column in related_columns],
            ["id", "related_value"],
        )

    @isolate_apps("schema_qualified_tables")
    def test_automatic_many_to_many_table_uses_source_schema(self):
        class Tag(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "tag",
                    schema="managed_schema",
                )

        class Article(models.Model):
            title = models.CharField(max_length=100)
            tags = models.ManyToManyField(Tag)

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "article",
                    schema="related_schema",
                )

        through_table = Article.tags.through._meta.db_table
        self.assertEqual(
            through_table,
            models.SchemaQualifiedTable(
                "article_tags",
                schema="related_schema",
            ),
        )
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
            editor.create_model(Article)
        self.assertTrue(self.table_exists("related_schema.article_tags"))

        tag = Tag.objects.create(name="Reviewed")
        article = Article.objects.create(title="Statement")
        article.tags.add(tag)
        self.assertEqual(list(article.tags.all()), [tag])

    @isolate_apps("schema_qualified_tables")
    def test_indexes_and_constraints(self):
        class ManagedCustomer(models.Model):
            name = models.CharField(max_length=100)
            balance = models.IntegerField()

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "customer_objects",
                    schema="managed_schema",
                )

        class RelatedCustomer(models.Model):
            name = models.CharField(max_length=100)
            balance = models.IntegerField()

            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "customer_objects",
                    schema="related_schema",
                )

        index = models.Index(fields=["name"], name="managed_customer_name_idx")
        renamed_index = models.Index(
            fields=["name"],
            name="managed_customer_name_renamed_idx",
        )
        unique = models.UniqueConstraint(
            fields=["name"],
            name="managed_customer_name_uniq",
        )
        check = models.CheckConstraint(
            condition=models.Q(balance__gte=0),
            name="managed_customer_balance_check",
        )
        with connection.schema_editor() as editor:
            editor.create_model(ManagedCustomer)
            editor.create_model(RelatedCustomer)
            editor.add_index(ManagedCustomer, index)
            editor.add_index(RelatedCustomer, index)
            editor.add_constraint(ManagedCustomer, unique)
            editor.add_constraint(ManagedCustomer, check)

        constraints = self.constraint_names(ManagedCustomer)
        self.assertIn(index.name, constraints)
        self.assertIn(unique.name, constraints)
        self.assertIn(check.name, constraints)

        with connection.schema_editor() as editor:
            editor.rename_index(ManagedCustomer, index, renamed_index)
        self.assertIn(renamed_index.name, self.constraint_names(ManagedCustomer))
        self.assertIn(index.name, self.constraint_names(RelatedCustomer))

        with connection.schema_editor() as editor:
            editor.remove_index(ManagedCustomer, renamed_index)
            editor.remove_constraint(ManagedCustomer, unique)
            editor.remove_constraint(ManagedCustomer, check)
        constraints = self.constraint_names(ManagedCustomer)
        self.assertNotIn(renamed_index.name, constraints)
        self.assertNotIn(unique.name, constraints)
        self.assertNotIn(check.name, constraints)
        self.assertIn(index.name, self.constraint_names(RelatedCustomer))

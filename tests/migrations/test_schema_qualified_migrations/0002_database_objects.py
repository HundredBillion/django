from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("migrations", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="statement",
            name="reference",
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="document",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AddIndex(
            model_name="statement",
            index=models.Index(
                fields=["reference"],
                name="schema_migration_reference_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="statement",
            constraint=models.UniqueConstraint(
                fields=["reference"],
                name="schema_migration_reference_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="statement",
            constraint=models.CheckConstraint(
                condition=models.Q(id__gte=1),
                name="schema_migration_id_check",
            ),
        ),
    ]

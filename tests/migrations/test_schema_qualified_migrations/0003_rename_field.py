from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("migrations", "0002_database_objects")]

    operations = [
        migrations.RenameField(
            model_name="statement",
            old_name="reference",
            new_name="external_reference",
        ),
    ]

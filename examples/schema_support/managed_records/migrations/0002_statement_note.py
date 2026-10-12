from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("managed_records", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="statement",
            name="note",
            field=models.CharField(default="", max_length=100),
        ),
    ]

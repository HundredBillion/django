from django.db import models


class Document(models.Model):
    filename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = models.SchemaQualifiedTable("record", schema="example_legacy_docs")


class Statement(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = models.SchemaQualifiedTable("record", schema="example_legacy_rows")

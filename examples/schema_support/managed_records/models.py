from django.db import models


class Document(models.Model):
    filename = models.CharField(max_length=100)

    class Meta:
        db_table = models.SchemaQualifiedTable("document", schema="example_documents")


class Statement(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100)
    note = models.CharField(max_length=100, default="")

    class Meta:
        db_table = models.SchemaQualifiedTable("statement", schema="example_statements")

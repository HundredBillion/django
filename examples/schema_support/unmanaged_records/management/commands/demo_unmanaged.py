from unmanaged_records.fixtures import provision
from unmanaged_records.models import Document, Statement

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Provision example legacy tables and demonstrate unmanaged ORM access."

    def handle(self, **options):
        provision()
        with transaction.atomic():
            document = Document.objects.create(filename="synthetic.pdf")
            statement = Statement.objects.create(document=document, reference="SYN-001")
            joined = Statement.objects.select_related("document").get(pk=statement.pk)
            if joined.document.filename != "synthetic.pdf":
                raise CommandError("Cross-schema read returned an unexpected document.")
            Statement.objects.filter(pk=statement.pk).update(reference="SYN-002")
            statement.refresh_from_db()
            if statement.reference != "SYN-002":
                raise CommandError("Unmanaged update did not persist.")
            document.delete()
            if Statement.objects.filter(pk=statement.pk).exists():
                raise CommandError("Related statement was not deleted.")
        self.stdout.write("Unmanaged CRUD and cross-schema join passed.")

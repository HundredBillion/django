from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import Document, Statement


class Command(BaseCommand):
    help = "Demonstrate managed ORM access after applying the example migrations."

    def handle(self, **options):
        with transaction.atomic():
            document = Document.objects.create(filename="synthetic.pdf")
            statement = Statement.objects.create(document=document, reference="SYN-001")
            joined = Statement.objects.select_related("document").get(pk=statement.pk)
            if joined.document.filename != "synthetic.pdf":
                raise CommandError("Cross-schema read returned an unexpected document.")
            Statement.objects.filter(pk=statement.pk).update(note="Reviewed")
            statement.refresh_from_db()
            if statement.note != "Reviewed":
                raise CommandError("Managed update did not persist.")
            document.delete()
            if Statement.objects.filter(pk=statement.pk).exists():
                raise CommandError("Related statement was not deleted.")
        self.stdout.write("Managed CRUD, migrated field, and cross-schema join passed.")

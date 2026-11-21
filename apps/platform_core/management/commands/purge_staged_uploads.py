from django.core.management.base import BaseCommand

from apps.platform_core.files import purge_expired_staged


class Command(BaseCommand):
    help = "Delete staged uploads older than STAGED_UPLOAD_RETENTION_HOURS (accepted evidence is kept)."

    def handle(self, *args, **options):
        count = purge_expired_staged()
        self.stdout.write(f"Purged {count} staged upload(s).")

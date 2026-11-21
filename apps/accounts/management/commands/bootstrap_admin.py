"""Operator-only bootstrap of the first System Admin (TECHNICAL_REQUIREMENTS.md 4.2, UC-02)."""

import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.commands import bootstrap_admin
from apps.platform_core.exceptions import DomainError


class Command(BaseCommand):
    help = "Create the first System Admin bound to a named IUB identity. Safe to re-run for the same address."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="IUB address of the System Admin.")
        parser.add_argument("--name", required=True, help="Full name.")

    def handle(self, *args, **options):
        try:
            admin = bootstrap_admin(
                iub_email=options["email"], full_name=options["name"], operator=getpass.getuser()
            )
        except DomainError as exc:
            details = "; ".join(m for msgs in exc.field_errors.values() for m in msgs)
            raise CommandError(f"{exc.message} {details}".strip()) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"System Admin ready: {admin.full_name} <{admin.iub_email}> (id {admin.pk})"
            )
        )

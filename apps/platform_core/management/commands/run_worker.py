"""Durable job worker: ``python manage.py run_worker [--once]`` (TR section 1, Python worker)."""

import socket
import time
import uuid

from django.core.management.base import BaseCommand

from apps.platform_core.jobs import run_once


class Command(BaseCommand):
    help = "Process durable jobs (IUB email and other side effects) from PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process one batch and exit.")
        parser.add_argument("--interval", type=float, default=2.0, help="Seconds between polls.")
        parser.add_argument("--batch", type=int, default=10)

    def handle(self, *args, **options):
        worker_id = f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"
        self.stdout.write(f"Worker {worker_id} started.")
        while True:
            report = run_once(worker_id, limit=options["batch"])
            if report.claimed:
                self.stdout.write(
                    f"claimed={report.claimed} succeeded={report.succeeded} "
                    f"retryable={report.retryable} failed={report.failed} uncertain={report.uncertain}"
                )
            if options["once"]:
                return
            time.sleep(options["interval"])

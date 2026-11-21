"""Seed synthetic demonstration data. Development only.

All people, emails and clubs are synthetic and flagged ``is_demo``; they can sign in only through
the DEMO_AUTH persona picker, never through live IUB Google sign-in.
"""

from datetime import date, time, timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.commands import request_profile_change
from apps.accounts.models import Grant, Profile, ProfileChangeRequest
from apps.clubs.models import Assignment, Club, Term
from apps.events.commands import EventInput, create_event
from apps.events.models import Event
from apps.finance.commands import BudgetLineInput, save_budget_version
from apps.finance.models import Currency
from apps.memos import commands as memo_commands
from apps.memos.models import Memo, MemoTemplate, TemplateVersion
from apps.platform_core import audit, clock
from apps.platform_core.access import CEILING, AccessCategory
from apps.platform_core.models import Job

PEOPLE = [
    ("admin", "Synthetic System Admin", AccessCategory.SYSTEM_ADMIN, "System Admin"),
    (
        "head",
        "Synthetic DoSA Head",
        AccessCategory.DOSA_HEAD,
        "Head, Division of Student Activities",
    ),
    ("advisor", "Synthetic Faculty Advisor", AccessCategory.FACULTY_ADVISOR, "Faculty Advisor"),
    (
        "president.pc",
        "Synthetic President (Programming Club)",
        AccessCategory.EB_MEMBER,
        "President, IUB Programming Club",
    ),
    (
        "president.sc",
        "Synthetic President (Science Club)",
        AccessCategory.EB_MEMBER,
        "President, IUB Science Club",
    ),
    (
        "president.dc",
        "Synthetic President (Debate Club)",
        AccessCategory.EB_MEMBER,
        "President, IUB Debate Club",
    ),
    (
        "president.bc",
        "Synthetic President (Business Club)",
        AccessCategory.EB_MEMBER,
        "President, IUB Business Club",
    ),
    (
        "president.cc",
        "Synthetic President (Cultural Club)",
        AccessCategory.EB_MEMBER,
        "President, IUB Cultural Club",
    ),
]

CLUBS = (
    ("IUBPC", "IUB Programming Club", "president.pc"),
    ("IUBSC", "IUB Science Club", "president.sc"),
    ("IUBDC", "IUB Debate Club", "president.dc"),
    ("IUBBC", "IUB Business Club", "president.bc"),
    ("IUBCC", "IUB Cultural Club", "president.cc"),
)


class Command(BaseCommand):
    help = "Create the Admin, DoSA, Faculty Advisor, five clubs and their presidents."

    def handle(self, *args, **options):
        if getattr(settings, "IS_PRODUCTION", False) or not settings.DEMO_AUTH:
            raise CommandError("seed_demo runs only with DEMO_AUTH enabled outside production.")
        domain = settings.DEMO_EMAIL_DOMAIN
        today = clock.local_today()
        with transaction.atomic():
            people = {}
            for handle, name, category, designation in PEOPLE:
                profile, created = Profile.objects.get_or_create(
                    iub_email=f"{handle}@{domain}",
                    defaults={
                        "full_name": name,
                        "access_category": category,
                        "designation": designation,
                        "is_demo": True,
                        "created_at": clock.now(),
                    },
                )
                if created:
                    profile.set_unusable_password()
                    profile.save(update_fields=["password"])
                    audit.record(
                        None, "profile.seed_demo", profile, reason="seed_demo synthetic persona"
                    )
                else:
                    profile.full_name = name
                    profile.designation = designation
                    profile.access_category = category
                    profile.is_active = True
                    profile.is_demo = True
                    profile.save(
                        update_fields=[
                            "full_name",
                            "designation",
                            "access_category",
                            "is_active",
                            "is_demo",
                        ]
                    )
                if category != AccessCategory.SYSTEM_ADMIN:
                    held = set(
                        Grant.objects.filter(profile=profile, revoked_at__isnull=True).values_list(
                            "action", flat=True
                        )
                    )
                    missing = sorted(set(CEILING[category]) - held)
                    if missing:
                        Grant.objects.bulk_create(
                            [
                                Grant(profile=profile, action=action, granted_at=clock.now())
                                for action in missing
                            ]
                        )
                people[handle] = profile
            keep = {profile.iub_email for profile in people.values()}
            retired = Profile.objects.filter(is_demo=True).exclude(iub_email__in=keep)
            now = clock.now()
            Assignment.objects.filter(profile__in=retired, ended_at__isnull=True).update(
                ended_at=now, end_date=today
            )
            retired.update(is_active=False)
            head = people["head"]
            clubs = {}
            for code, club_name, _president in CLUBS:
                club, _ = Club.objects.get_or_create(
                    short_code=code,
                    defaults={
                        "name": club_name,
                        "created_at": clock.now(),
                        "institutional_profile": f"{club_name} (synthetic demonstration record).",
                    },
                )
                clubs[code] = club
                term = club.terms.filter(status=Term.Status.ACTIVE).first()
                if term is None:
                    start = date(today.year if today.month >= 7 else today.year - 1, 7, 1)
                    term = Term.objects.create(
                        club=club,
                        label=f"{start.year}-{str(start.year + 1)[2:]}",
                        start_date=start,
                        end_date=start + timedelta(days=364),
                        status=Term.Status.ACTIVE,
                        created_by=head,
                        created_at=clock.now(),
                    )
                clubs[code + ":term"] = term
            appointments = [(president, code, "President") for code, _name, president in CLUBS]
            for handle, code, title in appointments:
                term = clubs[code + ":term"]
                Assignment.objects.get_or_create(
                    profile=people[handle],
                    term=term,
                    designation=title,
                    defaults={
                        "kind": Assignment.Kind.EB_MEMBER,
                        "club": clubs[code],
                        "start_date": term.start_date,
                        "granted_by": head,
                        "created_at": clock.now(),
                    },
                )
            for code, _name, _president in CLUBS:
                Assignment.objects.get_or_create(
                    profile=people["advisor"],
                    club=clubs[code],
                    kind=Assignment.Kind.FACULTY_ADVISOR,
                    defaults={
                        "start_date": clubs[code + ":term"].start_date,
                        "designation": "Faculty Advisor",
                        "granted_by": head,
                        "created_at": clock.now(),
                    },
                )
            if not MemoTemplate.objects.exists():
                template = MemoTemplate.objects.create(
                    label="Event permission memo",
                    is_active=True,
                    created_by=head,
                    created_at=clock.now(),
                )
                version = TemplateVersion.objects.create(
                    template=template,
                    number=1,
                    label="Event permission memo",
                    instructions=(
                        "Type the memo manually. Include the event title, dates, start and end times, "
                        "purpose and proposed venue in the body. Route Through your Faculty Advisor."
                    ),
                    required_fields=[
                        "body",
                        "from_line",
                        "memo_date",
                        "subject",
                        "through_line",
                        "to_line",
                    ],
                    required_attachments=[],
                    signature_areas=["advisor", "dosa"],
                    requires_budget=False,
                    created_by=head,
                    created_at=clock.now(),
                )
                template.current_version = version
                template.save(update_fields=["current_version"])
            _seed_workspace(people, clubs)
            _seed_venues(head)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded Admin, DoSA, one Faculty Advisor and {len(CLUBS)} club presidents (@{domain}). "
                "Earlier demonstration accounts are deactivated. Sign in at /dev/login/."
            )
        )


def _op() -> str:
    return uuid4().hex


def _sign(actor) -> memo_commands.SignatureInput:
    return memo_commands.SignatureInput(method="typed", typed_name=actor.full_name, attest=True)


def _open_event(author, club, *, title, event_type, when: date, headcount: int, venue: str) -> int:
    return create_event(
        author,
        club_id=club.pk,
        data=EventInput(
            title=title,
            event_type=event_type,
            first_date=when,
            last_date=when,
            start_time=time(18, 0),
            end_time=time(21, 0),
            proposed_venue=venue,
            expected_headcount=headcount,
            description="Synthetic demonstration record.",
        ),
        operation_key=_op(),
    ).object_id


def _draft_memo(author, event_id, template_id, **fields) -> Memo:
    memo_id = memo_commands.create_memo(
        author, event_id=event_id, template_id=template_id, operation_key=_op()
    ).object_id
    memo = Memo.objects.get(pk=memo_id)
    memo_commands.save_memo_draft(
        author,
        memo.pk,
        memo_commands.MemoDraftInput(**fields),
        budget_version_id=None,
        expected_revision=memo.revision,
        operation_key=_op(),
    )
    memo.refresh_from_db()
    return memo


def _send(author, memo: Memo) -> Memo:
    memo.refresh_from_db()
    memo_commands.send_memo_to_advisor(
        author, memo.pk, expected_revision=memo.revision, operation_key=_op()
    )
    memo.refresh_from_db()
    return memo


def _decide(actor, memo: Memo, decision: str, **kwargs) -> Memo:
    memo.refresh_from_db()
    memo_commands.decide_memo(
        actor,
        memo.pk,
        expected_version=memo.current_version.number,
        expected_stage=memo_commands.STAGE_FOR_STATUS[memo.status],
        decision=decision,
        signature=_sign(actor) if decision in {"confirm", "endorse", "approve"} else None,
        operation_key=_op(),
        **kwargs,
    )
    memo.refresh_from_db()
    return memo


def _memo_fields(author, club_name: str, subject: str, body: str) -> dict:
    return {
        "to_line": "Head, Division of Student Activities",
        "through_line": f"Faculty Advisor, {club_name}",
        "from_line": f"{author.full_name}, {author.designation}",
        "memo_date": clock.local_today(),
        "subject": subject,
        "body": body,
        "department": "Synthetic demonstration",
    }


def _seed_workspace(people, clubs) -> None:
    """Fill queues with synthetic records so each role opens a populated screen.

    Idempotent: a second run leaves the workspace alone once the marker event exists.
    Every write goes through the same commands a person would use.
    """
    if Event.objects.filter(title="Winter programming workshop").exists():
        return
    template = MemoTemplate.objects.filter(is_active=True).first()
    if template is None:
        return
    head = people["head"]
    advisor_pc = people["advisor"]
    president_pc = people["president.pc"]
    president_sc = people["president.sc"]
    programming = clubs["IUBPC"]
    science = clubs["IUBSC"]
    today = clock.local_today()

    workshop = _open_event(
        president_pc,
        programming,
        title="Winter programming workshop",
        event_type="workshop",
        when=today + timedelta(days=21),
        headcount=40,
        venue="Department classroom",
    )
    memo = _draft_memo(
        president_pc,
        workshop,
        template.pk,
        **_memo_fields(
            president_pc,
            programming.name,
            "Winter programming workshop",
            "The club requests permission for an evening workshop for 40 participants.",
        ),
    )
    _decide(advisor_pc, _send(president_pc, memo), "confirm")

    colloquium = _open_event(
        president_sc,
        science,
        title="Science colloquium",
        event_type="seminar",
        when=today + timedelta(days=35),
        headcount=60,
        venue="Seminar room",
    )
    _send(
        president_sc,
        _draft_memo(
            president_sc,
            colloquium,
            template.pk,
            **_memo_fields(
                president_sc,
                science.name,
                "Science colloquium",
                "The club requests permission for an evening colloquium for 60 participants.",
            ),
        ),
    )

    circle = _open_event(
        president_pc,
        programming,
        title="Evening coding circle",
        event_type="workshop",
        when=today + timedelta(days=18),
        headcount=25,
        venue="Club room",
    )
    _draft_memo(
        president_pc,
        circle,
        template.pk,
        **_memo_fields(
            president_pc,
            programming.name,
            "Evening coding circle",
            "Draft only. The club has not sent this memo to the Faculty Advisor.",
        ),
    )

    orientation = _open_event(
        president_pc,
        programming,
        title="Club orientation briefing",
        event_type="other",
        when=today + timedelta(days=14),
        headcount=30,
        venue="Department classroom",
    )
    approved = _draft_memo(
        president_pc,
        orientation,
        template.pk,
        **_memo_fields(
            president_pc,
            programming.name,
            "Club orientation briefing",
            "The club requests permission for a short orientation briefing.",
        ),
    )
    _decide(head, _decide(advisor_pc, _send(president_pc, approved), "confirm"), "approve")

    supplies = _open_event(
        president_pc,
        programming,
        title="Workshop supplies request",
        event_type="workshop",
        when=today + timedelta(days=24),
        headcount=40,
        venue="Department classroom",
    )
    save_budget_version(
        president_pc,
        supplies,
        lines=[
            BudgetLineInput(
                "Printed handouts", Decimal("2500.00"), Currency.BDT, Decimal("50"), "set"
            ),
            BudgetLineInput("Refreshments", Decimal("4000.00"), Currency.BDT),
        ],
        requested_amount=Decimal("6500.00"),
        requested_currency=Currency.BDT,
        purpose="Printed handouts and refreshments for the winter workshop.",
        expected_version_number=0,
        operation_key=_op(),
    )

    if not ProfileChangeRequest.objects.filter(
        profile=president_pc, status=ProfileChangeRequest.Status.PENDING
    ).exists():
        request_profile_change(
            president_pc,
            field="department",
            proposed_value="cse",
            operation_key=_op(),
        )

    now = clock.now()
    Job.objects.get_or_create(
        dedupe_key="demo:delivery:workshop-notice",
        defaults={
            "kind": "email.notice",
            "payload": {"subject": "Workshop notice", "note": "synthetic demonstration"},
            "state": Job.State.FAILED,
            "attempts": 3,
            "max_attempts": 5,
            "next_attempt_at": now,
            "last_error": "Synthetic mail provider refused the message (demonstration).",
            "created_at": now,
            "updated_at": now,
        },
    )


def _seed_venues(head) -> None:
    """Synthetic rooms (D-23). Capacities and hours are not official IUB figures."""
    from datetime import time

    from apps.events.models import Venue

    catalogue = (
        (
            "Synthetic classroom",
            "Campus block A",
            60,
            Venue.Kind.CLASSROOM,
            time(8, 0),
            time(22, 0),
        ),
        ("Synthetic MPH", "Campus", 500, Venue.Kind.LARGE_HALL, time(9, 0), time(22, 0)),
        ("Synthetic DMK", "Campus", 800, Venue.Kind.LARGE_HALL, time(9, 0), time(22, 0)),
        ("Synthetic Auditorium", "Campus", 1000, Venue.Kind.LARGE_HALL, time(9, 0), time(22, 0)),
    )
    for name, location, capacity, kind, opens, closes in catalogue:
        Venue.objects.get_or_create(
            name=name,
            defaults={
                "location": location,
                "capacity": capacity,
                "kind": kind,
                "opens_at": opens,
                "closes_at": closes,
                "is_synthetic": True,
                "created_at": clock.now(),
            },
        )

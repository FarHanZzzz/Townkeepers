"""Append-only audit trigger, btree_gist for venue exclusion (Increment 3) and the initial policy.

The initial policy is labelled synthetic: lead times 7 days / 1 month come from the project owner
(PRD 2.6); the approval buffer, review window and working days await DoSA confirmation (PRD C.2).
"""

import datetime

from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations

AUDIT_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION townhall_audit_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit entries are append-only (FR-COM-03)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_core_auditentry_immutable
BEFORE UPDATE OR DELETE ON platform_core_auditentry
FOR EACH ROW EXECUTE FUNCTION townhall_audit_immutable();
"""

AUDIT_TRIGGER_REVERSE = """
DROP TRIGGER IF EXISTS platform_core_auditentry_immutable ON platform_core_auditentry;
DROP FUNCTION IF EXISTS townhall_audit_immutable();
"""


def create_initial_policy(apps, schema_editor):
    PolicyVersion = apps.get_model("platform_core", "PolicyVersion")
    if PolicyVersion.objects.exists():
        return
    PolicyVersion.objects.create(
        effective_from=datetime.date(2000, 1, 1),
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        standard_lead_days=7,
        big_event_lead_months=1,
        approval_buffer_days=2,
        review_window_days=3,
        working_days=[7, 1, 2, 3, 4],
        email_on_submission=True,
        is_synthetic=True,
        note=(
            "Initial demonstration policy. Lead times follow PRD 2.6; approval buffer, review "
            "window and Sunday-Thursday working days are synthetic until DoSA confirms them."
        ),
    )


class Migration(migrations.Migration):
    dependencies = [("platform_core", "0001_initial")]

    operations = [
        BtreeGistExtension(),
        migrations.RunSQL(AUDIT_TRIGGER_SQL, AUDIT_TRIGGER_REVERSE),
        migrations.RunPython(create_initial_policy, migrations.RunPython.noop),
    ]

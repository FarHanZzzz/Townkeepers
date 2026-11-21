"""Club balance, event cash flow and variance (FR-FIN-03, FR-FIN-05, BR-05, AC-03, AC-20).

Confirmed releases are inflows. Scheduled and cancelled releases are not. Only verified expenses
are outflows. Each linked adjustment is applied once by the caller. Currencies are never added
together; pass one currency at a time. A missing figure stays None rather than becoming zero
when the caller has no rows of that kind and asks for a labelled empty result.
"""

from __future__ import annotations

from decimal import Decimal

ZERO = Decimal("0.00")


def money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def club_balance(confirmed_inflows, verified_expenses) -> Decimal:
    """Confirmed inflows minus verified outflows, after adjustments have been applied."""
    return money(
        sum((money(v) for v in confirmed_inflows), ZERO)
        - sum((money(v) for v in verified_expenses), ZERO)
    )


def event_cash_flow(attributed_inflows, verified_expenses) -> Decimal:
    """Attributed confirmed money minus verified event expenses."""
    return club_balance(attributed_inflows, verified_expenses)


def variance(verified_expenditure, planned) -> Decimal:
    """Verified expenditure minus planned cost. Positive is over budget (FR-FIN-05)."""
    return money(verified_expenditure) - money(planned)

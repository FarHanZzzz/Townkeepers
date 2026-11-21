"""Booking interval and route boundaries (FR-EVT-06, AC-14, AC-19, D-22)."""

from datetime import date, time

import pytest

from apps.events.policies import (
    booking_days,
    confirmation_route,
    large_venue_error,
    occupied_bounds,
    ranges_overlap,
)
from apps.platform_core.clock import combine_local


@pytest.mark.req("FR-EVT-06", "AC-19")
def test_identical_partial_and_contained_ranges_overlap_and_adjacent_ones_do_not():
    day = date(2026, 12, 18)
    start, end = occupied_bounds(day, time(18, 0), time(21, 0), 30, 15)
    same = occupied_bounds(day, time(18, 0), time(21, 0), 30, 15)
    partial = occupied_bounds(day, time(20, 0), time(22, 0), 0, 0)
    contained_start = combine_local(day, time(19, 0))
    contained_end = combine_local(day, time(20, 0))
    adjacent_start, adjacent_end = end, combine_local(day, time(23, 0))
    assert ranges_overlap(start, end, *same)
    assert ranges_overlap(start, end, *occupied_bounds(day, time(20, 0), time(22, 0), 0, 0))
    assert ranges_overlap(start, end, contained_start, contained_end)
    assert ranges_overlap(start, end, *partial)
    assert ranges_overlap(start, end, adjacent_start, adjacent_end) is False


@pytest.mark.req("FR-EVT-06", "AC-19")
def test_setup_buffer_makes_an_otherwise_adjacent_booking_overlap():
    day = date(2026, 12, 18)
    first_end = occupied_bounds(day, time(18, 0), time(19, 0), 0, 30)[1]
    second_start = occupied_bounds(day, time(19, 0), time(20, 0), 0, 0)[0]
    assert first_end > second_start


@pytest.mark.req("AC-14", "FR-EVT-05")
def test_large_venue_rejects_349_accepts_350_and_rejects_over_capacity():
    assert large_venue_error(349, 1000)
    assert large_venue_error(350, 1000) is None
    assert large_venue_error(1001, 1000)


@pytest.mark.req("FR-EVT-05", "D-22")
def test_evening_classroom_routes_to_advisor_then_dosa_without_a_department_head():
    assert confirmation_route("classroom", date(2026, 12, 16), time(18, 0), time(21, 0)) == (
        "advisor",
        "dosa",
    )


@pytest.mark.req("FR-EVT-05")
def test_friday_full_day_routes_to_dosa_then_admin_and_a_hall_routes_to_dosa():
    friday = date(2026, 12, 18)
    assert confirmation_route("classroom", friday, time(9, 0), time(17, 0)) == ("dosa", "admin")
    assert confirmation_route("large_hall", friday, time(18, 0), time(21, 0)) == ("dosa",)


@pytest.mark.req("FR-EVT-05")
def test_two_day_booking_is_consecutive_and_a_longer_span_is_rejected():
    first = date(2026, 12, 18)
    assert booking_days(first, first) == [first]
    assert len(booking_days(first, date(2026, 12, 19))) == 2
    with pytest.raises(ValueError):
        booking_days(first, date(2026, 12, 21))

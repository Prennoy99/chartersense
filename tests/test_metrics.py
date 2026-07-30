"""Tests against the ground-truth metric functions (app/metrics.py).

Requires the seeded Postgres DB to be reachable (docker-compose up +
scripts/seed.py already run) — these are integration tests, not pure units,
since the whole point of app/metrics.py is computing real numbers from real
data.
"""
from datetime import date

from app.metrics import Filters, avg_freight_rate_by_route, ballast_ratio, fleet_utilization_rate, tce, \
    voyage_profitability

ALL_VESSEL_TYPES = ["Capesize", "Panamax", "Supramax", "Handysize"]


def test_fleet_utilization_and_ballast_ratio_are_complementary():
    util = fleet_utilization_rate(Filters())
    ballast = ballast_ratio(Filters())
    assert util is not None and ballast is not None
    assert abs((util + ballast) - 1.0) < 1e-9


def test_fleet_utilization_rate_is_a_plausible_fraction():
    util = fleet_utilization_rate(Filters())
    assert 0.0 < util < 1.0


def test_tce_is_positive_for_every_vessel_type():
    # All voyages in the synthetic dataset are profitable by design; a
    # negative or zero TCE would mean either bad data or a formula bug.
    for vtype in ALL_VESSEL_TYPES:
        value = tce(Filters(vessel_type=vtype))
        assert value is not None
        assert value > 0, f"{vtype} TCE should be positive, got {value}"


def test_tce_with_no_matching_voyages_returns_none():
    value = tce(Filters(vessel_type="Capesize", start_date=date(1999, 1, 1), end_date=date(1999, 1, 2)))
    assert value is None


def test_avg_freight_rate_by_route_covers_all_seeded_routes():
    rates = avg_freight_rate_by_route(Filters())
    assert len(rates) == 12  # 3 routes x 4 vessel types, per generate_data.py
    assert all(rate > 0 for rate in rates.values())


def test_avg_freight_rate_by_route_filter_by_vessel_type_narrows_results():
    all_routes = avg_freight_rate_by_route(Filters())
    capesize_routes = avg_freight_rate_by_route(Filters(vessel_type="Capesize"))
    assert len(capesize_routes) < len(all_routes)
    assert len(capesize_routes) == 3


def test_voyage_profitability_shape_and_count():
    result = voyage_profitability(Filters(vessel_type="Panamax"))
    assert result is not None
    assert set(result.keys()) == {"avg", "total", "count"}
    assert result["count"] > 0
    assert abs(result["avg"] * result["count"] - result["total"]) < 1.0


def test_filters_narrow_voyage_counts_correctly():
    unfiltered = voyage_profitability(Filters())["count"]
    filtered = voyage_profitability(Filters(vessel_type="Handysize"))["count"]
    assert 0 < filtered < unfiltered

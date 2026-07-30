"""
Milestone 2 "done when": prints correct, sensible numbers for all 5
semantic-layer metrics, computed straight from the seeded DB.

Run: .venv/bin/python scripts/validate_metrics.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import metrics
from app.metrics import Filters


def section(title):
    print(f"\n=== {title} ===")


def main():
    section("1. Fleet-wide (no filters)")
    print(f"TCE (avg, USD/day):              {metrics.tce():,.0f}")
    print(f"Fleet utilization rate:          {metrics.fleet_utilization_rate():.1%}")
    print(f"Ballast ratio:                   {metrics.ballast_ratio():.1%}")
    print(f"  (sanity check: utilization + ballast ratio should sum to 1.0 -> "
          f"{metrics.fleet_utilization_rate() + metrics.ballast_ratio():.4f})")
    profit = metrics.voyage_profitability()
    print(f"Voyage profitability (avg, USD): {profit['avg']:,.0f}  "
          f"(n={profit['count']}, total={profit['total']:,.0f})")

    section("2. Average freight rate by route (fleet-wide)")
    for route, rate in metrics.avg_freight_rate_by_route().items():
        print(f"  {route:<30} {rate:,.2f}")

    section("3. Filtered example: Capesize voyages only")
    f = Filters(vessel_type="Capesize")
    print(f"TCE (avg, USD/day):              {metrics.tce(f):,.0f}")
    print(f"Fleet utilization rate:          {metrics.fleet_utilization_rate(f):.1%}")
    profit = metrics.voyage_profitability(f)
    print(f"Voyage profitability (avg, USD): {profit['avg']:,.0f}  (n={profit['count']})")

    section("4. Filtered example: last quarter (2026-04-01 to 2026-06-30)")
    f = Filters(start_date=date(2026, 4, 1), end_date=date(2026, 6, 30))
    tce_val = metrics.tce(f)
    util_val = metrics.fleet_utilization_rate(f)
    print(f"TCE (avg, USD/day):              {tce_val:,.0f}" if tce_val is not None else "TCE: no matching voyages")
    print(f"Fleet utilization rate:          {util_val:.1%}" if util_val is not None else "Utilization: no matching voyages")

    section("5. Combined filter: Capesize, last quarter")
    f = Filters(vessel_type="Capesize", start_date=date(2026, 4, 1), end_date=date(2026, 6, 30))
    tce_val = metrics.tce(f)
    print(f"Avg TCE on Capesize voyages last quarter: "
          f"{tce_val:,.0f} USD/day" if tce_val is not None else "no matching voyages")


if __name__ == "__main__":
    main()

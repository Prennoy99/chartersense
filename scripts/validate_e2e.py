"""
Milestone 5: runs a fixed set of natural-language questions through the same
code path the chat UI uses (app.main.query — LLM -> SQL -> safety check ->
DB execution), and diffs each answer against Milestone 2's ground-truth
module (app/metrics.py), which computes the same numbers independently via
hand-written SQL. Flags any mismatch beyond tolerance.

This is the actual "don't just trust the LLM, verify it" mechanism the
project brief calls for — M3's manual spot-checks showed matches, this
script makes that repeatable and automatic.

Run: .venv/bin/python scripts/validate_e2e.py
Exit code 0 if all cases pass, 1 if any mismatch or error.
"""
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# gemini-3.1-flash-lite's free tier caps at 15 requests/minute, and each
# question here costs 2 calls (generate_sql + explain_answer). Firing all
# cases back-to-back reliably 429s partway through, so pace them —
# empirically ~10/min stays comfortably under the limit.
SECONDS_BETWEEN_CASES = 8

from app import metrics
from app.main import query as query_endpoint
from app.metrics import Filters
from app.schemas import QueryRequest

REL_TOL = 0.005   # 0.5% relative tolerance — covers dollar-scale metrics (TCE, profitability)
ABS_TOL = 0.01    # floor for small-magnitude metrics (ratios are 0-1) so 0.5% of e.g. 0.29 doesn't become meaningless


def close_enough(expected: float, actual: float) -> bool:
    return abs(expected - actual) <= max(ABS_TOL, REL_TOL * abs(expected))


def extract_first_number(columns, rows):
    """Pulls the first numeric value out of row 0 — works for any single-
    metric question regardless of what the LLM named/ordered its columns."""
    if not rows:
        return None
    for value in rows[0]:
        if isinstance(value, (int, float)):
            return float(value)
    return None


# Each case: (question, ground_truth_fn, extractor_fn)
# ground_truth_fn() -> float; extractor_fn(columns, rows) -> float
CASES = [
    (
        "What was our average TCE on Capesize voyages last quarter?",
        lambda: metrics.tce(Filters(vessel_type="Capesize", start_date=date(2026, 4, 1), end_date=date(2026, 6, 30))),
        extract_first_number,
    ),
    (
        "What is our fleet utilization rate?",
        lambda: metrics.fleet_utilization_rate(Filters()),
        extract_first_number,
    ),
    (
        "What was the ballast ratio for Panamax vessels?",
        lambda: metrics.ballast_ratio(Filters(vessel_type="Panamax")),
        extract_first_number,
    ),
    (
        "What was our average voyage profitability for Supramax voyages?",
        lambda: metrics.voyage_profitability(Filters(vessel_type="Supramax"))["avg"],
        extract_first_number,
    ),
    (
        "What was our average voyage profitability for Capesize voyages?",
        lambda: metrics.voyage_profitability(Filters(vessel_type="Capesize"))["avg"],
        extract_first_number,
    ),
    (
        "What was the ballast ratio for Handysize vessels?",
        lambda: metrics.ballast_ratio(Filters(vessel_type="Handysize")),
        extract_first_number,
    ),
    (
        "What is the average TCE for Handysize vessels?",
        lambda: metrics.tce(Filters(vessel_type="Handysize")),
        extract_first_number,
    ),
    (
        "How many voyages did we complete for Meridian Bulk Shipping?",
        lambda: _count_voyages_for_charterer("Meridian Bulk Shipping"),
        extract_first_number,
    ),
]


def _count_voyages_for_charterer(charterer: str) -> int:
    with metrics.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM voyages WHERE charterer = %s", (charterer,))
        (count,) = cur.fetchone()
    return count


def main():
    results = []
    for i, (question, ground_truth_fn, extractor) in enumerate(CASES):
        if i > 0:
            time.sleep(SECONDS_BETWEEN_CASES)
        print(f"Q: {question}")
        try:
            expected = ground_truth_fn()
            response = query_endpoint(QueryRequest(question=question))
            actual = extractor(response.columns, response.rows)

            if expected is None or actual is None:
                ok = False
                detail = f"expected={expected}  actual={actual}  (missing value)"
            else:
                ok = close_enough(expected, actual)
                detail = f"expected={expected:,.2f}  actual={actual:,.2f}  {'OK' if ok else 'MISMATCH'}"

            print(f"  {detail}")
            print(f"  SQL: {response.sql}")
            results.append(ok)
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append(False)
        print()

    passed = sum(results)
    total = len(results)
    print(f"=== {passed}/{total} passed ===")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

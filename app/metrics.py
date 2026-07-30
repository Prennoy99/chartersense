"""Ground-truth metric computation.

Independently computes each of the 5 semantic-layer metrics directly from
the database via hand-written SQL — no LLM involved anywhere in this module.
This is the "ground truth" that Milestone 3's LLM-generated SQL answers get
checked against.

Each function accepts the same optional filter kwargs (a subset may be
unsupported per-metric — see semantic_layer/metrics.yaml's
`supported_filters`) and returns plain Python values.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.db import get_connection


@dataclass
class Filters:
    vessel_type: Optional[str] = None
    charterer: Optional[str] = None
    commodity: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


def _voyage_where(f: Filters, date_column: str = "vy.commencement_date"):
    """Builds a WHERE clause + params for voyage-grain queries joined to vessels."""
    clauses = []
    params = []
    if f.vessel_type:
        clauses.append("v.vessel_type = %s")
        params.append(f.vessel_type)
    if f.charterer:
        clauses.append("vy.charterer = %s")
        params.append(f.charterer)
    if f.commodity:
        clauses.append("vy.commodity = %s")
        params.append(f.commodity)
    if f.start_date:
        clauses.append(f"{date_column} >= %s")
        params.append(f.start_date)
    if f.end_date:
        clauses.append(f"{date_column} <= %s")
        params.append(f.end_date)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def tce(filters: Filters = Filters()) -> Optional[float]:
    where_sql, params = _voyage_where(filters)
    sql = f"""
        SELECT AVG(
            (vy.cargo_quantity_tons * vy.freight_rate_usd_per_ton
             - (vc.bunker_cost_usd + vc.port_costs_usd + vc.canal_costs_usd + vc.other_costs_usd))
            / (vy.ballast_days + vy.laden_days)
        )
        FROM voyages vy
        JOIN voyage_costs vc ON vc.voyage_id = vy.voyage_id
        JOIN vessels v ON v.vessel_id = vy.vessel_id
        {where_sql}
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        (result,) = cur.fetchone()
    return float(result) if result is not None else None


def fleet_utilization_rate(filters: Filters = Filters()) -> Optional[float]:
    where_sql, params = _voyage_where(filters)
    sql = f"""
        SELECT SUM(vy.laden_days) / NULLIF(SUM(vy.laden_days + vy.ballast_days), 0)
        FROM voyages vy
        JOIN vessels v ON v.vessel_id = vy.vessel_id
        {where_sql}
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        (result,) = cur.fetchone()
    return float(result) if result is not None else None


def avg_freight_rate_by_route(filters: Filters = Filters()) -> dict:
    clauses = []
    params = []
    if filters.vessel_type:
        clauses.append("vessel_type = %s")
        params.append(filters.vessel_type)
    if filters.start_date:
        clauses.append("date >= %s")
        params.append(filters.start_date)
    if filters.end_date:
        clauses.append("date <= %s")
        params.append(filters.end_date)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT route, AVG(rate_usd_per_ton_or_day)
        FROM freight_rates
        {where_sql}
        GROUP BY route
        ORDER BY route
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return {route: float(avg_rate) for route, avg_rate in rows}


def voyage_profitability(filters: Filters = Filters()) -> Optional[dict]:
    """Returns {"avg": ..., "total": ..., "count": ...} across matching voyages."""
    where_sql, params = _voyage_where(filters)
    sql = f"""
        SELECT
            AVG(vy.cargo_quantity_tons * vy.freight_rate_usd_per_ton
                - (vc.bunker_cost_usd + vc.port_costs_usd + vc.canal_costs_usd + vc.other_costs_usd)),
            SUM(vy.cargo_quantity_tons * vy.freight_rate_usd_per_ton
                - (vc.bunker_cost_usd + vc.port_costs_usd + vc.canal_costs_usd + vc.other_costs_usd)),
            COUNT(*)
        FROM voyages vy
        JOIN voyage_costs vc ON vc.voyage_id = vy.voyage_id
        JOIN vessels v ON v.vessel_id = vy.vessel_id
        {where_sql}
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        avg_profit, total_profit, count = cur.fetchone()
    if count == 0:
        return None
    return {"avg": float(avg_profit), "total": float(total_profit), "count": count}


def ballast_ratio(filters: Filters = Filters()) -> Optional[float]:
    where_sql, params = _voyage_where(filters)
    sql = f"""
        SELECT SUM(vy.ballast_days) / NULLIF(SUM(vy.ballast_days + vy.laden_days), 0)
        FROM voyages vy
        JOIN vessels v ON v.vessel_id = vy.vessel_id
        {where_sql}
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        (result,) = cur.fetchone()
    return float(result) if result is not None else None

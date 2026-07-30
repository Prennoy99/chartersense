"""
Loads the CSVs produced by generate_data.py into the Postgres database
defined by docker-compose.yml. Run generate_data.py first.
"""
import csv
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "chartersense"),
    "user": os.getenv("POSTGRES_USER", "chartersense_admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "admin_pw"),
}

# (csv filename, table name, ordered column list) — order matters for FKs.
TABLES = [
    ("vessels.csv", "vessels",
     ["vessel_id", "name", "vessel_type", "dwt", "build_year", "flag"]),
    ("voyages.csv", "voyages",
     ["voyage_id", "vessel_id", "charterer", "load_port", "discharge_port", "commodity",
      "cargo_quantity_tons", "laycan_start", "laycan_end", "commencement_date",
      "completion_date", "ballast_days", "laden_days", "freight_rate_usd_per_ton"]),
    ("voyage_costs.csv", "voyage_costs",
     ["voyage_id", "bunker_cost_usd", "port_costs_usd", "canal_costs_usd", "other_costs_usd"]),
    ("freight_rates.csv", "freight_rates",
     ["rate_id", "route", "date", "rate_usd_per_ton_or_day", "vessel_type"]),
]


def load_table(cur, csv_name, table, columns):
    path = DATA_DIR / csv_name
    with path.open() as f:
        reader = csv.DictReader(f)
        rows = [tuple(row[c] for c in columns) for row in reader]

    cols_sql = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    cur.executemany(
        f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})",
        rows,
    )
    print(f"loaded {len(rows):>5} rows into {table}")


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Idempotent: clear existing data (children first) before reloading.
            for _, table, _ in reversed(TABLES):
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            for csv_name, table, columns in TABLES:
                load_table(cur, csv_name, table, columns)
        conn.commit()
        print("seed complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

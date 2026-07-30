"""
Synthetic dry-bulk chartering data generator for CharterSense.

Produces four CSVs (vessels, voyages, freight_rates, voyage_costs) with
internally consistent, realistic-looking values. All data is fabricated —
not sourced from or representative of any real company's chartering data.

Deterministic: re-running with the same SEED reproduces identical output.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(exist_ok=True)

END_DATE = date(2026, 7, 15)
START_DATE = END_DATE - timedelta(days=730)  # ~2 years of history

VESSEL_TYPES = ["Capesize", "Panamax", "Supramax", "Handysize"]

FLAGS = ["Panama", "Marshall Islands", "Liberia", "Hong Kong", "Singapore", "Malta", "Cyprus", "Bahamas"]

NAME_PREFIXES = [
    "Nordic", "Pacific", "Atlantic", "Golden", "Silver", "Star", "Ocean", "Blue",
    "Global", "Southern", "Northern", "Crown", "Amber", "Coral", "Ivory", "Meridian",
]
NAME_SUFFIXES = [
    "Voyager", "Trader", "Pioneer", "Horizon", "Endeavor", "Navigator", "Mariner",
    "Enterprise", "Discovery", "Legacy", "Spirit", "Odyssey", "Venture", "Harmony",
]

# vessel_type -> (dwt_min, dwt_max, build_year_min, build_year_max)
VESSEL_SPECS = {
    "Capesize": (150_000, 180_000, 2000, 2023),
    "Panamax": (65_000, 82_000, 2002, 2023),
    "Supramax": (50_000, 60_000, 2004, 2023),
    "Handysize": (28_000, 40_000, 2005, 2023),
}

CHARTERERS = [
    "Meridian Bulk Shipping", "Vantage Ore Traders", "Continental Grain Corp",
    "Harborlight Commodities", "TransOcean Bulk Partners", "Ironbridge Resources",
    "Summit Freight & Trading", "Deep Blue Chartering", "Kestrel Commodities",
    "Anchorpoint Bulk Carriers", "Redwood Grain Traders", "Polaris Minerals",
]

# vessel_type -> list of route dicts (load_port, discharge_port, commodity,
# cargo tons range, per-ton fixture rate range, whether canal transit is typical)
ROUTES = {
    "Capesize": [
        {"load": "Tubarao", "discharge": "Qingdao", "commodity": "Iron Ore", "cargo": (160_000, 180_000), "rate": (8, 16), "canal": False},
        {"load": "Port Hedland", "discharge": "Qingdao", "commodity": "Iron Ore", "cargo": (155_000, 175_000), "rate": (6, 12), "canal": False},
        {"load": "Newcastle", "discharge": "Visakhapatnam", "commodity": "Coal", "cargo": (150_000, 170_000), "rate": (10, 18), "canal": False},
    ],
    "Panamax": [
        {"load": "New Orleans", "discharge": "Qingdao", "commodity": "Grain", "cargo": (65_000, 75_000), "rate": (18, 32), "canal": True},
        {"load": "Santos", "discharge": "Qingdao", "commodity": "Grain", "cargo": (65_000, 75_000), "rate": (16, 28), "canal": False},
        {"load": "Gladstone", "discharge": "Kandla", "commodity": "Coal", "cargo": (68_000, 78_000), "rate": (14, 24), "canal": False},
    ],
    "Supramax": [
        {"load": "Paranagua", "discharge": "Rotterdam", "commodity": "Grain", "cargo": (50_000, 58_000), "rate": (20, 34), "canal": False},
        {"load": "Vancouver", "discharge": "Shanghai", "commodity": "Grain", "cargo": (50_000, 58_000), "rate": (18, 30), "canal": False},
        {"load": "Richards Bay", "discharge": "Chennai", "commodity": "Coal", "cargo": (52_000, 58_000), "rate": (16, 26), "canal": False},
    ],
    "Handysize": [
        {"load": "Rotterdam", "discharge": "Casablanca", "commodity": "Fertilizer", "cargo": (28_000, 36_000), "rate": (22, 36), "canal": False},
        {"load": "Recife", "discharge": "Alexandria", "commodity": "Sugar", "cargo": (30_000, 38_000), "rate": (20, 34), "canal": False},
        {"load": "Houston", "discharge": "Veracruz", "commodity": "Steel Products", "cargo": (28_000, 34_000), "rate": (24, 40), "canal": False},
    ],
}

# vessel_type -> (ballast_days_range, laden_days_range, bunker_usd_per_day_range, port_call_cost_range)
DURATION_COST_SPECS = {
    "Capesize": {"ballast": (5, 15), "laden": (20, 35), "bunker_per_day": (18_000, 26_000), "port_cost": (60_000, 110_000)},
    "Panamax": {"ballast": (4, 12), "laden": (15, 25), "bunker_per_day": (11_000, 16_000), "port_cost": (40_000, 75_000)},
    "Supramax": {"ballast": (3, 10), "laden": (10, 20), "bunker_per_day": (8_000, 12_000), "port_cost": (30_000, 55_000)},
    "Handysize": {"ballast": (3, 8), "laden": (8, 16), "bunker_per_day": (6_000, 9_000), "port_cost": (20_000, 40_000)},
}

CANAL_COST_RANGE = (250_000, 450_000)


def random_date(start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=random.randint(0, span))


def gen_vessels(n_per_type=7):
    vessels = []
    used_names = set()
    vessel_id = 1
    for vtype in VESSEL_TYPES:
        dwt_min, dwt_max, yr_min, yr_max = VESSEL_SPECS[vtype]
        for _ in range(n_per_type):
            while True:
                name = f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_SUFFIXES)}"
                if name not in used_names:
                    used_names.add(name)
                    break
            vessels.append({
                "vessel_id": vessel_id,
                "name": name,
                "vessel_type": vtype,
                "dwt": random.randint(dwt_min, dwt_max),
                "build_year": random.randint(yr_min, yr_max),
                "flag": random.choice(FLAGS),
            })
            vessel_id += 1
    return vessels


def gen_voyages_and_costs(vessels, voyages_per_vessel_range=(10, 16)):
    voyages = []
    costs = []
    voyage_id = 1

    for vessel in vessels:
        vtype = vessel["vessel_type"]
        n_voyages = random.randint(*voyages_per_vessel_range)
        spec = DURATION_COST_SPECS[vtype]

        # Lay voyages out sequentially in time so a single vessel's voyages
        # don't overlap, without needing every voyage to chain end-to-end.
        cursor = START_DATE + timedelta(days=random.randint(0, 20))

        for _ in range(n_voyages):
            if cursor >= END_DATE:
                break
            route = random.choice(ROUTES[vtype])

            ballast_days = random.randint(*spec["ballast"])
            laden_days = random.randint(*spec["laden"])
            total_days = ballast_days + laden_days

            commencement_date = cursor
            completion_date = commencement_date + timedelta(days=total_days)
            if completion_date > END_DATE:
                break

            laycan_start = commencement_date - timedelta(days=random.randint(1, 4))
            laycan_end = laycan_start + timedelta(days=random.randint(1, 5))

            cargo_quantity_tons = round(random.uniform(*route["cargo"]), 2)
            freight_rate_usd_per_ton = round(random.uniform(*route["rate"]), 2)

            voyages.append({
                "voyage_id": voyage_id,
                "vessel_id": vessel["vessel_id"],
                "charterer": random.choice(CHARTERERS),
                "load_port": route["load"],
                "discharge_port": route["discharge"],
                "commodity": route["commodity"],
                "cargo_quantity_tons": cargo_quantity_tons,
                "laycan_start": laycan_start.isoformat(),
                "laycan_end": laycan_end.isoformat(),
                "commencement_date": commencement_date.isoformat(),
                "completion_date": completion_date.isoformat(),
                "ballast_days": ballast_days,
                "laden_days": laden_days,
                "freight_rate_usd_per_ton": freight_rate_usd_per_ton,
            })

            bunker_cost_usd = round(total_days * random.uniform(*spec["bunker_per_day"]), 2)
            port_costs_usd = round(random.uniform(*spec["port_cost"]) * 2, 2)  # load + discharge port calls
            canal_costs_usd = round(random.uniform(*CANAL_COST_RANGE), 2) if route["canal"] else 0.0
            other_costs_usd = round(random.uniform(15_000, 45_000), 2)

            costs.append({
                "voyage_id": voyage_id,
                "bunker_cost_usd": bunker_cost_usd,
                "port_costs_usd": port_costs_usd,
                "canal_costs_usd": canal_costs_usd,
                "other_costs_usd": other_costs_usd,
            })

            voyage_id += 1
            # Gap before the vessel's next voyage: transit/idle time not modeled as its own voyage.
            cursor = completion_date + timedelta(days=random.randint(2, 10))

    return voyages, costs


def gen_freight_rates():
    """Weekly market benchmark rates per route/vessel_type, independent of
    individual voyage fixtures (used for market-average style metrics)."""
    rates = []
    rate_id = 1
    for vtype in VESSEL_TYPES:
        for route in ROUTES[vtype]:
            route_name = f"{route['load']}-{route['discharge']}"
            base_rate = sum(route["rate"]) / 2
            d = START_DATE
            level = base_rate
            while d <= END_DATE:
                # Slow random walk around the base rate, clamped to a sane band.
                level += random.uniform(-0.08, 0.08) * base_rate
                level = max(route["rate"][0] * 0.7, min(route["rate"][1] * 1.3, level))
                rates.append({
                    "rate_id": rate_id,
                    "route": route_name,
                    "date": d.isoformat(),
                    "rate_usd_per_ton_or_day": round(level, 2),
                    "vessel_type": vtype,
                })
                rate_id += 1
                d += timedelta(days=7)
    return rates


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):>5} rows -> {path}")


def main():
    vessels = gen_vessels()
    voyages, costs = gen_voyages_and_costs(vessels)
    freight_rates = gen_freight_rates()

    write_csv(OUT_DIR / "vessels.csv", vessels,
              ["vessel_id", "name", "vessel_type", "dwt", "build_year", "flag"])
    write_csv(OUT_DIR / "voyages.csv", voyages,
              ["voyage_id", "vessel_id", "charterer", "load_port", "discharge_port", "commodity",
               "cargo_quantity_tons", "laycan_start", "laycan_end", "commencement_date",
               "completion_date", "ballast_days", "laden_days", "freight_rate_usd_per_ton"])
    write_csv(OUT_DIR / "voyage_costs.csv", costs,
              ["voyage_id", "bunker_cost_usd", "port_costs_usd", "canal_costs_usd", "other_costs_usd"])
    write_csv(OUT_DIR / "freight_rates.csv", freight_rates,
              ["rate_id", "route", "date", "rate_usd_per_ton_or_day", "vessel_type"])


if __name__ == "__main__":
    main()

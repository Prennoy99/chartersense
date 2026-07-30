-- CharterSense schema (Milestone 1)
-- 4 tables: vessels, voyages, freight_rates, voyage_costs

CREATE TABLE vessels (
    vessel_id     SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    vessel_type   TEXT NOT NULL CHECK (vessel_type IN ('Capesize', 'Panamax', 'Supramax', 'Handysize')),
    dwt           INTEGER NOT NULL CHECK (dwt > 0),
    build_year    INTEGER NOT NULL,
    flag          TEXT NOT NULL
);

CREATE TABLE voyages (
    voyage_id                 SERIAL PRIMARY KEY,
    vessel_id                 INTEGER NOT NULL REFERENCES vessels(vessel_id),
    charterer                 TEXT NOT NULL,
    load_port                 TEXT NOT NULL,
    discharge_port             TEXT NOT NULL,
    commodity                 TEXT NOT NULL,
    cargo_quantity_tons       NUMERIC(12, 2) NOT NULL CHECK (cargo_quantity_tons > 0),
    laycan_start               DATE NOT NULL,
    laycan_end                 DATE NOT NULL,
    commencement_date          DATE NOT NULL,
    completion_date            DATE NOT NULL,
    ballast_days               NUMERIC(6, 2) NOT NULL CHECK (ballast_days >= 0),
    laden_days                 NUMERIC(6, 2) NOT NULL CHECK (laden_days >= 0),
    -- Agreed fixture rate for this specific voyage (distinct from the market
    -- benchmark rates in freight_rates). voyage_revenue_usd is derived from
    -- this at query time: cargo_quantity_tons * freight_rate_usd_per_ton.
    freight_rate_usd_per_ton   NUMERIC(10, 2) NOT NULL CHECK (freight_rate_usd_per_ton > 0),
    CHECK (laycan_end >= laycan_start),
    CHECK (completion_date > commencement_date)
);

CREATE TABLE freight_rates (
    rate_id                     SERIAL PRIMARY KEY,
    route                       TEXT NOT NULL,
    date                        DATE NOT NULL,
    rate_usd_per_ton_or_day     NUMERIC(10, 2) NOT NULL CHECK (rate_usd_per_ton_or_day > 0),
    vessel_type                 TEXT NOT NULL CHECK (vessel_type IN ('Capesize', 'Panamax', 'Supramax', 'Handysize'))
);

CREATE TABLE voyage_costs (
    voyage_id         INTEGER PRIMARY KEY REFERENCES voyages(voyage_id),
    bunker_cost_usd    NUMERIC(12, 2) NOT NULL CHECK (bunker_cost_usd >= 0),
    port_costs_usd     NUMERIC(12, 2) NOT NULL CHECK (port_costs_usd >= 0),
    canal_costs_usd    NUMERIC(12, 2) NOT NULL CHECK (canal_costs_usd >= 0),
    other_costs_usd    NUMERIC(12, 2) NOT NULL CHECK (other_costs_usd >= 0)
);

CREATE INDEX idx_voyages_vessel_id ON voyages(vessel_id);
CREATE INDEX idx_voyages_commencement_date ON voyages(commencement_date);
CREATE INDEX idx_freight_rates_route_date ON freight_rates(route, date);
CREATE INDEX idx_freight_rates_vessel_type ON freight_rates(vessel_type);

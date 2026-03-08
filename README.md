# Crypto ELT Pipeline

An ELT pipeline that extracts Bitcoin price data from CoinGecko (usd), loads it into DuckDB, and transforms it into daily candlestick data using dbt, orchestrated with Airflow.

## Architecture
```
CoinGecko API → extract/extract.py → DuckDB (raw.crypto_prices)
                                              ↓
                                dbt (transforms.stg_crypto_prices)
                                              ↓
                            dbt (transforms.candlesticks_daily)
```

## Stack

| Tool | Role |
|---|---|
| UV | Dependency management |
| requests | HTTP calls to CoinGecko free tier API |
| DuckDB | Lightweight in-process SQL database |
| dbt-duckdb | Transformation layer |
| Airflow | Orchestration (standalone, no Docker) |

## Project Structure
```
crypto-elt/
├── Makefile
├── README.md
├── pyproject.toml
├── .env
├── data/
│   └── crypto.duckdb
├── extract/
│   └── extract.py
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       │   └── stg_crypto_prices.sql
│       └── marts/
│           └── candlesticks_daily.sql
└── dags/
    └── elt_pipeline.py
```

## Setup
```bash
# Install dependencies
make install

# Initialize Airflow database
make airflow-init
```

## Running the pipeline

Run the full pipeline once end to end:
```bash
make run
```

Or run each step individually:
```bash
make extract      # fetch from CoinGecko and load into DuckDB
make transform    # run dbt models
```

Start the Airflow UI:
```bash
make airflow-webserver  # terminal 1
make airflow-scheduler  # terminal 2
# visit http://localhost:8080
```

## Design Decisions

### PyAirbyte → requests

The assignment specifies PyAirbyte for extraction. However, the
`source-coingecko-coins` connector has a bug in its stream discovery phase
that makes it unusable regardless of the config provided:
```
Caused by: time data '' does not match format '%d-%m-%Y'
```

The connector reads `start_date` as an empty string internally during the
`discover` step, before our config values are even evaluated. This affects
both `source.check()` and `select_all_streams()`. The connector spec was
inspected and the correct format (`dd-mm-yyyy`) was confirmed and used -
the bug is in the connector itself, not the config.

I replaced PyAirbyte with a direct `requests` call to the CoinGecko
`/coins/bitcoin/market_chart/range` endpoint. This is more transparent,
has fewer dependencies, and is easier to debug and maintain.

### Idempotency

The extraction uses `INSERT ... ON CONFLICT DO UPDATE` on the
`(coin_id, vs_currency, timestamp)` primary key, so running the pipeline
multiple times never produces duplicate rows.

### DuckDB schema layout

- `raw.crypto_prices` - raw upsert table, stores exactly what the API returns
- `transforms.stg_crypto_prices` - view, cleans and deduplicates raw data
- `transforms.candlesticks_daily` - table, daily OHLC aggregation

### dbt model design

- Staging is a **view** (no storage cost, always fresh)
- Marts is a **table** (fast to query for downstream use)
- `QUALIFY` is used instead of a subquery for deduplication (cleaner, natively supported by DuckDB)

## Data Model

### `transforms.candlesticks_daily`

| Column | Type | Description |
|---|---|---|
| coin_id | VARCHAR | e.g. bitcoin |
| vs_currency | VARCHAR | e.g. usd |
| price_date | DATE | Day of the candle |
| open_price | DOUBLE | First price of the day |
| close_price | DOUBLE | Last price of the day |
| low_price | DOUBLE | Minimum price of the day |
| high_price | DOUBLE | Maximum price of the day |
| price_change | DOUBLE | close - open |
| price_change_pct | DOUBLE | % change open → close |

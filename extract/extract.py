import os
import duckdb
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "./data/crypto.duckdb")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")  # empty = free tier


def fetch_bitcoin_prices() -> list[dict]:
    """Fetch hourly Bitcoin prices for the last 7 days from CoinGecko."""

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
    params = {
        "vs_currency": "usd",
        "from": int(week_ago.timestamp()),
        "to": int(now.timestamp()),
        "precision": "full",
    }
    headers = {"accept": "application/json"}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

    print(f"📡 Fetching Bitcoin prices from {week_ago.date()} to {now.date()}...")
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    prices = data.get("prices", [])
    print(f"✅ Got {len(prices)} price points")

    # Each price point is [timestamp_ms, price]
    return [
        {
            "coin_id": "bitcoin",
            "vs_currency": "usd",
            "timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc),
            "price": price,
        }
        for ts, price in prices
    ]


def load_to_duckdb(records: list[dict]) -> None:
    """Load price records into DuckDB raw schema."""

    print(f"📦 Loading {len(records)} records into DuckDB...")
    con = duckdb.connect(DUCKDB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.crypto_prices (
            coin_id      VARCHAR        NOT NULL,
            vs_currency  VARCHAR        NOT NULL,
            timestamp    TIMESTAMPTZ    NOT NULL,
            price        DOUBLE         NOT NULL,
            loaded_at    TIMESTAMPTZ    DEFAULT now(),
            PRIMARY KEY (coin_id, vs_currency, timestamp)
        )
    """)

    # Upsert — safe to run multiple times (idempotent)
    con.executemany("""
        INSERT INTO raw.crypto_prices (coin_id, vs_currency, timestamp, price)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (coin_id, vs_currency, timestamp) DO UPDATE
            SET price = excluded.price,
                loaded_at = now()
    """, [(r["coin_id"], r["vs_currency"], r["timestamp"], r["price"]) for r in records])

    count = con.execute("SELECT COUNT(*) FROM raw.crypto_prices").fetchone()[0]
    print(f"✅ Table now has {count} rows")

    sample = con.execute("""
        SELECT coin_id, timestamp, price
        FROM raw.crypto_prices
        ORDER BY timestamp DESC
        LIMIT 3
    """).fetchall()
    print(f"📊 Latest 3 records: {sample}")

    con.close()


def extract_and_load() -> None:
    records = fetch_bitcoin_prices()
    load_to_duckdb(records)
    print("🎉 Extraction and loading complete!")


if __name__ == "__main__":
    extract_and_load()
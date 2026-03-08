
  
  create view "crypto"."transforms"."stg_crypto_prices__dbt_tmp" as (
    select
    coin_id,
    vs_currency,
    CAST(timestamp AS DATE)       as price_date,
    timestamp             as price_timestamp,
    price
from raw.crypto_prices
qualify row_number() over (
    partition by coin_id, vs_currency, timestamp
    order by timestamp
) = 1
  );

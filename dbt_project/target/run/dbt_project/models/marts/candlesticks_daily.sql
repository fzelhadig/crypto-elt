
  
    
    

    create  table
      "crypto"."transforms"."candlesticks_daily__dbt_tmp"
  
    as (
      with prices as (
    select * from "crypto"."transforms"."stg_crypto_prices"
),

daily as (
    select
        coin_id,
        vs_currency,
        price_date,

        -- Opening price: first price of the day
        first_value(price) over (
            partition by coin_id, vs_currency, price_date
            order by price_timestamp
            rows between unbounded preceding and unbounded following
        ) as open_price,

        -- Closing price: last price of the day
        last_value(price) over (
            partition by coin_id, vs_currency, price_date
            order by price_timestamp
            rows between unbounded preceding and unbounded following
        ) as close_price,

        min(price) over (
            partition by coin_id, vs_currency, price_date
        ) as low_price,

        max(price) over (
            partition by coin_id, vs_currency, price_date
        ) as high_price

    from prices
)

select distinct
    coin_id,
    vs_currency,
    price_date,
    open_price,
    close_price,
    low_price,
    high_price,
    round(close_price - open_price, 2)          as price_change,
    round((close_price - open_price)
        / open_price * 100, 4)                  as price_change_pct
from daily
order by price_date
    );
  
  
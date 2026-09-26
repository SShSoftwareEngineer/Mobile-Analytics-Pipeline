-- Deduplication and revenue_usd normalization
-- Dialect: PostgreSQL

DROP TABLE IF EXISTS events_fact;

CREATE TABLE events_fact AS
WITH ranked_events AS (
    SELECT
        events_raw.*,
        ROW_NUMBER() OVER (
            PARTITION BY event_id
            ORDER BY ingested_at DESC
        ) AS rn
    FROM events_raw
    WHERE LOWER(TRIM(is_test)) = 'false'
)
SELECT
    event_id,
    user_id,
    app_id,
    event_name,
    event_time::timestamptz AS event_time,
    ingested_at::timestamptz AS ingested_at,
    country,
    media_source,
    campaign,
    CASE
        WHEN revenue_usd IS NULL
          OR TRIM(revenue_usd) = ''
          OR UPPER(TRIM(revenue_usd)) = 'NULL'
            THEN 0.0
        WHEN TRIM(revenue_usd) ~ '^[+-]?[0-9]+([.,][0-9]+)?$'
            THEN REPLACE(TRIM(revenue_usd), ',', '.')::numeric
        ELSE 0.0
    END AS revenue_usd,
    FALSE AS is_test
FROM ranked_events
WHERE rn = 1;
-- Dialect: PostgreSQL

WITH watermark AS (
    -- Last successfully processed ingestion timestamp
    SELECT MAX(ingested_at) AS last_ingested_at
    FROM events_fact
),

incremental_events AS (
    -- Select new and potentially corrected events
    -- from the last processed ingestion timestamp.
    SELECT
        e.*
    FROM events_raw AS e
    CROSS JOIN watermark AS w
    WHERE e.ingested_at::timestamptz >= w.last_ingested_at
),

ranked_events AS (
    -- If the same event_id appears several times in the
    -- incremental window, keep its latest version.
    SELECT
        incremental_events.*,
        ROW_NUMBER() OVER (
            PARTITION BY event_id
            ORDER BY ingested_at::timestamptz DESC
        ) AS rn
    FROM incremental_events
    WHERE LOWER(TRIM(is_test)) = 'false'
)

INSERT INTO events_fact (
    event_id,
    user_id,
    app_id,
    event_name,
    event_time,
    ingested_at,
    country,
    media_source,
    campaign,
    revenue_usd,
    is_test
)

SELECT
    event_id,
    user_id,
    app_id,
    event_name,
    event_time::timestamptz,
    ingested_at::timestamptz,
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
WHERE rn = 1

ON CONFLICT (event_id)
DO UPDATE SET
    user_id = EXCLUDED.user_id,
    app_id = EXCLUDED.app_id,
    event_name = EXCLUDED.event_name,
    event_time = EXCLUDED.event_time,
    ingested_at = EXCLUDED.ingested_at,
    country = EXCLUDED.country,
    media_source = EXCLUDED.media_source,
    campaign = EXCLUDED.campaign,
    revenue_usd = EXCLUDED.revenue_usd,
    is_test = EXCLUDED.is_test;
-- Dialect: PostgreSQL

DROP TABLE IF EXISTS events_fact;

CREATE TABLE events_fact AS
SELECT DISTINCT ON (event_id) 
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
FROM events_raw
WHERE is_test = false
ORDER BY event_id, ingested_at DESC;
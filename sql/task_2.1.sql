-- Dialect: Any

DROP TABLE IF EXISTS events_fact;

CREATE TABLE events_fact AS
WITH ranked_events AS (SELECT events_raw.*,
                              row_number()
                              OVER (PARTITION BY events_raw.event_id ORDER BY events_raw.ingested_at DESC) AS rn
                       FROM events_raw
                       WHERE events_raw.is_test = 'false')
SELECT event_id,
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
FROM ranked_events
WHERE rn = 1
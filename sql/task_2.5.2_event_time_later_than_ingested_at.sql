-- Check 2: event_time must not be later than ingested_at or STOP.

SELECT
    event_id,
    event_time,
    ingested_at
FROM events_fact
WHERE event_time > ingested_at;
-- Check 1: event_id must be unique or STOP.

SELECT
    event_id,
    COUNT(*) AS cnt
FROM events_fact
GROUP BY event_id
HAVING COUNT(*) > 1;
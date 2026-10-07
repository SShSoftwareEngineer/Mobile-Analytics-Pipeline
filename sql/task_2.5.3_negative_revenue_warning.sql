-- Check 3: negative revenue is suspicious but may represent refunds. WARNING.

SELECT
    event_id,
    revenue_usd
FROM events_fact
WHERE revenue_usd < 0;
-- Dialect: PostgreSQL

-- Recreate intermediate daily revenue table
DROP TABLE IF EXISTS app_daily_revenue;

CREATE TABLE app_daily_revenue AS

-- Calculate revenue for each app and calendar day
WITH daily_revenue AS (SELECT app_id,
                              event_time::date AS event_date,
                              SUM(revenue_usd) AS daily_revenue
                       FROM events_fact
                       GROUP BY app_id,
                                event_time::date),

-- Find the last event date in the dataset
     max_date AS (SELECT MAX(event_time::date) AS max_event_date
                  FROM events_fact),

-- Define the date range for each app:
-- from app launch date to the last event date
     app_dates AS (SELECT app_id,
                          launched_on::date AS launched_on,
                          max_event_date
                   FROM apps
                            CROSS JOIN max_date),

-- Generate one calendar row for each app and each calendar day
     calendar AS (SELECT app_id,
                         generate_series(
                                 launched_on,
                                 max_event_date,
                                 interval '1 day'
                         )::date AS event_date
                  FROM app_dates)

-- Add daily revenue to the complete calendar.
-- Days without events receive zero revenue.
SELECT c.app_id,
       c.event_date,
       COALESCE(d.daily_revenue, 0) AS daily_revenue
FROM calendar AS c
         LEFT JOIN daily_revenue AS d
                   ON d.app_id = c.app_id
                       AND d.event_date = c.event_date;
-- Recreate the final daily revenue metrics table
-- Dialect: PostgreSQL

DROP TABLE IF EXISTS app_daily_revenue_metrics;

CREATE TABLE app_daily_revenue_metrics AS

-- Calculate all daily metrics from the complete calendar
WITH metrics AS (SELECT app_id,
                        event_date,
                        daily_revenue,

                        -- Cumulative revenue since app launch
                        SUM(daily_revenue) OVER (
                            PARTITION BY app_id
                            ORDER BY event_date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                            ) AS cumulative_revenue,

                        -- Average daily revenue for the current day
                        -- and the previous 6 calendar days
                        AVG(daily_revenue) OVER (
                            PARTITION BY app_id
                            ORDER BY event_date
                            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                            ) AS rolling_7d_avg_revenue,

                        -- Revenue for the previous calendar day
                        LAG(daily_revenue) OVER (
                            PARTITION BY app_id
                            ORDER BY event_date
                            ) AS previous_day_revenue

                 FROM app_daily_revenue)

-- Calculate the percentage change from the previous day
SELECT app_id,
       event_date,
       daily_revenue,
       cumulative_revenue,
       rolling_7d_avg_revenue,

       CASE
           WHEN previous_day_revenue IS NULL
               OR previous_day_revenue = 0
               THEN NULL
           ELSE
               (daily_revenue - previous_day_revenue)
                   / previous_day_revenue * 100
           END AS daily_revenue_change_pct

FROM metrics;
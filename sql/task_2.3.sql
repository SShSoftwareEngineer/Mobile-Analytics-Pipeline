-- Dialect: PostgreSQL

-- Recreate the daily campaign performance table
DROP TABLE IF EXISTS campaign_daily_performance;

CREATE TABLE campaign_daily_performance AS

-- Aggregate event revenue to the same grain as campaign costs
WITH daily_revenue AS (
    SELECT
        app_id,
        event_time::date AS date,
        media_source,
        campaign,
        SUM(revenue_usd) AS revenue
    FROM events_fact
    GROUP BY
        app_id,
        event_time::date,
        media_source,
        campaign
)

-- Combine revenue and campaign costs.
-- FULL OUTER JOIN keeps both sides: campaigns with costs but no revenue, and revenue with no corresponding costs.
SELECT
    COALESCE(r.app_id, c.app_id) AS app_id,
    COALESCE(r.date, c.date::date) AS date,
    COALESCE(r.media_source, c.media_source) AS media_source,
    COALESCE(r.campaign, c.campaign) AS campaign,
    COALESCE(r.revenue, 0) AS revenue,
    COALESCE(c.cost_usd::numeric, 0) AS cost_usd,

    -- ROAS is undefined when there is no campaign cost
    CASE
        WHEN COALESCE(c.cost_usd::numeric, 0) = 0
            THEN NULL
        ELSE
            COALESCE(r.revenue, 0) / c.cost_usd::numeric
    END AS roas

FROM daily_revenue AS r

FULL OUTER JOIN campaign_costs AS c
    ON r.app_id = c.app_id
   AND r.date = c.date::date
   AND r.media_source = c.media_source
   AND r.campaign = c.campaign;
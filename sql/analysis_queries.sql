-- ============================================================
-- Bank Marketing Campaign — SQL Analysis Queries
-- Database: bank.db (SQLite)
-- Table: contacts
-- ============================================================

-- ── Overall Summary ───────────────────────────────────────────
SELECT
    COUNT(*)                                          AS total_contacts,
    SUM(call_connected)                               AS connected_calls,
    SUM(subscribed)                                   AS total_subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 2)      AS overall_conversion_pct,
    ROUND(AVG(duration_min), 2)                       AS avg_call_min,
    ROUND(AVG(campaign), 2)                           AS avg_calls_per_contact,
    ROUND(AVG(balance), 0)                            AS avg_balance_eur
FROM contacts;


-- ── Q1: Which job + education segments convert best? ─────────
SELECT
    job,
    education,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(balance), 0)                            AS avg_balance_eur
FROM contacts
WHERE call_connected = 1
GROUP BY job, education
HAVING COUNT(*) >= 100
ORDER BY conversion_rate_pct DESC
LIMIT 20;


-- ── Q2: Call frequency sweet spot ────────────────────────────
-- At what number of calls does conversion start dropping?
SELECT
    campaign                                          AS num_calls,
    COUNT(*)                                          AS contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 2)      AS conversion_rate_pct,
    -- Running average to smooth noise
    ROUND(AVG(100.0 * SUM(subscribed) / COUNT(*))
          OVER (ORDER BY campaign ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING), 2)
                                                      AS smoothed_rate_pct
FROM contacts
WHERE call_connected = 1
  AND campaign <= 15
GROUP BY campaign
ORDER BY campaign;


-- ── Q3: Month-over-month subscription patterns ───────────────
SELECT
    month,
    month_num,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(duration_min), 2)                       AS avg_call_min,
    -- Prior month conversion for comparison
    LAG(ROUND(100.0 * SUM(subscribed) / COUNT(*), 1))
        OVER (ORDER BY month_num)                     AS prev_month_rate
FROM contacts
WHERE call_connected = 1
GROUP BY month, month_num
ORDER BY month_num;


-- ── Q4: Balance segment analysis ─────────────────────────────
SELECT
    balance_segment,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(age), 1)                                AS avg_age,
    ROUND(AVG(balance), 0)                            AS avg_balance_eur,
    ROUND(AVG(duration_min), 2)                       AS avg_call_min
FROM contacts
WHERE call_connected = 1
  AND balance_segment IS NOT NULL
GROUP BY balance_segment
ORDER BY
    CASE balance_segment
        WHEN 'negative'  THEN 1
        WHEN 'low'       THEN 2
        WHEN 'medium'    THEN 3
        WHEN 'high'      THEN 4
        WHEN 'very_high' THEN 5
    END;


-- ── Q5: Previous campaign effect ─────────────────────────────
SELECT
    was_previously_contacted,
    poutcome                                          AS prev_outcome,
    COUNT(*)                                          AS contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(pdays_clean), 0)                        AS avg_days_since_last_contact
FROM contacts
WHERE call_connected = 1
GROUP BY was_previously_contacted, poutcome
ORDER BY conversion_rate_pct DESC;


-- ── Q6: Age group breakdown ───────────────────────────────────
SELECT
    age_group,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(balance), 0)                            AS avg_balance_eur,
    ROUND(AVG(duration_min), 2)                       AS avg_call_min,
    ROUND(AVG(campaign), 2)                           AS avg_calls_needed
FROM contacts
WHERE call_connected = 1
  AND age_group IS NOT NULL
GROUP BY age_group
ORDER BY age_group;


-- ── Q7: High-value segments (balance > 2000 + subscribed) ────
WITH high_value AS (
    SELECT
        job,
        age_group,
        COUNT(*)                                      AS converted,
        ROUND(AVG(balance), 0)                        AS avg_balance,
        ROUND(AVG(duration_min), 2)                   AS avg_call_min
    FROM contacts
    WHERE subscribed = 1
      AND balance > 2000
      AND call_connected = 1
    GROUP BY job, age_group
    HAVING COUNT(*) >= 10
)
SELECT *
FROM high_value
ORDER BY converted DESC;


-- ── Q8: Default / loan risk vs subscription ───────────────────
SELECT
    "default"                                         AS in_default,
    housing                                           AS has_housing_loan,
    loan                                              AS has_personal_loan,
    COUNT(*)                                          AS contacts,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(balance), 0)                            AS avg_balance_eur
FROM contacts
WHERE call_connected = 1
GROUP BY "default", housing, loan
ORDER BY conversion_rate_pct DESC;

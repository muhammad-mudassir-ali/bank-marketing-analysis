"""
03_sql_analysis.py
------------------
Loads cleaned data into SQLite (no server needed),
runs business-question SQL queries, saves results.

Business Questions:
  Q1. Which job + education segments have the highest subscription rates?
  Q2. How does campaign contact frequency affect conversion — at what point
      do more calls hurt more than help?
  Q3. Which months drive the most subscriptions? Is there a seasonal pattern?
  Q4. Does balance level predict subscription likelihood?
  Q5. Are customers with no previous contact harder to convert?
"""

import pandas as pd
import sqlite3
import os

CLEAN_PATH = "data/cleaned/bank_clean.csv"
DB_PATH    = "data/bank.db"
SQL_OUT    = "outputs"

os.makedirs(SQL_OUT, exist_ok=True)

# ── Load into SQLite ──────────────────────────────────────────────────────────
df = pd.read_csv(CLEAN_PATH)

conn = sqlite3.connect(DB_PATH)
df.to_sql("contacts", conn, if_exists="replace", index=False)
print(f"Loaded {len(df):,} rows into SQLite table 'contacts'")
print(f"Database: {DB_PATH}\n")

# ── Helper ────────────────────────────────────────────────────────────────────
def run_query(sql, label):
    result = pd.read_sql_query(sql, conn)
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(result.to_string(index=False))
    result.to_csv(f"{SQL_OUT}/{label.replace(' ', '_').replace(':', '').lower()}.csv", index=False)
    return result

# ── Q1: Subscription rate by job and education ────────────────────────────────
run_query("""
SELECT
    job,
    education,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(balance), 0)                            AS avg_balance
FROM contacts
WHERE call_connected = 1
GROUP BY job, education
HAVING COUNT(*) >= 100
ORDER BY conversion_rate_pct DESC
LIMIT 20
""", "Q1: Top Segments by Conversion Rate")

# ── Q2: Contact frequency vs conversion ───────────────────────────────────────
run_query("""
SELECT
    campaign                                          AS num_calls,
    COUNT(*)                                          AS contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 2)      AS conversion_rate_pct
FROM contacts
WHERE call_connected = 1
  AND campaign <= 15
GROUP BY campaign
ORDER BY campaign
""", "Q2: Conversion Rate by Number of Calls")

# ── Q3: Monthly subscription patterns ─────────────────────────────────────────
run_query("""
SELECT
    month,
    month_num,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(duration_min), 2)                       AS avg_call_duration_min
FROM contacts
WHERE call_connected = 1
GROUP BY month, month_num
ORDER BY month_num
""", "Q3: Monthly Subscription Patterns")

# ── Q4: Balance segment vs subscription ───────────────────────────────────────
run_query("""
SELECT
    balance_segment,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(age), 1)                                AS avg_age,
    ROUND(AVG(balance), 0)                            AS avg_balance
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
    END
""", "Q4: Subscription Rate by Balance Segment")

# ── Q5: Previous contact effect ───────────────────────────────────────────────
run_query("""
SELECT
    was_previously_contacted,
    poutcome                                          AS previous_outcome,
    COUNT(*)                                          AS contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct
FROM contacts
WHERE call_connected = 1
GROUP BY was_previously_contacted, poutcome
ORDER BY conversion_rate_pct DESC
""", "Q5: Previous Contact Effect on Conversion")

# ── Bonus: Age group breakdown ────────────────────────────────────────────────
run_query("""
SELECT
    age_group,
    COUNT(*)                                          AS total_contacts,
    SUM(subscribed)                                   AS subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 1)      AS conversion_rate_pct,
    ROUND(AVG(balance), 0)                            AS avg_balance,
    ROUND(AVG(duration_min), 2)                       AS avg_call_min
FROM contacts
WHERE call_connected = 1
  AND age_group IS NOT NULL
GROUP BY age_group
ORDER BY age_group
""", "Q6: Subscription Rate by Age Group")

# ── Bonus: Overall summary stats ──────────────────────────────────────────────
run_query("""
SELECT
    COUNT(*)                                          AS total_contacts,
    SUM(call_connected)                               AS connected_calls,
    SUM(subscribed)                                   AS total_subscriptions,
    ROUND(100.0 * SUM(subscribed) / COUNT(*), 2)      AS overall_conversion_pct,
    ROUND(AVG(duration_min), 2)                       AS avg_call_min,
    ROUND(AVG(campaign), 2)                           AS avg_calls_per_contact,
    ROUND(AVG(balance), 0)                            AS avg_balance
FROM contacts
""", "Q0: Overall Summary")

conn.close()
print("\nAll queries complete. Results saved to outputs/")

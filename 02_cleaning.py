"""
02_cleaning.py
--------------
Cleans the raw Bank Marketing dataset.
Documents every decision made and why.

Business Question:
  Which customer segments are most likely to subscribe to a term deposit,
  and what does the campaign outreach pattern look like across those segments?
"""

import pandas as pd
import numpy as np
import os

RAW_PATH   = "data/raw/bank-full.csv"
CLEAN_PATH = "data/cleaned/bank_clean.csv"

os.makedirs("data/cleaned", exist_ok=True)

# ── Load raw ──────────────────────────────────────────────────────────────────
df = pd.read_csv(RAW_PATH, sep=";")
original_shape = df.shape
print(f"Raw shape: {df.shape}")

# ── 1. Understand the columns ─────────────────────────────────────────────────
# age        - numeric
# job        - categorical: type of job
# marital    - categorical: marital status
# education  - categorical: education level
# default    - has credit in default? (yes/no)
# balance    - average yearly balance in euros
# housing    - has housing loan? (yes/no)
# loan       - has personal loan? (yes/no)
# contact    - contact communication type (cellular/telephone/unknown)
# day        - last contact day of the month
# month      - last contact month of the year
# duration   - last contact duration in seconds
# campaign   - number of contacts during this campaign
# pdays      - days since last contact from previous campaign (-1 = never contacted)
# previous   - number of contacts before this campaign
# poutcome   - outcome of previous campaign
# y          - TARGET: subscribed to term deposit? (yes/no)

# ── 2. Duplicate check ────────────────────────────────────────────────────────
dups = df.duplicated().sum()
print(f"\nDuplicate rows: {dups}")
# These are NOT duplicates — same person can be contacted multiple times.
# The dataset is contact-level, not customer-level.

# ── 3. Null / unknown audit ───────────────────────────────────────────────────
print("\nNull counts:")
print(df.isnull().sum())

# No actual NaN values — but "unknown" is used as a category for missing values
print("\nUnknown counts per column:")
for col in df.select_dtypes(include='object').columns:
    n_unknown = (df[col] == 'unknown').sum()
    if n_unknown > 0:
        pct = n_unknown / len(df) * 100
        print(f"  {col}: {n_unknown} ({pct:.1f}%)")

# Decision: keep 'unknown' as its own category — it may have predictive signal.
# Dropping 14,000+ rows (30%+ of data) to remove unknowns would be wrong.

# ── 4. Data type corrections ──────────────────────────────────────────────────
# Create proper month order for sorting
month_order = ['jan','feb','mar','apr','may','jun',
               'jul','aug','sep','oct','nov','dec']
df['month'] = pd.Categorical(df['month'], categories=month_order, ordered=True)
df['month_num'] = df['month'].cat.codes + 1  # 1-12

# Encode target as binary integer (easier for analysis)
df['subscribed'] = (df['y'] == 'yes').astype(int)

# ── 5. Fix known data issues ──────────────────────────────────────────────────

# pdays = -1 means "never contacted before" — replace with NaN for clarity,
# then create a boolean flag that's more readable
df['was_previously_contacted'] = df['pdays'] != -1
df['pdays_clean'] = df['pdays'].replace(-1, np.nan)

# duration note: duration = 0 means the call never happened (contact failed).
# These rows have y = 'no' by definition — they're not real decisions.
# Flag them but keep for now; we'll exclude from conversion analysis.
df['call_connected'] = df['duration'] > 0
zero_duration = (df['duration'] == 0).sum()
print(f"\nRows with 0-second calls (call never connected): {zero_duration}")

# ── 6. Derived features ───────────────────────────────────────────────────────

# Age groups — meaningful for banking segmentation
df['age_group'] = pd.cut(
    df['age'],
    bins=[0, 24, 34, 44, 54, 64, 100],
    labels=['18-24', '25-34', '35-44', '45-54', '55-64', '65+']
)

# Balance segments
df['balance_segment'] = pd.cut(
    df['balance'],
    bins=[-10000, 0, 500, 2000, 5000, 200000],
    labels=['negative', 'low', 'medium', 'high', 'very_high']
)

# Duration in minutes (more readable than seconds)
df['duration_min'] = (df['duration'] / 60).round(2)

# Call intensity — campaign contacts bucketed
df['call_intensity'] = pd.cut(
    df['campaign'],
    bins=[0, 1, 3, 5, 100],
    labels=['1_call', '2-3_calls', '4-5_calls', '6+_calls']
)

# ── 7. Standardise string columns ─────────────────────────────────────────────
for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].str.strip().str.lower()

# ── 8. Outlier audit (no removal — just flag for transparency) ────────────────
q99_balance = df['balance'].quantile(0.99)
q01_balance = df['balance'].quantile(0.01)
q99_duration = df['duration'].quantile(0.99)
q99_campaign = df['campaign'].quantile(0.99)

print(f"\nBalance range: {df['balance'].min()} to {df['balance'].max()}")
print(f"Balance 1st-99th percentile: {q01_balance:.0f} to {q99_balance:.0f}")
print(f"Duration max: {df['duration'].max()}s ({df['duration'].max()/60:.1f} min)")
print(f"Campaign contacts max: {df['campaign'].max()}")
print(f"99th pct campaign: {q99_campaign}")

# Flag extreme outliers for visibility (keeping them — they're real data)
df['balance_outlier'] = (df['balance'] < q01_balance) | (df['balance'] > q99_balance)
df['long_call'] = df['duration'] > q99_duration

# ── 9. Cleaning summary ───────────────────────────────────────────────────────
cleaning_log = {
    "original_rows":         original_shape[0],
    "original_columns":      original_shape[1],
    "final_rows":            len(df),
    "final_columns":         len(df.columns),
    "rows_removed":          0,  # we kept all rows, used flags instead
    "duplicate_rows":        dups,
    "zero_duration_calls":   zero_duration,
    "new_features_added":    ["subscribed", "was_previously_contacted", "pdays_clean",
                               "call_connected", "age_group", "balance_segment",
                               "duration_min", "call_intensity", "month_num",
                               "balance_outlier", "long_call"],
}

print("\n── Cleaning Log ─────────────────────────────────────────────────")
for k, v in cleaning_log.items():
    print(f"  {k}: {v}")

# ── 10. Save ──────────────────────────────────────────────────────────────────
df.to_csv(CLEAN_PATH, index=False)
print(f"\nSaved cleaned data to: {CLEAN_PATH}")
print(f"Final shape: {df.shape}")

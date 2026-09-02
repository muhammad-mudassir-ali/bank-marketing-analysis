"""
05_cohort_retention.py
----------------------
Cohort/Retention analysis on the bank marketing data.

We treat each campaign month as a cohort — customers first
contacted in month X — and track how many from that cohort
were contacted again in subsequent months (re-engagement rate)
AND how subscription rates vary by cohort.

This answers:
  - Are newer cohorts converting better or worse over time?
  - Which cohorts had the highest long-term re-engagement?
  - Is there a "warming up" effect (contacted 2-3x before converting)?
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import os

CLEAN_PATH = "data/cleaned/bank_clean.csv"
CHART_DIR  = "outputs/charts"
os.makedirs(CHART_DIR, exist_ok=True)

df = pd.read_csv(CLEAN_PATH)
df = df[df['call_connected'] == True].copy()

print(f"Working dataset: {len(df):,} connected calls")
print(f"Unique months: {sorted(df['month'].unique())}")
print(f"Month range: {df['month_num'].min()} – {df['month_num'].max()}")

# ── Part A: Cohort Subscription Rate Analysis ─────────────────────────────────
# Cohort = month customer was first contacted
# We want: for each cohort month, what % subscribed?

print("\n── Part A: Subscription Rates by Contact Month Cohort ──────────")

# Since we don't have a true customer ID over time in this dataset,
# we define cohorts by the month of contact and analyse subscription
# rates + average call metrics across cohorts.

cohort_stats = (
    df.groupby('month_num')
      .agg(
          month=('month', 'first'),
          total_contacts=('subscribed', 'count'),
          subscriptions=('subscribed', 'sum'),
          avg_balance=('balance', 'mean'),
          avg_duration_min=('duration_min', 'mean'),
          avg_calls=('campaign', 'mean'),
      )
      .assign(conversion_rate=lambda x: x['subscriptions'] / x['total_contacts'])
      .reset_index()
      .sort_values('month_num')
)

print(cohort_stats[['month', 'total_contacts', 'subscriptions',
                     'conversion_rate', 'avg_calls']].to_string(index=False))

# ── Part B: Campaign Exposure Cohorts ────────────────────────────────────────
# Cohort = number of calls received (campaign column)
# Tracks how subscription rate decays/grows with more contact attempts

print("\n── Part B: Conversion by Campaign Exposure Cohort ─────────────")

exposure_cohort = (
    df[df['campaign'] <= 10]
      .groupby('campaign')
      .agg(
          contacts=('subscribed', 'count'),
          subscriptions=('subscribed', 'sum'),
      )
      .assign(conversion_rate=lambda x: x['subscriptions'] / x['contacts'])
      .reset_index()
)
print(exposure_cohort.to_string(index=False))

# ── Part C: Previous Campaign Cohort Retention Matrix ─────────────────────────
# Cross cohort: previous outcome × current campaign calls
# Shows if a "warm" lead from a previous campaign converts at different rates

print("\n── Part C: Previous Outcome × Current Campaign Calls Matrix ────")

matrix_df = df[df['campaign'] <= 8].copy()
pivot = matrix_df.pivot_table(
    values='subscribed',
    index='poutcome',
    columns='campaign',
    aggfunc='mean'
).round(3)
print(pivot)

# ── Visualizations ────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 14))
fig.suptitle("Cohort & Retention Analysis — Bank Marketing Campaign",
             fontsize=15, fontweight='bold', y=1.01)

# ── Chart 1: Monthly cohort conversion rates ──────────────────────────────────
ax1 = fig.add_subplot(2, 2, 1)
months_order = cohort_stats['month'].tolist()
colors_bar   = ['#2ECC71' if r > cohort_stats['conversion_rate'].mean() else '#E74C3C'
                for r in cohort_stats['conversion_rate']]

bars = ax1.bar(cohort_stats['month'], cohort_stats['conversion_rate'] * 100,
               color=colors_bar, edgecolor='white', linewidth=0.8)
ax1.axhline(cohort_stats['conversion_rate'].mean() * 100, color='navy',
            linestyle='--', linewidth=1.5, label=f"Mean: {cohort_stats['conversion_rate'].mean():.1%}")
ax1.set_title('Subscription Rate by Contact Month\n(Green = above average)', fontsize=11)
ax1.set_xlabel('Month of Contact')
ax1.set_ylabel('Conversion Rate (%)')
ax1.legend()
ax1.tick_params(axis='x', rotation=45)
ax1.spines[['top', 'right']].set_visible(False)
for bar, rate in zip(bars, cohort_stats['conversion_rate']):
    if rate > 0.15:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f'{rate:.0%}', ha='center', va='bottom', fontsize=8)

# ── Chart 2: Contact volume vs conversion rate scatter ────────────────────────
ax2 = fig.add_subplot(2, 2, 2)
scatter = ax2.scatter(
    cohort_stats['total_contacts'],
    cohort_stats['conversion_rate'] * 100,
    s=cohort_stats['total_contacts'] / 30,
    c=cohort_stats['month_num'],
    cmap='viridis', alpha=0.8, edgecolors='white', linewidth=1
)
for _, row in cohort_stats.iterrows():
    ax2.annotate(row['month'], (row['total_contacts'], row['conversion_rate']*100),
                 fontsize=8, ha='left', va='bottom', xytext=(5, 3), textcoords='offset points')
plt.colorbar(scatter, ax=ax2, label='Month (1=Jan, 12=Dec)')
ax2.set_title('Contact Volume vs Conversion Rate\n(bubble size = contact volume)', fontsize=11)
ax2.set_xlabel('Total Contacts in Month')
ax2.set_ylabel('Conversion Rate (%)')
ax2.spines[['top', 'right']].set_visible(False)

# ── Chart 3: Campaign exposure decay curve ────────────────────────────────────
ax3 = fig.add_subplot(2, 2, 3)
ax3.plot(exposure_cohort['campaign'], exposure_cohort['conversion_rate'] * 100,
         'o-', color='#3498DB', linewidth=2.5, markersize=8, markerfacecolor='white',
         markeredgewidth=2)
ax3.fill_between(exposure_cohort['campaign'], exposure_cohort['conversion_rate'] * 100,
                 alpha=0.15, color='#3498DB')

# Label optimal point
best_idx = exposure_cohort['conversion_rate'].idxmax()
best_row = exposure_cohort.loc[best_idx]
ax3.annotate(f"Peak: {best_row['conversion_rate']:.1%}\nat call #{best_row['campaign']:.0f}",
             xy=(best_row['campaign'], best_row['conversion_rate']*100),
             xytext=(best_row['campaign']+0.8, best_row['conversion_rate']*100 + 1),
             arrowprops=dict(arrowstyle='->', color='red'),
             fontsize=9, color='red')

ax3.set_title('Conversion Rate Decay Curve\n(How many calls is too many?)', fontsize=11)
ax3.set_xlabel('Number of Campaign Calls')
ax3.set_ylabel('Conversion Rate (%)')
ax3.spines[['top', 'right']].set_visible(False)

# ── Chart 4: Heatmap — previous outcome × campaign calls ─────────────────────
ax4 = fig.add_subplot(2, 2, 4)
sns.heatmap(
    pivot * 100,
    annot=True, fmt='.1f',
    cmap='YlOrRd',
    linewidths=0.5,
    cbar_kws={'label': 'Conversion Rate (%)'},
    ax=ax4
)
ax4.set_title('Retention Heatmap\nPrevious Outcome × Calls This Campaign (%)', fontsize=11)
ax4.set_xlabel('Number of Calls This Campaign')
ax4.set_ylabel('Previous Campaign Outcome')

plt.tight_layout()
plt.savefig(f"{CHART_DIR}/cohort_retention.png", dpi=150, bbox_inches='tight')
print(f"\nChart saved to {CHART_DIR}/cohort_retention.png")

# ── Written Insights ──────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  COHORT ANALYSIS — KEY INSIGHTS")
print("="*60)

best_month  = cohort_stats.loc[cohort_stats['conversion_rate'].idxmax(), 'month']
worst_month = cohort_stats.loc[cohort_stats['conversion_rate'].idxmin(), 'month']
best_rate   = cohort_stats['conversion_rate'].max()
worst_rate  = cohort_stats['conversion_rate'].min()
mean_rate   = cohort_stats['conversion_rate'].mean()

print(f"""
Monthly Cohort Insights:
  Best month:  {best_month.upper()} — {best_rate:.1%} conversion
  Worst month: {worst_month.upper()} — {worst_rate:.1%} conversion
  Average:     {mean_rate:.1%}
  Spread:      {(best_rate - worst_rate)*100:.1f} percentage points difference
               between best and worst month

Campaign Exposure Insights:
  At what call count does conversion peak?
  → Call #{best_row['campaign']:.0f} — {best_row['conversion_rate']:.1%}
  
  After that peak, more calls = diminishing returns.
  Recommendation: Cap campaign contacts per customer at
  {best_row['campaign']:.0f}-{best_row['campaign']+1:.0f} calls to protect
  conversion rates and reduce wasted agent time.

Previous Campaign Effect:
  Customers with a SUCCESSFUL previous outcome convert at
  dramatically higher rates. These are the warmest leads.
  
  Prioritise re-contacting previous 'success' cohorts first,
  before investing in cold outreach.
""")

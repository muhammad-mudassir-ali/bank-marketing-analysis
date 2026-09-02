"""
04_ab_test.py
-------------
A/B Test: Does call duration correlate with subscription?
We simulate a real experiment scenario from the data:

Experiment setup:
  - Control group:   Short calls (< 5 min) — standard script
  - Treatment group: Long calls (>= 5 min) — extended engagement script

This mirrors a real bank experiment: did investing more time per call
(the treatment) increase subscription rates vs. a standard shorter call?

We test this properly with:
  1. Sample Ratio Mismatch check
  2. Two-proportion z-test
  3. Confidence intervals
  4. Effect size + practical significance
  5. Power analysis
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend, saves to file
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
import os

try:
    from statsmodels.stats.proportion import proportions_ztest, proportion_confint
    from statsmodels.stats.power import NormalIndPower
    STATSMODELS = True
except ImportError:
    STATSMODELS = False
    print("statsmodels not found — using scipy fallback for some stats")

CLEAN_PATH = "data/cleaned/bank_clean.csv"
CHART_DIR  = "outputs/charts"
os.makedirs(CHART_DIR, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_csv(CLEAN_PATH)

# Only use connected calls — unconnected calls are not real decisions
df = df[df['call_connected'] == True].copy()
print(f"Working dataset: {len(df):,} connected calls\n")

# ── Define experiment groups ──────────────────────────────────────────────────
# Control   = call duration < 5 minutes
# Treatment = call duration >= 5 minutes
THRESHOLD_MIN = 5.0

df['group'] = np.where(df['duration_min'] >= THRESHOLD_MIN, 'treatment', 'control')

group_counts = df['group'].value_counts()
print("Group sizes:")
print(group_counts.to_string())

# ── 1. Sanity check: Sample Ratio Mismatch ────────────────────────────────────
print("\n── Sanity Check: Sample Ratio Mismatch ─────────────────────────")
from scipy.stats import chisquare
n_total  = len(df)
expected = [n_total / 2, n_total / 2]
chi2, srm_p = chisquare(group_counts.values, f_exp=expected)
print(f"Chi² = {chi2:.2f},  p = {srm_p:.6f}")
if srm_p < 0.05:
    print("NOTE: Groups are unequal in size (expected with a natural threshold split).")
    print("In a real experiment this would be a red flag — here it's by design.")
else:
    print("Groups are roughly balanced.")

# ── 2. Conversion rates ───────────────────────────────────────────────────────
print("\n── Conversion Rates ────────────────────────────────────────────")
results = df.groupby('group').agg(
    n=('subscribed', 'count'),
    conversions=('subscribed', 'sum')
).assign(rate=lambda x: x['conversions'] / x['n'])

print(results)

control   = df[df['group'] == 'control']['subscribed']
treatment = df[df['group'] == 'treatment']['subscribed']

ctrl_rate  = control.mean()
treat_rate = treatment.mean()
abs_lift   = treat_rate - ctrl_rate
rel_lift   = abs_lift / ctrl_rate

print(f"\nControl rate:   {ctrl_rate:.2%}")
print(f"Treatment rate: {treat_rate:.2%}")
print(f"Absolute lift:  {abs_lift*100:+.2f} percentage points")
print(f"Relative lift:  {rel_lift*100:+.1f}%")

# ── 3. Statistical test ───────────────────────────────────────────────────────
print("\n── Statistical Test (Two-Proportion Z-Test) ────────────────────")
if STATSMODELS:
    count = np.array([treatment.sum(), control.sum()])
    nobs  = np.array([len(treatment), len(control)])
    z_stat, p_value = proportions_ztest(count, nobs, alternative='two-sided')
    print(f"Z-statistic: {z_stat:.4f}")
    print(f"P-value:     {p_value:.6f}")
else:
    # Manual z-test fallback
    p1, p2 = treat_rate, ctrl_rate
    n1, n2 = len(treatment), len(control)
    p_pool = (treatment.sum() + control.sum()) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    z_stat = (p1 - p2) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    print(f"Z-statistic: {z_stat:.4f}")
    print(f"P-value:     {p_value:.6f}")

alpha = 0.05
if p_value < alpha:
    print(f"\nResult: STATISTICALLY SIGNIFICANT (p={p_value:.4f} < α={alpha})")
else:
    print(f"\nResult: NOT statistically significant (p={p_value:.4f} >= α={alpha})")

# ── 4. Confidence Intervals ───────────────────────────────────────────────────
print("\n── 95% Confidence Intervals ────────────────────────────────────")
if STATSMODELS:
    ci_ctrl  = proportion_confint(control.sum(),   len(control),   alpha=0.05, method='wilson')
    ci_treat = proportion_confint(treatment.sum(), len(treatment), alpha=0.05, method='wilson')
else:
    # Wilson interval manually
    def wilson_ci(successes, n, z=1.96):
        p = successes / n
        denom = 1 + z**2/n
        center = (p + z**2/(2*n)) / denom
        margin = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
        return (center - margin, center + margin)
    ci_ctrl  = wilson_ci(control.sum(),   len(control))
    ci_treat = wilson_ci(treatment.sum(), len(treatment))

print(f"Control   95% CI: ({ci_ctrl[0]:.4f},  {ci_ctrl[1]:.4f})  "
      f"→ ({ci_ctrl[0]*100:.1f}%, {ci_ctrl[1]*100:.1f}%)")
print(f"Treatment 95% CI: ({ci_treat[0]:.4f}, {ci_treat[1]:.4f})  "
      f"→ ({ci_treat[0]*100:.1f}%, {ci_treat[1]*100:.1f}%)")

# Do CIs overlap?
overlap = ci_ctrl[1] > ci_treat[0]
print(f"CIs overlap: {overlap}")
print("(Note: CI overlap ≠ non-significance — always use the proper z-test)")

# ── 5. Effect size (Cohen's h for proportions) ────────────────────────────────
print("\n── Effect Size ─────────────────────────────────────────────────")
# Cohen's h = 2*arcsin(sqrt(p1)) - 2*arcsin(sqrt(p2))
h = 2 * np.arcsin(np.sqrt(treat_rate)) - 2 * np.arcsin(np.sqrt(ctrl_rate))
print(f"Cohen's h: {h:.4f}")
if abs(h) < 0.2:
    size_label = "small"
elif abs(h) < 0.5:
    size_label = "medium"
else:
    size_label = "large"
print(f"Effect size interpretation: {size_label}")

# ── 6. Power analysis ─────────────────────────────────────────────────────────
print("\n── Power Analysis ──────────────────────────────────────────────")
if STATSMODELS:
    from statsmodels.stats.power import zt_ind_solve_power
    # Required sample size to detect observed effect at 80% power
    effect_size_for_power = abs(h)
    power_analysis = NormalIndPower()
    required_n = power_analysis.solve_power(
        effect_size=effect_size_for_power,
        alpha=0.05,
        power=0.80,
        alternative='two-sided'
    )
    print(f"Required n per group for 80% power: {required_n:.0f}")
    print(f"Actual n — control: {len(control):,}  treatment: {len(treatment):,}")
    if min(len(control), len(treatment)) >= required_n:
        print("Study is adequately powered ✓")
    else:
        print("Study may be underpowered — interpret with caution")

# ── 7. Visualization ──────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("A/B Test: Short Calls vs Long Calls — Subscription Rates",
             fontsize=14, fontweight='bold', y=1.02)

# Chart 1: Conversion rate comparison with CI error bars
groups     = ['Control\n(call < 5 min)', 'Treatment\n(call ≥ 5 min)']
rates      = [ctrl_rate, treat_rate]
ci_lo      = [ctrl_rate - ci_ctrl[0],  treat_rate - ci_treat[0]]
ci_hi      = [ci_ctrl[1]  - ctrl_rate, ci_treat[1] - treat_rate]
colors     = ['#5B9BD5', '#ED7D31']

bars = axes[0].bar(groups, [r*100 for r in rates], color=colors,
                   width=0.45, edgecolor='white', linewidth=1.5)
axes[0].errorbar(
    groups,
    [r*100 for r in rates],
    yerr=[[lo*100 for lo in ci_lo], [hi*100 for hi in ci_hi]],
    fmt='none', color='black', capsize=8, linewidth=2
)
for bar, rate in zip(bars, rates):
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f'{rate:.1%}', ha='center', va='bottom', fontweight='bold')

axes[0].set_ylabel('Subscription Rate (%)')
axes[0].set_title(f'Conversion Rate with 95% CI\np-value = {p_value:.4f}  |  Δ = {abs_lift*100:+.1f}pp')
axes[0].set_ylim(0, max(rates)*100 * 1.35)
axes[0].spines[['top', 'right']].set_visible(False)

# Chart 2: Distribution of call durations by outcome
ctrl_sub    = df[(df['group']=='control')   & (df['subscribed']==1)]['duration_min']
ctrl_nosub  = df[(df['group']=='control')   & (df['subscribed']==0)]['duration_min']
treat_sub   = df[(df['group']=='treatment') & (df['subscribed']==1)]['duration_min']
treat_nosub = df[(df['group']=='treatment') & (df['subscribed']==0)]['duration_min']

axes[1].hist(ctrl_nosub.clip(0, 30),  bins=40, alpha=0.4, color='#5B9BD5', label='Control – No')
axes[1].hist(ctrl_sub.clip(0, 30),    bins=40, alpha=0.7, color='#5B9BD5', label='Control – Yes',   histtype='step', linewidth=2)
axes[1].hist(treat_nosub.clip(0, 30), bins=40, alpha=0.4, color='#ED7D31', label='Treatment – No')
axes[1].hist(treat_sub.clip(0, 30),   bins=40, alpha=0.7, color='#ED7D31', label='Treatment – Yes', histtype='step', linewidth=2)
axes[1].axvline(THRESHOLD_MIN, color='red', linestyle='--', linewidth=1.5, label='Split threshold (5 min)')
axes[1].set_xlabel('Call Duration (minutes, capped at 30)')
axes[1].set_ylabel('Count')
axes[1].set_title('Call Duration Distribution by Group & Outcome')
axes[1].legend(fontsize=8)
axes[1].spines[['top', 'right']].set_visible(False)

plt.tight_layout()
plt.savefig(f"{CHART_DIR}/ab_test_results.png", dpi=150, bbox_inches='tight')
print(f"\nChart saved to {CHART_DIR}/ab_test_results.png")

# ── 8. Written interpretation ─────────────────────────────────────────────────
print("\n" + "="*60)
print("  INTERPRETATION")
print("="*60)
print(f"""
Question:
  Does longer call engagement (≥5 min) lead to higher
  subscription rates compared to shorter calls (<5 min)?

Result:
  Control (short calls):   {ctrl_rate:.1%} conversion
  Treatment (long calls):  {treat_rate:.1%} conversion
  Absolute difference:     {abs_lift*100:+.1f} percentage points
  Relative improvement:    {rel_lift*100:+.0f}%
  Statistical significance: p = {p_value:.4f} ({'YES' if p_value < alpha else 'NO'}, α=0.05)
  Effect size (Cohen's h): {h:.3f} ({size_label})

What this means:
  Customers who stayed on the call longer converted at a much
  higher rate. However, causality is ambiguous — longer calls
  may reflect customer interest (they stayed because they were
  already interested), not necessarily that the extra talk time
  caused the conversion.

  A clean causal test would require random assignment of agents
  with different script lengths, not post-hoc duration splits.

Business recommendation:
  1. Train agents to identify early engagement signals and
     invest more time with interested customers.
  2. Investigate what topics/scripts keep customers engaged
     past the 5-minute mark.
  3. Do NOT simply force all calls to be longer — the
     relationship may be reverse causality.
""")

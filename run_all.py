"""
run_all.py
----------
Runs the entire pipeline in sequence:
  1. Pull data from UCI
  2. Clean
  3. SQL analysis
  4. A/B test
  5. Cohort / retention
"""

import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

steps = [
    ("01_data_pull.py",       "Step 1: Pull data"),
    ("02_cleaning.py",        "Step 2: Clean data"),
    ("03_sql_analysis.py",    "Step 3: SQL analysis"),
    ("04_ab_test.py",         "Step 4: A/B test"),
    ("05_cohort_retention.py","Step 5: Cohort/Retention"),
]

for script, label in steps:
    print(f"\n{'#'*60}")
    print(f"  {label}")
    print(f"{'#'*60}\n")
    result = subprocess.run([sys.executable, script], capture_output=False)
    if result.returncode != 0:
        print(f"\n❌ {script} failed with exit code {result.returncode}")
        print("Fix the error above and re-run, or run individual scripts.")
        sys.exit(result.returncode)
    print(f"\n✓ {label} complete")

print("\n" + "="*60)
print("  ALL STEPS COMPLETE")
print("  Charts saved to: outputs/charts/")
print("  SQL results:     outputs/*.csv")
print("  Database:        data/bank.db")
print("="*60)

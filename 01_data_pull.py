"""
01_data_pull.py
---------------
Pulls the Bank Marketing dataset from UCI ML Repository.
Real Portuguese bank telemarketing data (2008-2013).
No login required.

Dataset: https://archive.ics.uci.edu/dataset/222/bank+marketing
"""

import requests
import zipfile
import io
import os
import pandas as pd

RAW_DIR = "data/raw"
os.makedirs(RAW_DIR, exist_ok=True)

# ── Download ──────────────────────────────────────────────────────────────────
print("Downloading Bank Marketing dataset from UCI...")

url = "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip"
response = requests.get(url, timeout=30)
response.raise_for_status()

print(f"Downloaded {len(response.content) / 1024:.0f} KB")

# ── Unzip ─────────────────────────────────────────────────────────────────────
with zipfile.ZipFile(io.BytesIO(response.content)) as outer_zip:
    print("Files in outer zip:", outer_zip.namelist())

    # The inner zip is bank.zip
    with outer_zip.open("bank.zip") as inner_file:
        with zipfile.ZipFile(io.BytesIO(inner_file.read())) as inner_zip:
            print("Files in inner zip:", inner_zip.namelist())
            inner_zip.extractall(RAW_DIR)

print(f"\nExtracted to {RAW_DIR}/")

# ── Quick look ────────────────────────────────────────────────────────────────
# bank-full.csv  = 45,211 rows (all contacts)
# bank.csv       = 4,521 rows (10% sample)
# We use the full dataset

df = pd.read_csv(f"{RAW_DIR}/bank-full.csv", sep=";")

print(f"\nShape: {df.shape}")
print(f"\nColumn names:\n{df.columns.tolist()}")
print(f"\nFirst 5 rows:")
print(df.head())
print(f"\nData types:")
print(df.dtypes)
print(f"\nNull counts:")
print(df.isnull().sum())
print(f"\nBasic stats:")
print(df.describe(include='all'))

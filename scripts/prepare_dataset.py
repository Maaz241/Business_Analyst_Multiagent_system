"""
Data Preparation Script for NovaMart.
Loads raw Excel (Year 2009-2010 & Year 2010-2011) or existing sales.csv,
cleans transactions deterministically, generates derived tables, and saves processed CSV files.

Usage:
    python scripts/prepare_dataset.py
"""

import sys
import time
from pathlib import Path
import pandas as pd

# Ensure standard UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import (
    DEFAULT_RAW_FILE,
    PROCESSED_DATA_DIR,
    DEFAULT_SALES_FILE,
    DEFAULT_CUSTOMERS_FILE,
    DEFAULT_PRODUCTS_FILE,
    DEFAULT_TARGETS_FILE,
)
from app.data.cleaner import DataCleaningPipeline
from app.utils.logging import logger


def main():
    print("==================================================")
    print("       NovaMart Data Preparation Pipeline        ")
    print("==================================================\n")

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    cleaner = DataCleaningPipeline()
    start_time = time.time()

    if DEFAULT_SALES_FILE.exists() and DEFAULT_SALES_FILE.stat().st_size > 1000:
        print(f"Detected existing cleaned sales dataset at: {DEFAULT_SALES_FILE.name}")
        print("Loading sales.csv to generate customers, products, and targets...")
        sales_df = pd.read_csv(
            DEFAULT_SALES_FILE,
            dtype={"order_id": str, "customer_id": str, "product_id": str, "country": str, "category": str},
            parse_dates=["order_date"],
        )
        print(f"Loaded {len(sales_df):,} sales rows.")
    else:
        if not DEFAULT_RAW_FILE.exists():
            print(f"Error: Raw data file not found at {DEFAULT_RAW_FILE}")
            sys.exit(1)

        print(f"Loading raw Excel dataset from: {DEFAULT_RAW_FILE.name}...")
        print("Reading sheets 'Year 2009-2010' and 'Year 2010-2011'...")
        excel_file = pd.ExcelFile(DEFAULT_RAW_FILE)
        frames = []
        for sheet in excel_file.sheet_names:
            print(f"  -> Reading sheet: {sheet}...")
            sheet_df = pd.read_excel(excel_file, sheet_name=sheet)
            print(f"     Loaded {len(sheet_df):,} rows.")
            frames.append(sheet_df)

        raw_df = pd.concat(frames, ignore_index=True)
        print(f"Total raw records loaded: {len(raw_df):,}\n")

        print("Running deterministic data cleaning pipeline...")
        sales_df, audit = cleaner.clean_transactions(raw_df)

        print(f"Saving sales dataset to {DEFAULT_SALES_FILE}...")
        sales_df.to_csv(DEFAULT_SALES_FILE, index=False)
        print(f"  [OK] Saved {DEFAULT_SALES_FILE.name} ({len(sales_df):,} rows)")

    # Derive customers, products, and targets
    print("Deriving customers, products, and management targets tables...")
    customers_df, products_df, targets_df = cleaner.create_derived_tables(sales_df)

    print(f"Saving derived tables to {PROCESSED_DATA_DIR}...")
    customers_df.to_csv(DEFAULT_CUSTOMERS_FILE, index=False)
    print(f"  [OK] Saved {DEFAULT_CUSTOMERS_FILE.name} ({len(customers_df):,} rows)")

    products_df.to_csv(DEFAULT_PRODUCTS_FILE, index=False)
    print(f"  [OK] Saved {DEFAULT_PRODUCTS_FILE.name} ({len(products_df):,} rows)")

    targets_df.to_csv(DEFAULT_TARGETS_FILE, index=False)
    print(f"  [OK] Saved {DEFAULT_TARGETS_FILE.name} ({len(targets_df):,} rows)")

    duration = time.time() - start_time
    total_rev = float(sales_df["revenue"].sum())

    print("\n--------------------------------------------------")
    print("           DATA PREPARATION SUMMARY               ")
    print("--------------------------------------------------")
    print(f"Total Cleaned Transactions : {len(sales_df):,}")
    print(f"Total Net Sales Revenue    : GBP {total_rev:,.2f}")
    print(f"Unique Orders              : {sales_df['order_id'].nunique():,}")
    print(f"Unique Customers           : {len(customers_df):,}")
    print(f"Unique Products            : {len(products_df):,}")
    print(f"Active Countries           : {sales_df['country'].nunique()}")
    print(f"Completed in               : {duration:.2f}s")
    print("--------------------------------------------------\n")
    print("[SUCCESS] NovaMart data layer initialized successfully!\n")


if __name__ == "__main__":
    main()

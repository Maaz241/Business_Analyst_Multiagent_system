"""
Dataset Loader and Schema Validator for NovaMart.
Loads processed CSV tables or uploaded business data into memory with caching.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from app.config import (
    DEFAULT_SALES_FILE,
    DEFAULT_CUSTOMERS_FILE,
    DEFAULT_PRODUCTS_FILE,
    DEFAULT_TARGETS_FILE,
    PROCESSED_DATA_DIR,
)
from app.data.cleaner import DataCleaningPipeline
from app.utils.logging import logger

_GLOBAL_DATA_CACHE: Dict[str, pd.DataFrame] = {}


class DataLoader:
    """Loads and provides access to NovaMart structured datasets."""

    def __init__(self, processed_dir: Optional[Path] = None):
        self.processed_dir = processed_dir or PROCESSED_DATA_DIR
        self.sales_path = self.processed_dir / "sales.csv"
        self.customers_path = self.processed_dir / "customers.csv"
        self.products_path = self.processed_dir / "products.csv"
        self.targets_path = self.processed_dir / "targets.csv"

    def has_processed_data(self) -> bool:
        """Check if all standard processed files exist."""
        has_sales = self.sales_path.exists() or (self.processed_dir / "sales.csv.gz").exists()
        return (
            has_sales
            and self.customers_path.exists()
            and self.products_path.exists()
        )

    def load_sales(self, force_reload: bool = False) -> pd.DataFrame:
        """Load sales transaction DataFrame with date parsing (supports .csv or .csv.gz)."""
        cache_key = "sales_df"
        if not force_reload and cache_key in _GLOBAL_DATA_CACHE:
            return _GLOBAL_DATA_CACHE[cache_key]

        target_file = self.sales_path
        if not target_file.exists():
            gz_path = self.processed_dir / "sales.csv.gz"
            if gz_path.exists():
                target_file = gz_path
            else:
                raise FileNotFoundError(
                    f"Sales dataset not found at {self.sales_path} or {gz_path}. Run 'python scripts/prepare_dataset.py' first."
                )

        logger.info("Loading sales dataset from %s", target_file)
        df = pd.read_csv(
            target_file,
            dtype={
                "order_id": str,
                "customer_id": str,
                "product_id": str,
                "country": str,
                "category": str,
            },
            parse_dates=["order_date"],
        )
        _GLOBAL_DATA_CACHE[cache_key] = df
        return df

    def load_customers(self, force_reload: bool = False) -> pd.DataFrame:
        """Load customers summary DataFrame."""
        cache_key = "customers_df"
        if not force_reload and cache_key in _GLOBAL_DATA_CACHE:
            return _GLOBAL_DATA_CACHE[cache_key]

        if not self.customers_path.exists():
            raise FileNotFoundError(f"Customers dataset not found at {self.customers_path}")

        df = pd.read_csv(
            self.customers_path,
            dtype={"customer_id": str, "country": str, "customer_segment": str},
            parse_dates=["first_purchase_date", "last_purchase_date"],
        )
        _GLOBAL_DATA_CACHE[cache_key] = df
        return df

    def load_products(self, force_reload: bool = False) -> pd.DataFrame:
        """Load products summary DataFrame."""
        cache_key = "products_df"
        if not force_reload and cache_key in _GLOBAL_DATA_CACHE:
            return _GLOBAL_DATA_CACHE[cache_key]

        if not self.products_path.exists():
            raise FileNotFoundError(f"Products dataset not found at {self.products_path}")

        df = pd.read_csv(
            self.products_path,
            dtype={"product_id": str, "category": str, "sub_category": str},
        )
        _GLOBAL_DATA_CACHE[cache_key] = df
        return df

    def load_targets(self, force_reload: bool = False) -> pd.DataFrame:
        """Load management targets DataFrame."""
        cache_key = "targets_df"
        if not force_reload and cache_key in _GLOBAL_DATA_CACHE:
            return _GLOBAL_DATA_CACHE[cache_key]

        if not self.targets_path.exists():
            # Return empty if missing
            return pd.DataFrame()

        df = pd.read_csv(self.targets_path)
        _GLOBAL_DATA_CACHE[cache_key] = df
        return df

    def get_dataset_summary(self) -> Dict[str, Any]:
        """Return high-level metadata about loaded datasets for Supervisor planning."""
        sales_df = self.load_sales()
        min_date = sales_df["order_date"].min()
        max_date = sales_df["order_date"].max()

        quarters = sorted(sales_df["year_quarter"].dropna().unique().tolist())
        countries = sorted(sales_df["country"].dropna().unique().tolist())
        categories = sorted(sales_df["category"].dropna().unique().tolist())

        return {
            "total_rows": len(sales_df),
            "date_range": {
                "start": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
                "end": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
            },
            "available_quarters": quarters,
            "total_revenue": round(float(sales_df["revenue"].sum()), 2),
            "total_orders": int(sales_df["order_id"].nunique()),
            "total_customers": int(sales_df["customer_id"].nunique()),
            "total_products": int(sales_df["product_id"].nunique()),
            "countries_count": len(countries),
            "countries_top5": countries[:5],
            "categories": categories,
            "columns": list(sales_df.columns),
        }

    def load_custom_file(self, file_path_or_buffer: Any, filename: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Clean and load user-uploaded CSV or Excel file."""
        logger.info("Loading custom uploaded file: %s", filename)
        if filename.endswith(".csv"):
            raw_df = pd.read_csv(file_path_or_buffer)
        elif filename.endswith((".xlsx", ".xls")):
            raw_df = pd.read_excel(file_path_or_buffer)
        else:
            raise ValueError(f"Unsupported data file type: {filename}")

        cleaner = DataCleaningPipeline()
        cleaned_df, report = cleaner.clean_transactions(raw_df)
        return cleaned_df, report

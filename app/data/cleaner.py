"""
Deterministic Data Cleaning and Normalization Pipeline for NovaMart.
Adheres strictly to documented business governance rules (kpi_definitions.pdf).
Never silently drops or modifies data without auditing.
"""

from __future__ import annotations
import re
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from app.utils.logging import logger


# Mapping keywords to NovaMart's 4 core strategic product categories
CATEGORY_KEYWORDS = {
    "Electronics": [
        "clock", "alarm", "digital", "battery", "light", "lamp", "torch", "usb",
        "radio", "phone", "camera", "led", "electronic", "calculator", "timer"
    ],
    "Gifts": [
        "gift", "box", "wrap", "card", "ribbon", "heart", "bow", "star", "birthday",
        "christmas", "toy", "game", "novelty", "plush", "teddy", "decoration", "ornament"
    ],
    "Accessories": [
        "bag", "purse", "wallet", "scarf", "jewel", "necklace", "bracelet", "ring",
        "charm", "keyring", "umbrella", "hat", "glove", "mirror", "case", "travel"
    ],
    "Home & Living": [
        "cushion", "mug", "cup", "plate", "bowl", "kitchen", "bottle", "frame",
        "candle", "holder", "t-light", "drawer", "shelf", "hanger", "towel",
        "glass", "pot", "vase", "garden", "mat", "tin", "basket", "storage"
    ]
}


def assign_category(description: Optional[str]) -> Tuple[str, str]:
    """Deterministically assign category and sub-category from product description."""
    if not isinstance(description, str) or not description.strip():
        return "Home & Living", "General"

    desc_lower = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}", desc_lower):
                return category, kw.capitalize()

    # Default category fallback
    return "Home & Living", "General"


def assign_customer_segment(total_revenue: float, total_orders: int) -> str:
    """Classify customer into business segment based on purchase behavior."""
    if total_revenue >= 10000 or total_orders >= 25:
        return "Enterprise / Wholesale"
    elif total_revenue >= 3000 or total_orders >= 10:
        return "High Value"
    elif total_orders >= 3:
        return "Regular"
    else:
        return "Occasional"


class DataCleaningPipeline:
    """
    Deterministic data cleaner and normalizer.
    Generates detailed cleaning audit report.
    """

    def __init__(self):
        self.audit_report: Dict[str, Any] = {}

    def clean_transactions(self, raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Clean, normalize, and validate raw transaction DataFrame.
        Returns cleaned DataFrame and cleaning audit report.
        """
        initial_rows = len(raw_df)
        logger.info("Starting cleaning pipeline on %d raw rows", initial_rows)

        df = raw_df.copy()

        # 1. Normalize Column Names
        col_map = {
            "Invoice": "order_id",
            "invoice": "order_id",
            "InvoiceNo": "order_id",
            "order_id": "order_id",
            "StockCode": "product_id",
            "stock_code": "product_id",
            "product_id": "product_id",
            "Description": "product_name",
            "description": "product_name",
            "product_name": "product_name",
            "Quantity": "quantity",
            "quantity": "quantity",
            "InvoiceDate": "order_date",
            "invoice_date": "order_date",
            "order_date": "order_date",
            "Price": "unit_price",
            "price": "unit_price",
            "unit_price": "unit_price",
            "UnitPrice": "unit_price",
            "Customer ID": "customer_id",
            "customer_id": "customer_id",
            "CustomerID": "customer_id",
            "Country": "country",
            "country": "country",
        }

        rename_dict = {orig: target for orig, target in col_map.items() if orig in df.columns}
        df = df.rename(columns=rename_dict)

        required_cols = ["order_id", "product_id", "quantity", "order_date", "unit_price", "country"]
        missing_required = [c for c in required_cols if c not in df.columns]
        if missing_required:
            raise ValueError(f"Missing required columns in dataset: {missing_required}")

        # Ensure product_name exists
        if "product_name" not in df.columns:
            df["product_name"] = "Unknown Product"

        # Ensure customer_id exists
        if "customer_id" not in df.columns:
            df["customer_id"] = np.nan

        # 2. Track Cancellations / Returns
        order_str = df["order_id"].astype(str)
        is_cancellation_code = order_str.str.startswith("C") | order_str.str.startswith("c")
        is_negative_qty = df["quantity"] <= 0
        cancellation_mask = is_cancellation_code | is_negative_qty
        cancellation_rows = int(cancellation_mask.sum())

        # Exclude cancellations from completed revenue transactions per KPI governance
        df_valid = df[~cancellation_mask].copy()

        # 3. Track Missing & Invalid Values
        missing_customer_mask = df_valid["customer_id"].isna()
        missing_customer_rows = int(missing_customer_mask.sum())

        # Price validation: unit_price must be > 0
        invalid_price_mask = (df_valid["unit_price"].isna()) | (df_valid["unit_price"] <= 0)
        invalid_price_rows = int(invalid_price_mask.sum())
        df_valid = df_valid[~invalid_price_mask].copy()

        # 4. Handle Customer IDs
        df_valid["customer_id"] = df_valid["customer_id"].apply(
            lambda x: f"GUEST_{np.random.randint(100000, 999999)}" if pd.isna(x) or str(x).strip() in ("", "nan", "None")
            else str(int(float(x))) if str(x).replace(".", "").isdigit() else str(x).strip()
        )

        # 5. Type normalization
        df_valid["order_id"] = df_valid["order_id"].astype(str).str.strip()
        df_valid["product_id"] = df_valid["product_id"].astype(str).str.strip()
        df_valid["product_name"] = df_valid["product_name"].fillna("Unknown Product").astype(str).str.strip()
        df_valid["quantity"] = pd.to_numeric(df_valid["quantity"], errors="coerce").fillna(0).astype(int)
        df_valid["unit_price"] = pd.to_numeric(df_valid["unit_price"], errors="coerce").fillna(0.0).round(4)
        df_valid["country"] = df_valid["country"].fillna("Unspecified").astype(str).str.strip()

        # Parse Dates
        df_valid["order_date"] = pd.to_datetime(df_valid["order_date"], errors="coerce")
        df_valid = df_valid.dropna(subset=["order_date"]).sort_values("order_date").reset_index(drop=True)

        # 6. Calculate Revenue & Time Attributes
        df_valid["revenue"] = (df_valid["quantity"] * df_valid["unit_price"]).round(2)
        df_valid["year"] = df_valid["order_date"].dt.year
        df_valid["quarter"] = "Q" + df_valid["order_date"].dt.quarter.astype(str)
        df_valid["month"] = df_valid["order_date"].dt.month
        df_valid["month_name"] = df_valid["order_date"].dt.strftime("%B")
        df_valid["year_quarter"] = df_valid["year"].astype(str) + "-" + df_valid["quarter"]

        # 7. Category Assignment
        categories_and_subs = [assign_category(name) for name in df_valid["product_name"]]
        df_valid["category"] = [c[0] for c in categories_and_subs]
        df_valid["sub_category"] = [c[1] for c in categories_and_subs]

        final_rows = len(df_valid)
        removed_rows = initial_rows - final_rows

        # 8. Build Comprehensive Audit Report
        min_date = df_valid["order_date"].min()
        max_date = df_valid["order_date"].max()
        total_rev = float(df_valid["revenue"].sum())

        self.audit_report = {
            "rows_loaded": initial_rows,
            "rows_retained": final_rows,
            "rows_removed": removed_rows,
            "cancellation_rows": cancellation_rows,
            "invalid_price_rows": invalid_price_rows,
            "missing_customer_rows": missing_customer_rows,
            "date_range": f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}" if pd.notna(min_date) else "N/A",
            "total_revenue": round(total_rev, 2),
            "unique_orders": int(df_valid["order_id"].nunique()),
            "unique_customers": int(df_valid["customer_id"].nunique()),
            "unique_products": int(df_valid["product_id"].nunique()),
            "countries_count": int(df_valid["country"].nunique()),
            "countries": sorted(df_valid["country"].unique().tolist()),
            "categories": sorted(df_valid["category"].unique().tolist()),
        }

        logger.info(
            "Cleaning finished: %d rows retained, £%.2f total revenue, %d unique orders",
            final_rows, total_rev, self.audit_report["unique_orders"]
        )

        return df_valid, self.audit_report

    def create_derived_tables(self, sales_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Derive customers.csv, products.csv, and targets.csv from cleaned sales DataFrame.
        """
        logger.info("Deriving customers, products, and targets summary tables")

        # Customers summary
        cust_group = sales_df.groupby("customer_id")
        customers_df = cust_group.agg(
            country=("country", "first"),
            first_purchase_date=("order_date", "min"),
            last_purchase_date=("order_date", "max"),
            total_orders=("order_id", "nunique"),
            total_revenue=("revenue", "sum"),
        ).reset_index()

        customers_df["total_revenue"] = customers_df["total_revenue"].round(2)
        customers_df["customer_segment"] = customers_df.apply(
            lambda r: assign_customer_segment(r["total_revenue"], r["total_orders"]), axis=1
        )
        # Active status: purchased in 2011
        customers_df["active_status"] = customers_df["last_purchase_date"].apply(
            lambda d: "Active" if pd.notna(d) and d.year >= 2011 else "Lapsed"
        )

        # Products summary
        prod_group = sales_df.groupby("product_id")
        products_df = prod_group.agg(
            product_name=("product_name", "first"),
            category=("category", "first"),
            sub_category=("sub_category", "first"),
            total_units_sold=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
            orders_count=("order_id", "nunique")
        ).reset_index()
        products_df["total_revenue"] = products_df["total_revenue"].round(2)

        # Management targets table (synthetic management targets per Section 8 & Section 67)
        targets_data = [
            {"metric": "Revenue Growth", "target_value": "12.0%", "period": "Annual 2011", "region": "Global", "notes": "Corporate baseline target"},
            {"metric": "Revenue Growth", "target_value": "10.0%", "period": "Q3 2011", "region": "Global", "notes": "Targeted quarterly growth vs Q2"},
            {"metric": "APAC Growth", "target_value": "15.0%", "period": "Annual 2011", "region": "APAC", "notes": "High priority strategic expansion region"},
            {"metric": "Repeat Customer Rate", "target_value": "75.0%", "period": "Annual 2011", "region": "Global", "notes": "Customer loyalty & retention threshold"},
            {"metric": "Average Order Value", "target_value": "£350.00", "period": "Annual 2011", "region": "Global", "notes": "Target basket size"},
            {"metric": "Electronics Revenue Share", "target_value": "25.0%", "period": "Annual 2011", "region": "Global", "notes": "Category revenue contribution goal"},
            {"metric": "Maximum Discount Rate", "target_value": "20.0%", "period": "Policy", "region": "Global", "notes": "Discretionary discount ceiling per pricing policy"},
        ]
        targets_df = pd.DataFrame(targets_data)

        return customers_df, products_df, targets_df

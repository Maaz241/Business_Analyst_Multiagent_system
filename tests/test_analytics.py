"""
Deterministic Analytics Test Suite for NovaMart.
Validates arithmetic correctness, KPI calculations, and period-over-period comparisons.
"""

import pytest
import pandas as pd
from app.tools.analytics import (
    calculate_total_revenue,
    calculate_order_count,
    calculate_average_order_value,
    compare_periods,
    revenue_by_country,
    revenue_by_category,
    top_products,
    bottom_products,
    customer_metrics,
    detect_anomalies,
)


@pytest.fixture
def sample_sales_df():
    """Create a controlled sample DataFrame for mathematical verification."""
    data = {
        "order_id": ["O1", "O1", "O2", "O3", "O4", "O5"],
        "product_id": ["P1", "P2", "P1", "P3", "P2", "P3"],
        "product_name": ["Digital Clock", "Leather Bag", "Digital Clock", "Ceramic Mug", "Leather Bag", "Ceramic Mug"],
        "quantity": [2, 1, 3, 5, 2, 4],
        "unit_price": [10.0, 50.0, 10.0, 8.0, 50.0, 8.0],
        "revenue": [20.0, 50.0, 30.0, 40.0, 100.0, 32.0],
        "country": ["United Kingdom", "United Kingdom", "Germany", "France", "United Kingdom", "Germany"],
        "customer_id": ["C1", "C1", "C2", "C3", "C1", "C2"],
        "order_date": pd.to_datetime([
            "2011-04-10", "2011-04-10", "2011-05-15",
            "2011-07-20", "2011-08-05", "2011-09-12"
        ]),
        "year": [2011, 2011, 2011, 2011, 2011, 2011],
        "quarter": ["Q2", "Q2", "Q2", "Q3", "Q3", "Q3"],
        "year_quarter": ["2011-Q2", "2011-Q2", "2011-Q2", "2011-Q3", "2011-Q3", "2011-Q3"],
        "category": ["Electronics", "Accessories", "Electronics", "Home & Living", "Accessories", "Home & Living"],
    }
    return pd.DataFrame(data)


def test_revenue_calculation(sample_sales_df):
    """Test total revenue matches exact sum of quantity * unit_price."""
    res_all = calculate_total_revenue(df=sample_sales_df)
    assert res_all["value"] == 272.0
    assert res_all["orders_count"] == 5

    res_q2 = calculate_total_revenue(period="2011-Q2", df=sample_sales_df)
    assert res_q2["value"] == 100.0

    res_q3 = calculate_total_revenue(period="2011-Q3", df=sample_sales_df)
    assert res_q3["value"] == 172.0


def test_growth_calculation(sample_sales_df):
    """Test period-over-period percentage growth calculation."""
    res = compare_periods("2011-Q2", "2011-Q3", df=sample_sales_df)
    # Q2=100, Q3=172 -> Diff = +72 -> Growth = +72.0%
    assert res["base_revenue"] == 100.0
    assert res["target_revenue"] == 172.0
    assert res["revenue_change_abs"] == 72.0
    assert res["revenue_change_pct"] == 72.0
    assert not res["is_decline"]


def test_aov(sample_sales_df):
    """Test Average Order Value (AOV = total_revenue / unique_orders)."""
    res = calculate_average_order_value(period="2011-Q2", df=sample_sales_df)
    # Q2: 2 orders (O1, O2), Total Rev = 100 -> AOV = 50.0
    assert res["value"] == 50.0
    assert res["order_count"] == 2


def test_period_comparison_breakdown(sample_sales_df):
    """Test dimensional breakdown across periods."""
    res = compare_periods("2011-Q2", "2011-Q3", dimension="country", df=sample_sales_df)
    assert "breakdown" in res
    assert len(res["breakdown"]) > 0


def test_country_grouping(sample_sales_df):
    """Test grouping revenue by country."""
    res = revenue_by_country(df=sample_sales_df)
    countries = {c["country"]: c["revenue"] for c in res["countries"]}
    # UK: 20 + 50 + 100 = 170
    assert countries["United Kingdom"] == 170.0
    # Germany: 30 + 32 = 62
    assert countries["Germany"] == 62.0


def test_top_and_bottom_products(sample_sales_df):
    """Test top and bottom product ranking."""
    top = top_products(n=2, df=sample_sales_df)
    assert len(top["products"]) == 2
    # Highest revenue product is Leather Bag (50 + 100 = 150)
    assert top["products"][0]["product_name"] == "Leather Bag"

    bottom = bottom_products(n=2, df=sample_sales_df)
    assert len(bottom["products"]) == 2


def test_customer_metrics(sample_sales_df):
    """Test customer retention and repeat purchase rate."""
    res = customer_metrics(df=sample_sales_df)
    # Customers: C1 (3 orders: O1, O4), C2 (2 orders: O2, O5), C3 (1 order: O3)
    # 2 out of 3 are repeat -> 66.67%
    assert res["active_registered_customers"] == 3
    assert res["repeat_customers_count"] == 2
    assert res["repeat_customer_rate_pct"] == 66.67

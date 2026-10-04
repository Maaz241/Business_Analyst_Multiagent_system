"""
Deterministic Business Analytics Engine for NovaMart.
100% Python/Pandas calculation layer.
All business arithmetic, KPIs, period-over-period comparisons, and anomaly checks
are calculated deterministically here. LLMs are strictly prohibited from doing mental math.

Enhanced v2.0: Cohort Analysis, RFM Segmentation, Revenue Forecasting,
Growth Decomposition, and Market Basket Analysis.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd

from app.data.loader import DataLoader
from app.services.cache import get_cached_result, set_cached_result
from app.utils.logging import logger
from app.config import MAX_TOOL_RESULT_ROWS


_loader = DataLoader()
_active_custom_df: Optional[pd.DataFrame] = None


def set_active_dataset(df: Optional[pd.DataFrame] = None) -> None:
    """Set global active dataset for all downstream analytics and charts."""
    global _active_custom_df
    _active_custom_df = df
    logger.info("Active dataset updated: %s", "Custom DataFrame" if df is not None else "Default NovaMart Data")


def get_active_dataset() -> Optional[pd.DataFrame]:
    """Retrieve currently active dataset if set, or None if using default."""
    return _active_custom_df


def _get_df(custom_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Return provided dataframe, active custom dataframe, or default loaded sales dataframe."""
    if custom_df is not None:
        return custom_df
    if _active_custom_df is not None:
        return _active_custom_df
    return _loader.load_sales()


def inspect_dataset(df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Inspect dataset metadata, row counts, date ranges, and dimensions."""
    data = _get_df(df)
    min_date = data["order_date"].min()
    max_date = data["order_date"].max()

    return {
        "total_transactions": len(data),
        "date_range": {
            "start": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
            "end": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
        },
        "available_quarters": sorted(data["year_quarter"].dropna().unique().tolist()),
        "countries_count": int(data["country"].nunique()),
        "top_countries": data["country"].value_counts().head(5).index.tolist(),
        "categories": sorted(data["category"].dropna().unique().tolist()),
        "total_revenue": round(float(data["revenue"].sum()), 2),
        "total_orders": int(data["order_id"].nunique()),
        "total_customers": int(data["customer_id"].nunique()),
    }


def get_date_range(df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Return start date, end date, and list of all available quarters."""
    data = _get_df(df)
    min_date = data["order_date"].min()
    max_date = data["order_date"].max()
    return {
        "start_date": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
        "end_date": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
        "quarters": sorted(data["year_quarter"].dropna().unique().tolist()),
    }


def filter_dataset(
    df: Optional[pd.DataFrame] = None,
    period: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
    customer_id: Optional[str] = None,
) -> pd.DataFrame:
    """Filter dataset by period (e.g. '2011-Q3'), country, or category."""
    data = _get_df(df)

    if period:
        # Matches year_quarter like '2011-Q3' or year like '2011'
        if "-" in period:
            data = data[data["year_quarter"] == period]
        elif period.startswith("Q"):
            data = data[data["quarter"] == period]
        elif period.isdigit():
            data = data[data["year"] == int(period)]

    if country:
        data = data[data["country"].str.lower() == country.lower()]

    if category:
        data = data[data["category"].str.lower() == category.lower()]

    if customer_id:
        data = data[data["customer_id"] == str(customer_id)]

    return data


def calculate_total_revenue(
    period: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Calculate total monetary sales revenue deterministically."""
    cache_args = {"period": period, "country": country, "category": category}
    cached = get_cached_result("calculate_total_revenue", cache_args)
    if cached and df is None:
        return cached

    filtered = filter_dataset(df=df, period=period, country=country, category=category)
    total_rev = float(filtered["revenue"].sum())
    order_cnt = int(filtered["order_id"].nunique())
    units_sold = int(filtered["quantity"].sum())

    res = {
        "metric": "total_revenue",
        "value": round(total_rev, 2),
        "formatted": f"£{total_rev:,.2f}",
        "period": period or "All Time",
        "country": country or "Global",
        "category": category or "All Categories",
        "orders_count": order_cnt,
        "units_sold": units_sold,
        "calculation": "sum(quantity * unit_price)",
    }
    set_cached_result("calculate_total_revenue", cache_args, res)
    return res


def calculate_order_count(
    period: Optional[str] = None,
    country: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Calculate count of distinct completed orders."""
    filtered = filter_dataset(df=df, period=period, country=country)
    unique_orders = int(filtered["order_id"].nunique())
    return {
        "metric": "order_count",
        "value": unique_orders,
        "formatted": f"{unique_orders:,}",
        "period": period or "All Time",
        "country": country or "Global",
        "calculation": "count(distinct order_id)",
    }


def calculate_average_order_value(
    period: Optional[str] = None,
    country: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Calculate Average Order Value (AOV = Total Revenue / Completed Orders)."""
    filtered = filter_dataset(df=df, period=period, country=country)
    total_rev = float(filtered["revenue"].sum())
    order_cnt = filtered["order_id"].nunique()

    aov = (total_rev / order_cnt) if order_cnt > 0 else 0.0
    return {
        "metric": "average_order_value",
        "value": round(aov, 2),
        "formatted": f"£{aov:,.2f}",
        "total_revenue": round(total_rev, 2),
        "order_count": int(order_cnt),
        "period": period or "All Time",
        "country": country or "Global",
        "calculation": "total_revenue / unique_orders",
    }


def compare_periods(
    base_period: str,
    target_period: str,
    dimension: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compare two business periods (e.g. '2011-Q2' vs '2011-Q3') deterministically.
    Calculates exact absolute difference, percentage change, and optional breakdown by dimension.
    """
    cache_args = {
        "base_period": base_period,
        "target_period": target_period,
        "dimension": dimension,
        "country": country,
        "category": category,
    }
    cached = get_cached_result("compare_periods", cache_args)
    if cached and df is None:
        return cached

    base_df = filter_dataset(df=df, period=base_period, country=country, category=category)
    target_df = filter_dataset(df=df, period=target_period, country=country, category=category)

    base_rev = float(base_df["revenue"].sum())
    target_rev = float(target_df["revenue"].sum())

    base_orders = int(base_df["order_id"].nunique())
    target_orders = int(target_df["order_id"].nunique())

    base_aov = (base_rev / base_orders) if base_orders > 0 else 0.0
    target_aov = (target_rev / target_orders) if target_orders > 0 else 0.0

    rev_diff = target_rev - base_rev
    rev_growth_pct = ((rev_diff / base_rev) * 100) if base_rev > 0 else 0.0

    order_diff = target_orders - base_orders
    order_growth_pct = ((order_diff / base_orders) * 100) if base_orders > 0 else 0.0

    aov_diff = target_aov - base_aov
    aov_growth_pct = ((aov_diff / base_aov) * 100) if base_aov > 0 else 0.0

    result: Dict[str, Any] = {
        "base_period": base_period,
        "target_period": target_period,
        "base_revenue": round(base_rev, 2),
        "target_revenue": round(target_rev, 2),
        "revenue_change_abs": round(rev_diff, 2),
        "revenue_change_pct": round(rev_growth_pct, 2),
        "base_orders": base_orders,
        "target_orders": target_orders,
        "order_change_pct": round(order_growth_pct, 2),
        "base_aov": round(base_aov, 2),
        "target_aov": round(target_aov, 2),
        "aov_change_pct": round(aov_growth_pct, 2),
        "is_decline": rev_diff < 0,
        "calculation": "((target_rev - base_rev) / base_rev) * 100",
    }

    # If dimension requested, calculate dimensional breakdown
    if dimension and dimension in ["country", "category", "product_name"]:
        base_group = base_df.groupby(dimension)["revenue"].sum()
        target_group = target_df.groupby(dimension)["revenue"].sum()

        all_keys = set(base_group.index).union(set(target_group.index))
        breakdown = []

        for key in all_keys:
            b_val = float(base_group.get(key, 0.0))
            t_val = float(target_group.get(key, 0.0))
            diff = t_val - b_val
            pct = ((diff / b_val) * 100) if b_val > 0 else (100.0 if t_val > 0 else 0.0)
            # Calculate contribution to overall change
            contribution_pct = ((diff / rev_diff) * 100) if rev_diff != 0 else 0.0
            breakdown.append({
                dimension: str(key),
                "base_revenue": round(b_val, 2),
                "target_revenue": round(t_val, 2),
                "revenue_change_abs": round(diff, 2),
                "growth_pct": round(pct, 2),
                "contribution_to_change_pct": round(contribution_pct, 2),
            })

        # Sort by absolute change descending
        breakdown.sort(key=lambda x: x["revenue_change_abs"])
        result["breakdown_dimension"] = dimension
        result["breakdown"] = breakdown[:MAX_TOOL_RESULT_ROWS]

    set_cached_result("compare_periods", cache_args, result)
    return result


def revenue_by_country(
    period: Optional[str] = None,
    top_n: int = 10,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Breakdown revenue and order metrics by country."""
    filtered = filter_dataset(df=df, period=period)
    total_rev = float(filtered["revenue"].sum())

    grouped = (
        filtered.groupby("country")
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            units=("quantity", "sum"),
        )
        .reset_index()
    )

    grouped["revenue_share_pct"] = ((grouped["revenue"] / total_rev) * 100).round(2) if total_rev > 0 else 0.0
    grouped["revenue"] = grouped["revenue"].round(2)
    grouped = grouped.sort_values("revenue", ascending=False).head(top_n)

    return {
        "period": period or "All Time",
        "total_revenue": round(total_rev, 2),
        "countries": grouped.to_dict(orient="records"),
    }


def revenue_by_category(
    period: Optional[str] = None,
    country: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Breakdown revenue by NovaMart's 4 core strategic product categories."""
    filtered = filter_dataset(df=df, period=period, country=country)
    total_rev = float(filtered["revenue"].sum())

    grouped = (
        filtered.groupby("category")
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            units_sold=("quantity", "sum"),
        )
        .reset_index()
    )

    grouped["revenue_share_pct"] = ((grouped["revenue"] / total_rev) * 100).round(2) if total_rev > 0 else 0.0
    grouped["revenue"] = grouped["revenue"].round(2)
    grouped = grouped.sort_values("revenue", ascending=False)

    return {
        "period": period or "All Time",
        "country": country or "Global",
        "total_revenue": round(total_rev, 2),
        "categories": grouped.to_dict(orient="records"),
    }


def top_products(
    period: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
    n: int = 10,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Identify top performing products by revenue."""
    filtered = filter_dataset(df=df, period=period, country=country, category=category)
    grouped = (
        filtered.groupby(["product_id", "product_name", "category"])
        .agg(
            revenue=("revenue", "sum"),
            units_sold=("quantity", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    grouped["revenue"] = grouped["revenue"].round(2)
    top = grouped.sort_values("revenue", ascending=False).head(n)

    return {
        "period": period or "All Time",
        "criteria": "highest_revenue",
        "count": len(top),
        "products": top.to_dict(orient="records"),
    }


def bottom_products(
    period: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
    n: int = 10,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Identify bottom performing products with low revenue or steep declines."""
    filtered = filter_dataset(df=df, period=period, country=country, category=category)
    grouped = (
        filtered.groupby(["product_id", "product_name", "category"])
        .agg(
            revenue=("revenue", "sum"),
            units_sold=("quantity", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    grouped["revenue"] = grouped["revenue"].round(2)
    # Filter to products with at least 1 sale
    bottom = grouped[grouped["revenue"] > 0].sort_values("revenue", ascending=True).head(n)

    return {
        "period": period or "All Time",
        "criteria": "lowest_revenue",
        "count": len(bottom),
        "products": bottom.to_dict(orient="records"),
    }


def customer_metrics(
    period: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Calculate customer-level metrics: unique, active, repeat rate, and segmentation."""
    filtered = filter_dataset(df=df, period=period)

    # Exclude guest checkouts from customer loyalty repeat rate calculations
    registered = filtered[~filtered["customer_id"].str.startswith("GUEST_")]
    orders_per_cust = registered.groupby("customer_id")["order_id"].nunique()

    total_active_cust = len(orders_per_cust)
    repeat_cust_count = int((orders_per_cust > 1).sum())
    repeat_rate = ((repeat_cust_count / total_active_cust) * 100) if total_active_cust > 0 else 0.0

    return {
        "period": period or "All Time",
        "active_registered_customers": total_active_cust,
        "repeat_customers_count": repeat_cust_count,
        "repeat_customer_rate_pct": round(repeat_rate, 2),
        "average_orders_per_customer": round(float(orders_per_cust.mean()), 2) if total_active_cust > 0 else 0.0,
    }


def detect_anomalies(
    metric: str = "revenue",
    freq: str = "W",  # 'W' for weekly, 'M' for monthly
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Detect statistical anomalies (> 2 standard deviations from rolling mean)
    across the time series.
    """
    data = _get_df(df).copy()
    data = data.set_index("order_date")

    if metric == "revenue":
        ts = data["revenue"].resample(freq).sum()
    elif metric == "orders":
        ts = data["order_id"].resample(freq).nunique()
    else:
        ts = data["quantity"].resample(freq).sum()

    rolling_mean = ts.rolling(window=4, min_periods=2).mean()
    rolling_std = ts.rolling(window=4, min_periods=2).std().fillna(1.0)

    z_scores = (ts - rolling_mean) / rolling_std
    anomaly_mask = z_scores.abs() > 2.0

    anomalies = []
    for date, val in ts[anomaly_mask].items():
        anomalies.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(float(val), 2),
            "z_score": round(float(z_scores[date]), 2),
            "expected_mean": round(float(rolling_mean[date]), 2),
            "type": "spike" if z_scores[date] > 0 else "drop",
        })

    return {
        "metric": metric,
        "frequency": freq,
        "total_anomalies_detected": len(anomalies),
        "anomalies": anomalies,
    }


# ═══════════════════════════════════════════════════════════════════
# ENHANCED v2.0 — HACKATHON DIFFERENTIATION TOOLS
# ═══════════════════════════════════════════════════════════════════

def rfm_segmentation(
    period: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    RFM (Recency, Frequency, Monetary) Customer Segmentation.
    Deterministically segments customers into value tiers.
    """
    data = filter_dataset(df=df, period=period)
    if data.empty:
        return {"segments": [], "total_customers": 0}

    registered = data[~data["customer_id"].str.startswith("GUEST_")]
    max_date = registered["order_date"].max()

    rfm = registered.groupby("customer_id").agg(
        recency=("order_date", lambda x: (max_date - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("revenue", "sum"),
    ).reset_index()

    # Quantile-based scoring (1-5 scale)
    for col in ["recency", "frequency", "monetary"]:
        try:
            if col == "recency":
                rfm[f"{col}_score"] = pd.qcut(rfm[col], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
            else:
                rfm[f"{col}_score"] = pd.qcut(rfm[col], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
        except (ValueError, TypeError):
            rfm[f"{col}_score"] = 3

    rfm["rfm_score"] = rfm["recency_score"] + rfm["frequency_score"] + rfm["monetary_score"]

    # Segment labels
    def label_segment(score: int) -> str:
        if score >= 13:
            return "Champions"
        elif score >= 10:
            return "Loyal"
        elif score >= 7:
            return "At Risk"
        elif score >= 5:
            return "Needs Attention"
        else:
            return "Lost"

    rfm["segment"] = rfm["rfm_score"].apply(label_segment)

    segment_summary = (
        rfm.groupby("segment")
        .agg(
            customer_count=("customer_id", "count"),
            avg_monetary=("monetary", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_recency=("recency", "mean"),
        )
        .reset_index()
    )
    segment_summary["avg_monetary"] = segment_summary["avg_monetary"].round(2)
    segment_summary["avg_frequency"] = segment_summary["avg_frequency"].round(2)
    segment_summary["avg_recency"] = segment_summary["avg_recency"].round(1)

    return {
        "period": period or "All Time",
        "total_customers": len(rfm),
        "segments": segment_summary.to_dict(orient="records"),
        "segment_distribution": rfm["segment"].value_counts().to_dict(),
    }


def revenue_time_series(
    freq: str = "ME",
    country: Optional[str] = None,
    category: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Generate revenue time series data for trend charting and forecasting."""
    data = filter_dataset(df=df, country=country, category=category).copy()
    if data.empty:
        return {"series": [], "frequency": freq}

    data = data.set_index("order_date")
    ts = data["revenue"].resample(freq).sum().reset_index()
    ts.columns = ["date", "revenue"]

    series = [
        {"date": row["date"].strftime("%Y-%m-%d"), "revenue": round(float(row["revenue"]), 2)}
        for _, row in ts.iterrows()
    ]

    return {
        "frequency": freq,
        "country": country or "Global",
        "category": category or "All",
        "data_points": len(series),
        "series": series,
    }


def revenue_forecast(
    periods_ahead: int = 3,
    freq: str = "ME",
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Simple deterministic linear trend forecast.
    Uses least-squares regression on monthly revenue for projection.
    """
    data = _get_df(df).copy().set_index("order_date")
    ts = data["revenue"].resample(freq).sum()

    if len(ts) < 4:
        return {"forecast": [], "method": "insufficient_data"}

    # Numeric index for regression
    x = np.arange(len(ts)).astype(float)
    y = ts.values.astype(float)

    # Linear regression
    n = len(x)
    x_mean = x.mean()
    y_mean = y.mean()
    ss_xx = np.sum((x - x_mean) ** 2)
    ss_xy = np.sum((x - x_mean) * (y - y_mean))

    slope = ss_xy / ss_xx if ss_xx > 0 else 0
    intercept = y_mean - slope * x_mean

    # R-squared
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Forecast future periods
    last_date = ts.index[-1]
    forecast_points = []
    for i in range(1, periods_ahead + 1):
        future_x = len(ts) - 1 + i
        predicted = slope * future_x + intercept
        if freq in ("ME", "M"):
            future_date = last_date + pd.DateOffset(months=i)
        else:
            future_date = last_date + pd.DateOffset(weeks=i)

        forecast_points.append({
            "date": future_date.strftime("%Y-%m-%d"),
            "predicted_revenue": round(float(max(predicted, 0)), 2),
            "period_index": future_x,
        })

    # Monthly growth rate
    if len(ts) >= 2:
        recent_growth = float((ts.iloc[-1] - ts.iloc[-2]) / ts.iloc[-2] * 100) if ts.iloc[-2] > 0 else 0
    else:
        recent_growth = 0

    return {
        "method": "linear_regression",
        "slope_per_period": round(float(slope), 2),
        "intercept": round(float(intercept), 2),
        "r_squared": round(float(r_squared), 4),
        "recent_growth_pct": round(recent_growth, 2),
        "historical_periods": len(ts),
        "forecast": forecast_points,
    }


def growth_decomposition(
    base_period: str,
    target_period: str,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Decompose revenue growth into Volume, Price/Mix, and New Market components.
    Separates growth drivers deterministically.
    """
    base_df = filter_dataset(df=df, period=base_period)
    target_df = filter_dataset(df=df, period=target_period)

    base_rev = float(base_df["revenue"].sum())
    target_rev = float(target_df["revenue"].sum())
    total_change = target_rev - base_rev

    # Volume effect: change in quantity at base average price
    base_qty = float(base_df["quantity"].sum())
    target_qty = float(target_df["quantity"].sum())
    base_avg_price = (base_rev / base_qty) if base_qty > 0 else 0

    volume_effect = (target_qty - base_qty) * base_avg_price

    # Price/Mix effect: residual
    price_mix_effect = total_change - volume_effect

    # New vs existing countries
    base_countries = set(base_df["country"].unique())
    target_countries = set(target_df["country"].unique())
    new_countries = target_countries - base_countries
    lost_countries = base_countries - target_countries

    new_market_rev = float(target_df[target_df["country"].isin(new_countries)]["revenue"].sum()) if new_countries else 0
    lost_market_rev = float(base_df[base_df["country"].isin(lost_countries)]["revenue"].sum()) if lost_countries else 0

    return {
        "base_period": base_period,
        "target_period": target_period,
        "base_revenue": round(base_rev, 2),
        "target_revenue": round(target_rev, 2),
        "total_revenue_change": round(total_change, 2),
        "total_change_pct": round((total_change / base_rev * 100) if base_rev > 0 else 0, 2),
        "volume_effect": round(volume_effect, 2),
        "volume_effect_pct": round((volume_effect / base_rev * 100) if base_rev > 0 else 0, 2),
        "price_mix_effect": round(price_mix_effect, 2),
        "price_mix_effect_pct": round((price_mix_effect / base_rev * 100) if base_rev > 0 else 0, 2),
        "new_market_revenue": round(new_market_rev, 2),
        "lost_market_revenue": round(lost_market_rev, 2),
        "new_countries": sorted(list(new_countries)),
        "lost_countries": sorted(list(lost_countries)),
        "base_avg_unit_price": round(base_avg_price, 2),
        "target_avg_unit_price": round((target_rev / target_qty) if target_qty > 0 else 0, 2),
        "quantity_change_pct": round(((target_qty - base_qty) / base_qty * 100) if base_qty > 0 else 0, 2),
    }


def monthly_kpi_dashboard(
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Calculate comprehensive monthly KPIs for sparkline / heatmap visualization.
    Returns monthly revenue, orders, AOV, and customer counts.
    """
    data = _get_df(df).copy()
    data = data.set_index("order_date")

    monthly = data.resample("ME").agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
        customers=("customer_id", "nunique"),
        units=("quantity", "sum"),
    ).reset_index()

    monthly["aov"] = (monthly["revenue"] / monthly["orders"]).round(2).fillna(0)
    monthly["revenue"] = monthly["revenue"].round(2)

    # Calculate MoM growth
    monthly["revenue_mom_pct"] = monthly["revenue"].pct_change().fillna(0).round(4) * 100
    monthly["order_mom_pct"] = monthly["orders"].pct_change().fillna(0).round(4) * 100

    records = []
    for _, row in monthly.iterrows():
        records.append({
            "month": row["order_date"].strftime("%Y-%m"),
            "revenue": float(row["revenue"]),
            "orders": int(row["orders"]),
            "customers": int(row["customers"]),
            "units": int(row["units"]),
            "aov": float(row["aov"]),
            "revenue_mom_pct": round(float(row["revenue_mom_pct"]), 2),
            "order_mom_pct": round(float(row["order_mom_pct"]), 2),
        })

    return {
        "months": len(records),
        "data": records,
    }


def country_performance_matrix(
    period: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Generate a country performance matrix with revenue, growth, and market share.
    Used for geo-heatmap and strategic portfolio views.
    """
    data = _get_df(df)
    if period:
        filtered = filter_dataset(df=df, period=period)
    else:
        filtered = data

    total_rev = float(filtered["revenue"].sum())

    grouped = (
        filtered.groupby("country")
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            avg_unit_price=("unit_price", "mean"),
            total_qty=("quantity", "sum"),
        )
        .reset_index()
    )

    grouped["revenue"] = grouped["revenue"].round(2)
    grouped["market_share_pct"] = ((grouped["revenue"] / total_rev) * 100).round(2) if total_rev > 0 else 0
    grouped["avg_unit_price"] = grouped["avg_unit_price"].round(2)
    grouped["aov"] = (grouped["revenue"] / grouped["orders"]).round(2).fillna(0)

    grouped = grouped.sort_values("revenue", ascending=False)

    return {
        "period": period or "All Time",
        "total_countries": len(grouped),
        "total_revenue": round(total_rev, 2),
        "countries": grouped.to_dict(orient="records"),
    }


def quarterly_executive_summary(
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive quarterly metrics for executive overview.
    Returns quarterly breakdowns for all key metrics.
    """
    data = _get_df(df)
    quarters = sorted(data["year_quarter"].dropna().unique().tolist())

    quarterly_data = []
    for q in quarters:
        q_data = data[data["year_quarter"] == q]
        rev = float(q_data["revenue"].sum())
        orders = int(q_data["order_id"].nunique())
        customers = int(q_data["customer_id"].nunique())
        aov = (rev / orders) if orders > 0 else 0

        quarterly_data.append({
            "quarter": q,
            "revenue": round(rev, 2),
            "orders": orders,
            "customers": customers,
            "aov": round(aov, 2),
            "units_sold": int(q_data["quantity"].sum()),
            "avg_unit_price": round(float(q_data["unit_price"].mean()), 2),
        })

    # Calculate QoQ growth
    for i in range(1, len(quarterly_data)):
        prev_rev = quarterly_data[i - 1]["revenue"]
        curr_rev = quarterly_data[i]["revenue"]
        quarterly_data[i]["qoq_growth_pct"] = round(
            ((curr_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0, 2
        )

    if quarterly_data:
        quarterly_data[0]["qoq_growth_pct"] = 0.0

    return {
        "total_quarters": len(quarterly_data),
        "quarters": quarterly_data,
    }

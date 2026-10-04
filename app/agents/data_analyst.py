"""
Data Analyst Agent  (v2.1 – fully defensive dict access).
Executes deterministic Pandas analytical tools on NovaMart structured data.
Computes KPIs, compares periods, identifies trends and anomalies dynamically.
Never guesses or estimates numbers.  All dict lookups use .get() with defaults.
"""

from __future__ import annotations
import re
import time
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from app.tools.analytics import (
    inspect_dataset,
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
    rfm_segmentation,
)
from app.utils.logging import log_agent_step, logger
from app.utils.formatting import format_currency, format_percent


def _detect_periods(question: str, available_quarters: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Detect target_period and base_period from question, matched against dataset quarters."""
    q_clean = question.upper()

    # 1. Match full quarters like 2011-Q3, 2022-Q4, 2011Q3, Q3 2011, Q3-2011
    matches = re.findall(r"\b(20\d\d)[- ]?Q([1-4])\b|\bQ([1-4])[- ]?(20\d\d)\b", q_clean)
    found_quarters = []
    for m in matches:
        if m[0] and m[1]:
            found_quarters.append(f"{m[0]}-Q{m[1]}")
        elif m[2] and m[3]:
            found_quarters.append(f"{m[3]}-Q{m[2]}")

    # 2. Check if just Q1/Q2/Q3/Q4 is mentioned without year
    if not found_quarters:
        q_matches = re.findall(r"\bQ([1-4])\b", q_clean)
        for qm in q_matches:
            matching = [aq for aq in available_quarters if aq.endswith(f"-Q{qm}")]
            if matching:
                found_quarters.append(matching[-1])

    # 3. Check if just a 4-digit year is mentioned (e.g. 2022, 2011)
    if not found_quarters:
        y_matches = re.findall(r"\b(20\d\d)\b", q_clean)
        for ym in y_matches:
            matching = [aq for aq in available_quarters if aq.startswith(f"{ym}-")]
            if matching:
                found_quarters.append(matching[-1])

    target_period = None
    base_period = None

    if found_quarters and found_quarters[0] in available_quarters:
        target_period = found_quarters[0]
        idx = available_quarters.index(target_period)
        if idx > 0:
            base_period = available_quarters[idx - 1]
    elif available_quarters:
        target_period = available_quarters[-1]
        if len(available_quarters) >= 2:
            base_period = available_quarters[-2]

    return target_period, base_period


class DataAnalystAgent:
    """Specialist agent responsible for deterministic quantitative business analysis."""

    def __init__(self, sales_df: Optional[pd.DataFrame] = None):
        self.sales_df = sales_df

    def run(self, question: str, plan_tasks: List[Dict[str, Any]], iteration: int = 0) -> Dict[str, Any]:
        """
        Execute deterministic analytics corresponding to the plan.
        Returns findings, tool results, metrics, and evidence units.
        """
        start_time = time.perf_counter()
        tool_results: List[Dict[str, Any]] = []
        findings: List[Dict[str, Any]] = []
        evidence_list: List[Dict[str, Any]] = []
        charts_recommended: List[str] = ["revenue_trend"]

        q_lower = question.lower()

        try:
          with log_agent_step("DataAnalyst", "Execute quantitative analysis", iteration=iteration):
            # 1. Dataset overview & dynamic period identification
            dataset_meta = inspect_dataset(self.sales_df)
            available_quarters = dataset_meta.get("available_quarters", [])
            target_period, base_period = _detect_periods(question, available_quarters)

            source_label = "active_transactions"

            # 2. Period-over-period comparison if trend, comparison, decline, or growth is requested
            needs_comparison = any(
                term in q_lower
                for term in ["decline", "fall", "drop", "growth", "change", "quarter", "compare", "performance", "expansion", "why"]
            )

            if needs_comparison and base_period and target_period and base_period != target_period:
                # Compare by Country
                comp_geo = compare_periods(base_period, target_period, dimension="country", df=self.sales_df)
                tool_results.append({
                    "tool": "compare_periods_country",
                    "params": {"base": base_period, "target": target_period, "dimension": "country"},
                    "output": comp_geo,
                })

                # Compare by Category
                comp_cat = compare_periods(base_period, target_period, dimension="category", df=self.sales_df)
                tool_results.append({
                    "tool": "compare_periods_category",
                    "params": {"base": base_period, "target": target_period, "dimension": "category"},
                    "output": comp_cat,
                })

                charts_recommended.extend(["period_comparison", "growth_waterfall"])

                # Primary period change finding
                ev_id_1 = f"EV-CALC-{len(evidence_list)+1:02d}"
                chg_abs = comp_geo.get("revenue_change_abs", 0.0)
                chg_pct = comp_geo.get("revenue_change_pct", 0.0)
                direction = "decline" if chg_abs < 0 else "growth"

                base_r = comp_geo.get("base_revenue", 0.0)
                targ_r = comp_geo.get("target_revenue", 0.0)

                evidence_list.append({
                    "id": ev_id_1,
                    "source": source_label,
                    "source_type": "data_calculation",
                    "details": (
                        f"{base_period} Revenue: {format_currency(base_r)}, "
                        f"{target_period} Revenue: {format_currency(targ_r)}, "
                        f"Absolute Change: {format_currency(chg_abs)}, "
                        f"Growth: {format_percent(chg_pct)}"
                    ),
                    "calculation": f"compare_periods('{base_period}', '{target_period}')",
                })

                findings.append({
                    "title": f"Period Revenue Shift ({base_period} to {target_period})",
                    "statement": (
                        f"Total revenue moved from {format_currency(base_r)} in {base_period} "
                        f"to {format_currency(targ_r)} in {target_period}, representing a "
                        f"{direction} of {format_percent(chg_pct)} ({format_currency(chg_abs)})."
                    ),
                    "metric": f"{target_period} Revenue Change",
                    "value": format_percent(chg_pct),
                    "evidence_ids": [ev_id_1],
                    "confidence": "High",
                    "classification": "fact",
                })

                # Dimensional Geo Breakdown
                geo_breakdown = comp_geo.get("breakdown", [])
                if geo_breakdown:
                    worst_countries = [c for c in geo_breakdown if c.get("revenue_change_abs", 0) < 0][:3]
                    best_countries = [c for c in geo_breakdown if c.get("revenue_change_abs", 0) > 0][:3]
                    notable_countries = worst_countries if "decline" in q_lower or not best_countries else best_countries

                    for c in notable_countries:
                        ev_id_c = f"EV-CALC-{len(evidence_list)+1:02d}"
                        c_name = c.get("country", "Unknown")
                        c_base = c.get("base_revenue", 0.0)
                        c_targ = c.get("target_revenue", 0.0)
                        c_growth = c.get("growth_pct", 0.0)
                        c_chg = c.get("revenue_change_abs", 0.0)

                        evidence_list.append({
                            "id": ev_id_c,
                            "source": source_label,
                            "source_type": "data_calculation",
                            "details": (
                                f"Country: {c_name}, {base_period}: {format_currency(c_base)}, "
                                f"{target_period}: {format_currency(c_targ)}, Growth: {format_percent(c_growth)}"
                            ),
                            "calculation": f"compare_periods(dimension='country', {base_period}, {target_period})",
                        })
                        c_dir = "contracted" if c_growth < 0 else "expanded"
                        findings.append({
                            "title": f"Regional Shift: {c_name}",
                            "statement": (
                                f"Revenue in {c_name} {c_dir} by {format_percent(c_growth)} "
                                f"({format_currency(c_chg)}) during {target_period}."
                            ),
                            "metric": f"{c_name} Growth",
                            "value": format_percent(c_growth),
                            "evidence_ids": [ev_id_c],
                            "confidence": "High",
                            "classification": "fact",
                        })

                # Dimensional Category Breakdown
                cat_breakdown = comp_cat.get("breakdown", [])
                if cat_breakdown:
                    notable_cats = sorted(cat_breakdown, key=lambda x: abs(x.get("revenue_change_abs", 0)), reverse=True)[:2]
                    for cat in notable_cats:
                        ev_id_cat = f"EV-CALC-{len(evidence_list)+1:02d}"
                        cat_name = cat.get("category", "General")
                        cat_base = cat.get("base_revenue", 0.0)
                        cat_targ = cat.get("target_revenue", 0.0)
                        cat_growth = cat.get("growth_pct", 0.0)

                        evidence_list.append({
                            "id": ev_id_cat,
                            "source": source_label,
                            "source_type": "data_calculation",
                            "details": (
                                f"Category: {cat_name}, {base_period}: {format_currency(cat_base)}, "
                                f"{target_period}: {format_currency(cat_targ)}, Growth: {format_percent(cat_growth)}"
                            ),
                            "calculation": f"compare_periods(dimension='category', {base_period}, {target_period})",
                        })
                        cat_dir = "decline" if cat_growth < 0 else "growth"
                        findings.append({
                            "title": f"Category Impact: {cat_name}",
                            "statement": (
                                f"The {cat_name} category recorded a {cat_dir} of {format_percent(cat_growth)} "
                                f"in {target_period} relative to {base_period}."
                            ),
                            "metric": f"{cat_name} Growth",
                            "value": format_percent(cat_growth),
                            "evidence_ids": [ev_id_cat],
                            "confidence": "High",
                            "classification": "fact",
                        })

            # 3. Primary Period Operational Metrics
            q_rev = calculate_total_revenue(period=target_period, df=self.sales_df)
            q_orders = calculate_order_count(period=target_period, df=self.sales_df)
            q_aov = calculate_average_order_value(period=target_period, df=self.sales_df)
            q_cust = customer_metrics(period=target_period, df=self.sales_df)

            tool_results.append({"tool": "calculate_total_revenue", "output": q_rev})
            tool_results.append({"tool": "calculate_average_order_value", "output": q_aov})
            tool_results.append({"tool": "customer_metrics", "output": q_cust})
            charts_recommended.extend(["revenue_by_country", "revenue_by_category"])

            # Ensure country-level findings exist even if single-period or no comparison
            has_geo_finding = any("Regional Shift" in f["title"] or "Territory" in f["title"] for f in findings)
            if not has_geo_finding:
                geo_data = revenue_by_country(period=target_period, df=self.sales_df)
                tool_results.append({"tool": "revenue_by_country", "output": geo_data})
                top_countries = geo_data.get("countries", [])[:3]
                for c in top_countries:
                    ev_id_geo = f"EV-CALC-{len(evidence_list)+1:02d}"
                    c_country = c.get("country", "Unknown")
                    c_rev = c.get("revenue", 0.0)
                    c_share = c.get("revenue_share_pct", 0.0)
                    evidence_list.append({
                        "id": ev_id_geo,
                        "source": source_label,
                        "source_type": "data_calculation",
                        "details": f"Country: {c_country}, Revenue: {format_currency(c_rev)}, Share: {c_share}%",
                        "calculation": f"revenue_by_country(period='{target_period}')",
                    })
                    cnt = int(c.get("orders", c.get("order_count", 0)) or 0)
                    findings.append({
                        "title": f"Territory Distribution: {c_country}",
                        "statement": (
                            f"{c_country} generated {format_currency(c_rev)} ({c_share}% of total revenue) "
                            f"across {cnt:,} orders in {target_period or 'the active reporting period'}."
                        ),
                        "metric": f"{c_country} Share",
                        "value": f"{c_share}%",
                        "evidence_ids": [ev_id_geo],
                        "confidence": "High",
                        "classification": "fact",
                    })

            # 4. Product Level Analysis
            if any(term in q_lower for term in ["product", "sku", "item", "category", "best", "worst", "top", "bottom"]):
                top_p = top_products(period=target_period, n=5, df=self.sales_df)
                bot_p = bottom_products(period=target_period, n=5, df=self.sales_df)
                tool_results.append({"tool": "top_products", "output": top_p})
                tool_results.append({"tool": "bottom_products", "output": bot_p})

                top_list = top_p.get("products", [])
                for idx, prod in enumerate(top_list[:3]):
                    ev_p = f"EV-CALC-{len(evidence_list)+1:02d}"
                    p_name = prod.get("product_name", "Unknown SKU")
                    p_rev = prod.get("revenue", 0.0)
                    p_units = int(prod.get("units_sold", 0) or 0)
                    p_cat = prod.get("category", "General")
                    evidence_list.append({
                        "id": ev_p,
                        "source": source_label,
                        "source_type": "data_calculation",
                        "details": f"Rank #{idx+1}: {p_name} ({p_cat}), Revenue: {format_currency(p_rev)}, Units: {p_units:,}",
                        "calculation": f"top_products(period='{target_period}')",
                    })
                    findings.append({
                        "title": f"Top SKU #{idx+1}: {p_name[:35]}",
                        "statement": (
                            f"Product '{p_name}' in category {p_cat} was a top revenue driver, contributing "
                            f"{format_currency(p_rev)} across {p_units:,} units in {target_period or 'the reporting period'}."
                        ),
                        "metric": f"SKU #{idx+1} Revenue",
                        "value": format_currency(p_rev),
                        "evidence_ids": [ev_p],
                        "confidence": "High",
                        "classification": "fact",
                    })

                # Also calculate category breakdown
                cat_data = revenue_by_category(period=target_period, df=self.sales_df)
                tool_results.append({"tool": "revenue_by_category", "output": cat_data})
                for c_item in cat_data.get("categories", [])[:3]:
                    ev_c = f"EV-CALC-{len(evidence_list)+1:02d}"
                    c_cat_name = c_item.get("category", "General")
                    c_rev = c_item.get("revenue", 0.0)
                    c_share = c_item.get("revenue_share_pct", 0.0)
                    c_units = int(c_item.get("units_sold", 0) or 0)
                    evidence_list.append({
                        "id": ev_c,
                        "source": source_label,
                        "source_type": "data_calculation",
                        "details": f"Category {c_cat_name}: Revenue {format_currency(c_rev)}, Share {c_share}%",
                        "calculation": f"revenue_by_category(period='{target_period}')",
                    })
                    findings.append({
                        "title": f"Category Share: {c_cat_name}",
                        "statement": (
                            f"The {c_cat_name} category delivered {format_currency(c_rev)} "
                            f"({c_share}% of total revenue) across {c_units:,} units."
                        ),
                        "metric": f"{c_cat_name} Share",
                        "value": f"{c_share}%",
                        "evidence_ids": [ev_c],
                        "confidence": "High",
                        "classification": "fact",
                    })

            # 5. Customer & RFM Analysis
            if any(term in q_lower for term in ["customer", "segment", "churn", "rfm", "repeat"]):
                rfm_res = rfm_segmentation(period=target_period, df=self.sales_df)
                tool_results.append({"tool": "rfm_segmentation", "output": rfm_res})
                charts_recommended.append("rfm_treemap")

                tot_cust = int(q_cust.get("total_customers", q_cust.get("active_registered_customers", 0)) or 0)
                rep_rate = q_cust.get("repeat_customer_rate_pct", 0.0)

                ev_rfm = f"EV-CALC-{len(evidence_list)+1:02d}"
                evidence_list.append({
                    "id": ev_rfm,
                    "source": source_label,
                    "source_type": "data_calculation",
                    "details": f"Repeat Customer Rate: {rep_rate}%, Total Customers: {tot_cust:,}",
                    "calculation": f"customer_metrics(period='{target_period}')",
                })
                findings.append({
                    "title": "Customer Retention & Repeat Dynamics",
                    "statement": (
                        f"Active customer base reached {tot_cust:,} accounts with a repeat purchase rate of "
                        f"{rep_rate}% during {target_period or 'the reporting period'}."
                    ),
                    "metric": "Repeat Purchase Rate",
                    "value": f"{rep_rate}%",
                    "evidence_ids": [ev_rfm],
                    "confidence": "High",
                    "classification": "fact",
                })

            # 6. Statistical Anomalies
            anoms = detect_anomalies(metric="revenue", freq="W", df=self.sales_df)
            tool_results.append({"tool": "detect_anomalies", "output": anoms})
            if anoms.get("total_anomalies_detected", 0) > 0:
                charts_recommended.append("anomalies")

            # 7. Guaranteed Baseline Findings if specific branches yielded 0 findings
            if not findings:
                ev_base = f"EV-CALC-{len(evidence_list)+1:02d}"
                evidence_list.append({
                    "id": ev_base,
                    "source": source_label,
                    "source_type": "data_calculation",
                    "details": f"Period: {target_period or 'All Time'}, Revenue: {q_rev.get('formatted', 'N/A')}, Orders: {q_orders.get('formatted', 'N/A')}, AOV: {q_aov.get('formatted', 'N/A')}",
                    "calculation": f"calculate_total_revenue(period='{target_period}')",
                })
                findings.append({
                    "title": f"Period Revenue Baseline ({target_period or 'All Time'})",
                    "statement": (
                        f"NovaMart recorded {q_rev.get('formatted', 'N/A')} in total revenue across {q_orders.get('formatted', 'N/A')} "
                        f"completed orders with an Average Order Value of {q_aov.get('formatted', 'N/A')} during {target_period or 'the active period'}."
                    ),
                    "metric": "Total Revenue",
                    "value": q_rev.get("formatted", "N/A"),
                    "evidence_ids": [ev_base],
                    "confidence": "High",
                    "classification": "fact",
                })

            duration = time.perf_counter() - start_time
            logger.info("DataAnalyst completed in %.2fs with %d findings", duration, len(findings))

            return {
                "findings": findings,
                "tool_results": tool_results,
                "evidence": evidence_list,
                "charts": list(set(charts_recommended)),
                "summary_metrics": {
                    "period": target_period or "All Time",
                    "revenue": q_rev.get("formatted", "N/A"),
                    "orders": q_orders.get("formatted", "N/A"),
                    "aov": q_aov.get("formatted", "N/A"),
                    "repeat_rate": f"{q_cust.get('repeat_customer_rate_pct', 0)}%",
                },
                "duration": round(duration, 3),
            }

        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.error("DataAnalyst crashed after %.2fs: %s", duration, exc, exc_info=True)
            return {
                "findings": [],
                "tool_results": [],
                "evidence": [],
                "charts": ["revenue_trend"],
                "summary_metrics": {
                    "period": "All Time",
                    "revenue": "N/A",
                    "orders": "N/A",
                    "aov": "N/A",
                    "repeat_rate": "0%",
                },
                "duration": round(duration, 3),
            }

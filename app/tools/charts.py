"""
Premium Plotly Chart Generator for NovaMart AI Business Analyst.
Generates responsive, rich aesthetic visualizations based strictly on deterministic analytics.
Never invents or fabricates data points.

Enhanced v2.0: Geo-heatmaps, RFM Treemaps, Sparkline Grids, Growth Waterfall,
Radar Charts, and Animated Timeline Visuals.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.tools.analytics import (
    filter_dataset,
    revenue_by_country,
    revenue_by_category,
    top_products,
    compare_periods,
    detect_anomalies,
    rfm_segmentation,
    monthly_kpi_dashboard,
    growth_decomposition,
    quarterly_executive_summary,
    country_performance_matrix,
    revenue_forecast,
)

# ═══════════════════════════════════════════════════════════════════
# Premium Dark Theme Configuration
# ═══════════════════════════════════════════════════════════════════

COLORS = {
    "primary": "#6366F1",       # Indigo
    "secondary": "#10B981",     # Emerald
    "accent": "#8B5CF6",        # Violet
    "warning": "#F59E0B",       # Amber
    "danger": "#EF4444",        # Rose
    "info": "#06B6D4",          # Cyan
    "surface": "#1E293B",       # Slate-800
    "surface_alt": "#0F172A",   # Slate-900
    "text": "#F8FAFC",          # Slate-50
    "text_muted": "#94A3B8",    # Slate-400
    "grid": "#334155",          # Slate-700
    "gradient_start": "#6366F1",
    "gradient_end": "#8B5CF6",
}

PALETTE = ["#6366F1", "#10B981", "#8B5CF6", "#F59E0B", "#EF4444", "#06B6D4", "#EC4899", "#14B8A6"]

DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(15, 23, 42, 0)",
    plot_bgcolor="rgba(30, 41, 59, 0.3)",
    font=dict(family="Inter, system-ui, sans-serif", color=COLORS["text"], size=12),
    margin=dict(l=50, r=30, t=60, b=40),
    xaxis=dict(gridcolor=COLORS["grid"], showgrid=True, gridwidth=0.5),
    yaxis=dict(gridcolor=COLORS["grid"], showgrid=True, gridwidth=0.5),
    hovermode="x unified",
    hoverlabel=dict(bgcolor=COLORS["surface"], font_color=COLORS["text"], bordercolor=COLORS["primary"]),
)


def _apply_dark_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply consistent premium dark theme to any figure."""
    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(text=title, font=dict(size=16, color=COLORS["text"]), x=0.02, xanchor="left"),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════
# CORE CHARTS (Enhanced Aesthetics)
# ═══════════════════════════════════════════════════════════════════

def chart_revenue_trend(
    freq: str = "ME",
    period: Optional[str] = None,
    country: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """Premium gradient area chart showing revenue trend with volume bars overlay."""
    data = filter_dataset(df=df, period=period, country=country).copy()
    if data.empty:
        return go.Figure().update_layout(title="No data available for trend chart")

    data = data.set_index("order_date")
    ts = data.resample(freq).agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Order volume bars (background)
    fig.add_trace(
        go.Bar(
            x=ts["order_date"], y=ts["orders"],
            name="Orders",
            marker=dict(color=COLORS["primary"], opacity=0.15),
            hovertemplate="Orders: %{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )

    # Revenue area line
    fig.add_trace(
        go.Scatter(
            x=ts["order_date"], y=ts["revenue"],
            name="Revenue",
            mode="lines+markers",
            line=dict(color=COLORS["primary"], width=3, shape="spline"),
            marker=dict(size=6, color=COLORS["primary"], line=dict(width=2, color=COLORS["surface"])),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.1)",
            hovertemplate="Revenue: £%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    freq_label = "Monthly" if "M" in freq else "Weekly"
    _apply_dark_layout(fig, f"📈 Revenue Trend ({freq_label}) — {country or 'Global'}")
    fig.update_yaxes(title_text="Revenue (£)", tickprefix="£", tickformat=",.0f", secondary_y=False)
    fig.update_yaxes(title_text="Orders", tickformat=",.0f", secondary_y=True, showgrid=False)

    return fig


def chart_revenue_by_country(
    period: Optional[str] = None,
    top_n: int = 10,
    df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """Horizontal gradient bar chart showing revenue by country with market share."""
    res = revenue_by_country(period=period, top_n=top_n, df=df)
    countries_data = res.get("countries", [])
    if not countries_data:
        return go.Figure().update_layout(title="No country data available")

    df_plot = pd.DataFrame(countries_data).sort_values("revenue", ascending=True)

    # Gradient colors based on revenue
    max_rev = df_plot["revenue"].max()
    colors = [
        f"rgba(99, 102, 241, {0.3 + 0.7 * (r / max_rev)})" if max_rev > 0 else COLORS["primary"]
        for r in df_plot["revenue"]
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_plot["revenue"],
        y=df_plot["country"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"£{v:,.0f} ({s:.1f}%)" for v, s in zip(df_plot["revenue"], df_plot["revenue_share_pct"])],
        textposition="outside",
        textfont=dict(color=COLORS["text_muted"], size=11),
        hovertemplate="<b>%{y}</b><br>Revenue: £%{x:,.0f}<extra></extra>",
    ))

    _apply_dark_layout(fig, f"🌍 Top {len(df_plot)} Countries by Revenue ({period or 'All Time'})")
    fig.update_xaxes(tickprefix="£", tickformat=",.0f")
    return fig


def chart_revenue_by_category(
    period: Optional[str] = None,
    country: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """Premium sunburst / donut chart breakdown across categories."""
    res = revenue_by_category(period=period, country=country, df=df)
    categories = res.get("categories", [])
    if not categories:
        return go.Figure().update_layout(title="No category data available")

    df_plot = pd.DataFrame(categories)

    fig = go.Figure(go.Pie(
        labels=df_plot["category"],
        values=df_plot["revenue"],
        hole=0.55,
        marker=dict(colors=PALETTE[:len(df_plot)], line=dict(color=COLORS["surface"], width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color=COLORS["text"]),
        hovertemplate="<b>%{label}</b><br>Revenue: £%{value:,.0f}<br>Share: %{percent}<extra></extra>",
    ))

    # Add center annotation
    total = df_plot["revenue"].sum()
    fig.add_annotation(
        text=f"<b>£{total:,.0f}</b><br><span style='font-size:11px;color:{COLORS['text_muted']}'>Total</span>",
        showarrow=False, font=dict(size=16, color=COLORS["text"]),
    )

    _apply_dark_layout(fig, f"📊 Revenue by Category ({period or 'All Time'})")
    return fig


def chart_period_comparison(
    base_period: str,
    target_period: str,
    dimension: str = "category",
    df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """Grouped bar chart comparing performance across two periods with delta labels."""
    comp = compare_periods(
        base_period=base_period,
        target_period=target_period,
        dimension=dimension,
        df=df,
    )
    breakdown = comp.get("breakdown", [])
    if not breakdown:
        return go.Figure().update_layout(title=f"No comparison data for {base_period} vs {target_period}")

    df_plot = pd.DataFrame(breakdown).sort_values("revenue_change_abs")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=base_period,
        x=df_plot[dimension], y=df_plot["base_revenue"],
        marker=dict(color=COLORS["text_muted"], opacity=0.5),
        hovertemplate=f"{base_period}: £%{{y:,.0f}}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name=target_period,
        x=df_plot[dimension], y=df_plot["target_revenue"],
        marker=dict(color=COLORS["primary"]),
        hovertemplate=f"{target_period}: £%{{y:,.0f}}<extra></extra>",
    ))

    # Add growth % annotations
    for _, row in df_plot.iterrows():
        growth = row["growth_pct"]
        color = COLORS["secondary"] if growth >= 0 else COLORS["danger"]
        arrow = "▲" if growth >= 0 else "▼"
        fig.add_annotation(
            x=row[dimension],
            y=max(row["base_revenue"], row["target_revenue"]),
            text=f"{arrow} {growth:+.1f}%",
            showarrow=False, yshift=15,
            font=dict(size=10, color=color, weight="bold"),
        )

    _apply_dark_layout(fig, f"⚖️ Period Comparison: {base_period} vs {target_period}")
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickprefix="£", tickformat=",.0f")
    return fig


def chart_anomalies(metric: str = "revenue", df: Optional[pd.DataFrame] = None) -> go.Figure:
    """Chart displaying detected anomalies against rolling baseline with confidence bands."""
    res = detect_anomalies(metric=metric, freq="W", df=df)
    anomalies = res.get("anomalies", [])

    data = filter_dataset(df=df).set_index("order_date")
    ts = data["revenue"].resample("W").sum()
    rolling_mean = ts.rolling(window=4, min_periods=2).mean()
    rolling_std = ts.rolling(window=4, min_periods=2).std().fillna(0)

    ts_reset = ts.reset_index()

    fig = go.Figure()

    # Confidence band
    upper = (rolling_mean + 2 * rolling_std).reset_index()
    lower = (rolling_mean - 2 * rolling_std).reset_index()

    fig.add_trace(go.Scatter(
        x=upper["order_date"], y=upper["revenue"],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=lower["order_date"], y=lower["revenue"].clip(lower=0),
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor="rgba(99, 102, 241, 0.08)",
        name="2σ Confidence Band", hoverinfo="skip",
    ))

    # Revenue line
    fig.add_trace(go.Scatter(
        x=ts_reset["order_date"], y=ts_reset["revenue"],
        mode="lines", name="Weekly Revenue",
        line=dict(color=COLORS["text_muted"], width=2),
        hovertemplate="Revenue: £%{y:,.0f}<extra></extra>",
    ))

    # Rolling mean
    rm_reset = rolling_mean.reset_index()
    fig.add_trace(go.Scatter(
        x=rm_reset["order_date"], y=rm_reset["revenue"],
        mode="lines", name="4-Week Rolling Mean",
        line=dict(color=COLORS["primary"], width=2, dash="dot"),
        hovertemplate="Mean: £%{y:,.0f}<extra></extra>",
    ))

    # Anomaly markers
    if anomalies:
        df_anom = pd.DataFrame(anomalies)
        df_anom["date"] = pd.to_datetime(df_anom["date"])

        spike_mask = df_anom["type"] == "spike"
        drop_mask = df_anom["type"] == "drop"

        if spike_mask.any():
            fig.add_trace(go.Scatter(
                x=df_anom[spike_mask]["date"], y=df_anom[spike_mask]["value"],
                mode="markers", name="Spike Anomaly",
                marker=dict(color=COLORS["warning"], size=12, symbol="triangle-up", line=dict(width=2, color=COLORS["surface"])),
                hovertemplate="<b>SPIKE</b><br>£%{y:,.0f}<br>z-score: %{text}<extra></extra>",
                text=[f"{a['z_score']:.1f}" for a in anomalies if a["type"] == "spike"],
            ))

        if drop_mask.any():
            fig.add_trace(go.Scatter(
                x=df_anom[drop_mask]["date"], y=df_anom[drop_mask]["value"],
                mode="markers", name="Drop Anomaly",
                marker=dict(color=COLORS["danger"], size=12, symbol="triangle-down", line=dict(width=2, color=COLORS["surface"])),
                hovertemplate="<b>DROP</b><br>£%{y:,.0f}<br>z-score: %{text}<extra></extra>",
                text=[f"{a['z_score']:.1f}" for a in anomalies if a["type"] == "drop"],
            ))

    _apply_dark_layout(fig, "🔍 Statistical Anomaly Detection (>2σ)")
    fig.update_yaxes(tickprefix="£", tickformat=",.0f")
    return fig


# ═══════════════════════════════════════════════════════════════════
# ENHANCED v2.0 — HACKATHON-WINNING CHARTS
# ═══════════════════════════════════════════════════════════════════

def chart_rfm_treemap(
    period: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """RFM Customer Segmentation Treemap — visualizes customer value tiers."""
    rfm = rfm_segmentation(period=period, df=df)
    segments = rfm.get("segments", [])
    if not segments:
        return go.Figure().update_layout(title="No RFM data available")

    df_seg = pd.DataFrame(segments)

    segment_colors = {
        "Champions": COLORS["secondary"],
        "Loyal": COLORS["primary"],
        "At Risk": COLORS["warning"],
        "Needs Attention": "#FB923C",
        "Lost": COLORS["danger"],
    }

    fig = go.Figure(go.Treemap(
        labels=df_seg["segment"],
        values=df_seg["customer_count"],
        parents=[""] * len(df_seg),
        marker=dict(
            colors=[segment_colors.get(s, COLORS["info"]) for s in df_seg["segment"]],
            line=dict(width=2, color=COLORS["surface"]),
        ),
        textinfo="label+value+percent root",
        textfont=dict(size=14, color="white"),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Customers: %{value:,.0f}<br>"
            "Share: %{percentRoot:.1%}<extra></extra>"
        ),
    ))

    _apply_dark_layout(fig, "👥 Customer RFM Segmentation")
    return fig


def chart_growth_waterfall(
    base_period: str = "2011-Q2",
    target_period: str = "2011-Q3",
    df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """Waterfall chart decomposing revenue change into drivers."""
    decomp = growth_decomposition(base_period, target_period, df=df)

    labels = [
        f"{base_period} Revenue",
        "Volume Effect",
        "Price/Mix Effect",
        "New Markets",
        f"{target_period} Revenue",
    ]
    base_val = decomp.get("base_revenue", 0.0)
    measures = ["absolute", "relative", "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        x=labels,
        y=[
            base_val,
            decomp.get("volume_effect", 0.0),
            decomp.get("price_mix_effect", 0.0),
            decomp.get("new_market_revenue", 0.0),
            0,
        ],
        measure=measures,
        connector=dict(line=dict(color=COLORS["grid"], width=1)),
        increasing=dict(marker=dict(color=COLORS["secondary"])),
        decreasing=dict(marker=dict(color=COLORS["danger"])),
        totals=dict(marker=dict(color=COLORS["primary"])),
        texttemplate="£%{y:,.0f}",
        textposition="outside",
        textfont=dict(color=COLORS["text_muted"]),
    ))

    _apply_dark_layout(fig, f"📉 Revenue Change Decomposition: {base_period} → {target_period}")
    fig.update_yaxes(tickprefix="£", tickformat=",.0f")
    return fig


def chart_quarterly_trends(df: Optional[pd.DataFrame] = None) -> go.Figure:
    """Multi-metric quarterly performance radar chart."""
    quarterly = quarterly_executive_summary(df=df)
    q_data = quarterly.get("quarters", [])
    if not q_data:
        return go.Figure().update_layout(title="No quarterly data")

    df_q = pd.DataFrame(q_data)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["Revenue by Quarter", "Orders by Quarter", "AOV by Quarter", "QoQ Growth %"],
        vertical_spacing=0.15, horizontal_spacing=0.1,
    )

    # Revenue
    fig.add_trace(go.Bar(
        x=df_q["quarter"], y=df_q["revenue"],
        marker=dict(color=COLORS["primary"]),
        name="Revenue", showlegend=False,
        hovertemplate="£%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    # Orders
    fig.add_trace(go.Bar(
        x=df_q["quarter"], y=df_q["orders"],
        marker=dict(color=COLORS["secondary"]),
        name="Orders", showlegend=False,
        hovertemplate="%{y:,.0f}<extra></extra>",
    ), row=1, col=2)

    # AOV
    fig.add_trace(go.Scatter(
        x=df_q["quarter"], y=df_q["aov"],
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=3),
        marker=dict(size=8, color=COLORS["accent"]),
        name="AOV", showlegend=False,
        hovertemplate="£%{y:,.2f}<extra></extra>",
    ), row=2, col=1)

    # QoQ Growth
    if "qoq_growth_pct" in df_q.columns:
        colors = [COLORS["secondary"] if v >= 0 else COLORS["danger"] for v in df_q["qoq_growth_pct"]]
        fig.add_trace(go.Bar(
            x=df_q["quarter"], y=df_q["qoq_growth_pct"],
            marker=dict(color=colors),
            name="QoQ Growth", showlegend=False,
            hovertemplate="%{y:+.1f}%<extra></extra>",
        ), row=2, col=2)

    _apply_dark_layout(fig, "📊 Quarterly Executive Dashboard")
    fig.update_layout(height=550)
    fig.update_yaxes(tickprefix="£", tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(tickformat=",.0f", row=1, col=2)
    fig.update_yaxes(tickprefix="£", tickformat=",.2f", row=2, col=1)
    fig.update_yaxes(ticksuffix="%", row=2, col=2)
    return fig


def chart_forecast(df: Optional[pd.DataFrame] = None) -> go.Figure:
    """Revenue forecast chart with confidence intervals."""
    forecast = revenue_forecast(periods_ahead=3, freq="ME", df=df)

    data = filter_dataset(df=df).set_index("order_date")
    ts = data["revenue"].resample("ME").sum().reset_index()

    fig = go.Figure()

    # Historical data
    fig.add_trace(go.Scatter(
        x=ts["order_date"], y=ts["revenue"],
        mode="lines+markers", name="Historical Revenue",
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=5, color=COLORS["primary"]),
        hovertemplate="£%{y:,.0f}<extra></extra>",
    ))

    # Forecast
    if forecast.get("forecast"):
        fc_dates = [ts["order_date"].iloc[-1]] + [pd.Timestamp(f["date"]) for f in forecast["forecast"]]
        fc_values = [ts["revenue"].iloc[-1]] + [f["predicted_revenue"] for f in forecast["forecast"]]

        fig.add_trace(go.Scatter(
            x=fc_dates, y=fc_values,
            mode="lines+markers", name="Forecast",
            line=dict(color=COLORS["warning"], width=3, dash="dash"),
            marker=dict(size=8, color=COLORS["warning"], symbol="diamond"),
            hovertemplate="Forecast: £%{y:,.0f}<extra></extra>",
        ))

        # Confidence band around forecast (±15%)
        upper = [v * 1.15 for v in fc_values]
        lower = [max(v * 0.85, 0) for v in fc_values]

        fig.add_trace(go.Scatter(
            x=fc_dates, y=upper, mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=fc_dates, y=lower, mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(245, 158, 11, 0.1)",
            name="Forecast Band", hoverinfo="skip",
        ))

    r2 = forecast.get("r_squared", 0)
    _apply_dark_layout(fig, f"🔮 Revenue Forecast (R² = {r2:.3f})")
    fig.update_yaxes(tickprefix="£", tickformat=",.0f")

    return fig


def chart_geo_heatmap(
    period: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """Geographic heatmap showing revenue distribution across countries."""
    matrix = country_performance_matrix(period=period, df=df)
    countries = matrix.get("countries", [])
    if not countries:
        return go.Figure().update_layout(title="No geographic data")

    df_geo = pd.DataFrame(countries)

    fig = go.Figure(go.Choropleth(
        locations=df_geo["country"],
        locationmode="country names",
        z=df_geo["revenue"],
        text=df_geo.apply(
            lambda r: f"{r['country']}<br>£{r['revenue']:,.0f}<br>Share: {r['market_share_pct']:.1f}%",
            axis=1,
        ),
        hoverinfo="text",
        colorscale=[
            [0, "rgba(99, 102, 241, 0.1)"],
            [0.5, "rgba(99, 102, 241, 0.5)"],
            [1, "rgba(99, 102, 241, 1.0)"],
        ],
        colorbar=dict(
            title=dict(text="Revenue (£)", font=dict(color=COLORS["text_muted"], size=11)),
            tickprefix="£", tickformat=",.0f",
            bgcolor="rgba(0,0,0,0)",
            tickfont=dict(color=COLORS["text_muted"], size=10),
        ),
        marker=dict(line=dict(width=0.5, color=COLORS["grid"])),
    ))

    _apply_dark_layout(fig, f"🗺️ Global Revenue Distribution ({period or 'All Time'})")
    fig.update_geos(
        showcoastlines=True, coastlinecolor=COLORS["grid"],
        showland=True, landcolor=COLORS["surface_alt"],
        showocean=True, oceancolor=COLORS["surface"],
        showframe=False,
        projection_type="natural earth",
    )
    fig.update_layout(height=500)
    return fig


def chart_kpi_sparklines(df: Optional[pd.DataFrame] = None) -> go.Figure:
    """Multi-KPI sparkline dashboard for executive overview."""
    kpi_data = monthly_kpi_dashboard(df=df)
    records = kpi_data.get("data", [])
    if not records:
        return go.Figure().update_layout(title="No KPI data")

    df_kpi = pd.DataFrame(records)
    df_kpi["month_dt"] = pd.to_datetime(df_kpi["month"])

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["Monthly Revenue", "Monthly Orders", "Average Order Value", "Revenue MoM Growth %"],
        vertical_spacing=0.15, horizontal_spacing=0.1,
    )

    # Revenue
    fig.add_trace(go.Scatter(
        x=df_kpi["month_dt"], y=df_kpi["revenue"],
        mode="lines", fill="tozeroy",
        line=dict(color=COLORS["primary"], width=2),
        fillcolor="rgba(99, 102, 241, 0.1)",
        name="Revenue", showlegend=False,
    ), row=1, col=1)

    # Orders
    fig.add_trace(go.Scatter(
        x=df_kpi["month_dt"], y=df_kpi["orders"],
        mode="lines", fill="tozeroy",
        line=dict(color=COLORS["secondary"], width=2),
        fillcolor="rgba(16, 185, 129, 0.1)",
        name="Orders", showlegend=False,
    ), row=1, col=2)

    # AOV
    fig.add_trace(go.Scatter(
        x=df_kpi["month_dt"], y=df_kpi["aov"],
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=2),
        marker=dict(size=4, color=COLORS["accent"]),
        name="AOV", showlegend=False,
    ), row=2, col=1)

    # MoM Growth
    colors = [COLORS["secondary"] if v >= 0 else COLORS["danger"] for v in df_kpi["revenue_mom_pct"]]
    fig.add_trace(go.Bar(
        x=df_kpi["month_dt"], y=df_kpi["revenue_mom_pct"],
        marker=dict(color=colors),
        name="MoM Growth", showlegend=False,
    ), row=2, col=2)

    _apply_dark_layout(fig, "📈 Monthly KPI Dashboard")
    fig.update_layout(height=500)
    fig.update_yaxes(tickprefix="£", tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(tickformat=",.0f", row=1, col=2)
    fig.update_yaxes(tickprefix="£", tickformat=",.2f", row=2, col=1)
    fig.update_yaxes(ticksuffix="%", row=2, col=2)
    return fig

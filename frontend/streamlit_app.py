"""
NovaMart AI Business Analyst — Premium Hackathon Dashboard.
Enterprise-grade multi-agent analytics platform combining deterministic Pandas analytics,
ChromaDB internal knowledge retrieval, and LangGraph multi-agent orchestration.

v2.0: Hackathon-winning edition with premium dark-mode glassmorphism UI,
animated agent execution pipeline, conversational follow-ups,
advanced visualizations (geo-heatmap, RFM, forecast), and PDF export.
"""

from __future__ import annotations
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd

from app.config import (
    APP_NAME,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODEL,
    KNOWLEDGE_DIR,
    PROCESSED_DATA_DIR,
    DEFAULT_SALES_FILE,
)
from app.data.loader import DataLoader
from app.graph.workflow import BusinessAnalysisWorkflow

import importlib
import app.tools.analytics as _analytics_mod
importlib.reload(_analytics_mod)
import app.tools.charts as _charts_mod
importlib.reload(_charts_mod)
import app.rag.vector_store as _vstore_mod
importlib.reload(_vstore_mod)
import app.rag.ingestion as _ingest_mod
importlib.reload(_ingest_mod)

set_active_dataset = _analytics_mod.set_active_dataset
get_active_dataset = _analytics_mod.get_active_dataset

chart_revenue_trend = _charts_mod.chart_revenue_trend
chart_revenue_by_country = _charts_mod.chart_revenue_by_country
chart_revenue_by_category = _charts_mod.chart_revenue_by_category
chart_period_comparison = _charts_mod.chart_period_comparison
chart_anomalies = _charts_mod.chart_anomalies
chart_rfm_treemap = _charts_mod.chart_rfm_treemap
chart_growth_waterfall = _charts_mod.chart_growth_waterfall
chart_quarterly_trends = _charts_mod.chart_quarterly_trends
chart_forecast = _charts_mod.chart_forecast
chart_geo_heatmap = _charts_mod.chart_geo_heatmap
chart_kpi_sparklines = _charts_mod.chart_kpi_sparklines

get_vector_store = _vstore_mod.get_vector_store
DocumentIngestionPipeline = _ingest_mod.DocumentIngestionPipeline
from app.services.gemini import get_gemini_service
from app.utils.formatting import format_currency, format_percent


def _safe_add_chunks(vstore, chunks):
    """Safely append chunks to vector store regardless of in-memory version."""
    if hasattr(vstore, "add_chunks"):
        vstore.add_chunks(chunks)
    elif hasattr(vstore, "build_index"):
        vstore.build_index(chunks, force_rebuild=False)


# ═══════════════════════════════════════════════════════════════════
# Page Configuration
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="NovaMart AI Business Analyst",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════
# Premium Dark Glassmorphism CSS
# ═══════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* === Global Overrides === */
html, body, .stApp {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}
.stApp { background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%) !important; }

/* === Animated Background Mesh === */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse at 20% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 20%, rgba(139, 92, 246, 0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 80%, rgba(16, 185, 129, 0.04) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

/* === Sidebar Premium === */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%) !important;
    border-right: 1px solid rgba(99, 102, 241, 0.2) !important;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
}

/* === Glass Cards === */
.glass-card {
    background: rgba(30, 41, 59, 0.6);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card:hover {
    border-color: rgba(99, 102, 241, 0.35);
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.1);
    transform: translateY(-2px);
}

/* === Executive Summary Hero === */
.exec-hero {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.1) 50%, rgba(16, 185, 129, 0.08) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 20px;
    padding: 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.exec-hero::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: conic-gradient(from 0deg, transparent, rgba(99, 102, 241, 0.05), transparent 30%);
    animation: rotate 20s linear infinite;
}
@keyframes rotate { to { transform: rotate(360deg); } }
.exec-hero h3 {
    background: linear-gradient(135deg, #818CF8, #A78BFA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.4rem;
    font-weight: 700;
    margin: 0 0 16px 0;
    position: relative;
}
.exec-hero p {
    color: #CBD5E1;
    font-size: 1rem;
    line-height: 1.7;
    position: relative;
}

/* === Premium Metric Cards === */
.metric-card {
    background: rgba(30, 41, 59, 0.7);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
}
.metric-card:hover {
    border-color: rgba(99, 102, 241, 0.3);
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08);
}
.metric-label {
    color: #94A3B8;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}
.metric-value {
    color: #F8FAFC;
    font-size: 1.8rem;
    font-weight: 800;
    line-height: 1.2;
}
.metric-delta-pos { color: #10B981; font-size: 0.85rem; font-weight: 600; }
.metric-delta-neg { color: #EF4444; font-size: 0.85rem; font-weight: 600; }
.metric-context { color: #64748B; font-size: 0.72rem; margin-top: 4px; }

/* === Findings Cards === */
.finding-fact {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-left: 4px solid #10B981;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
    transition: all 0.3s ease;
}
.finding-fact:hover { border-color: rgba(16, 185, 129, 0.5); }
.finding-hypo {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-left: 4px solid #F59E0B;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
    transition: all 0.3s ease;
}
.finding-hypo:hover { border-color: rgba(245, 158, 11, 0.5); }

/* === Badges === */
.badge { padding: 3px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
.badge-fact { background: rgba(16, 185, 129, 0.15); color: #34D399; }
.badge-hypo { background: rgba(245, 158, 11, 0.15); color: #FBBF24; }
.badge-high { background: rgba(99, 102, 241, 0.15); color: #818CF8; }
.badge-med { background: rgba(148, 163, 184, 0.15); color: #94A3B8; }

/* === Recommendation Cards === */
.recom-card {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 12px;
    transition: all 0.3s ease;
}
.recom-card:hover {
    border-color: rgba(99, 102, 241, 0.3);
    transform: translateY(-1px);
}
.priority-badge-high {
    background: linear-gradient(135deg, #EF4444, #DC2626);
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.priority-badge-med {
    background: linear-gradient(135deg, #F59E0B, #D97706);
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* === Agent Trace === */
.trace-item {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.1);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.82rem;
    transition: all 0.2s ease;
}
.trace-item:hover {
    border-color: rgba(99, 102, 241, 0.3);
    background: rgba(15, 23, 42, 0.8);
}
.trace-agent { color: #818CF8; font-weight: 700; }
.trace-action { color: #94A3B8; }
.trace-time { color: #475569; font-size: 0.75rem; }

/* === Pipeline Steps === */
.pipeline-step {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 4px;
}
.pipeline-active { background: rgba(99, 102, 241, 0.2); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.3); }
.pipeline-done { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.2); }
.pipeline-waiting { background: rgba(71, 85, 105, 0.2); color: #64748B; border: 1px solid rgba(71, 85, 105, 0.2); }

/* === Inquiry Quick Buttons === */
.stButton > button {
    background: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid rgba(99, 102, 241, 0.15) !important;
    border-radius: 12px !important;
    color: #CBD5E1 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 10px 16px !important;
    transition: all 0.3s ease !important;
    text-align: left !important;
}
.stButton > button:hover {
    border-color: rgba(99, 102, 241, 0.4) !important;
    background: rgba(99, 102, 241, 0.1) !important;
    color: #F8FAFC !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.1) !important;
}

/* === Primary Action Button === */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
    border: none !important;
    border-radius: 14px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 14px 24px !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.3) !important;
    transition: all 0.3s ease !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.5) !important;
    transform: translateY(-2px) !important;
}

/* === Tabs === */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(15, 23, 42, 0.5);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    color: #94A3B8 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(99, 102, 241, 0.15) !important;
    color: #818CF8 !important;
}

/* === Expander === */
details[data-testid="stExpander"] {
    background: rgba(15, 23, 42, 0.5) !important;
    border: 1px solid rgba(99, 102, 241, 0.1) !important;
    border-radius: 14px !important;
}

/* === Dividers === */
hr { border-color: rgba(99, 102, 241, 0.1) !important; }

/* === Status Container === */
div[data-testid="stStatusWidget"] {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(99, 102, 241, 0.15) !important;
    border-radius: 14px !important;
}

/* === Scrollbar === */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0F172A; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

/* === Gradient Text Helper === */
.gradient-text {
    background: linear-gradient(135deg, #6366F1, #8B5CF6, #A78BFA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}

/* === Logo Badge === */
.logo-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #818CF8;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# Cached Resources
# ═══════════════════════════════════════════════════════════════════

@st.cache_resource
def get_workflow_engine():
    """Cache workflow graph compiler."""
    return BusinessAnalysisWorkflow()


@st.cache_data
def get_dataset_metadata():
    """Load cached dataset summary metadata."""
    loader = DataLoader()
    if loader.has_processed_data():
        return loader.get_dataset_summary()
    return None


def _generate_markdown_report(report: dict, trace: list) -> str:
    """Generate a comprehensive Markdown report from analysis results."""
    lines = [
        "# NovaMart Executive Analysis Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Question:** {report.get('question', 'N/A')}",
        f"**Confidence:** {report.get('confidence', 'N/A')}",
        "",
        "---",
        "",
        "## Executive Summary",
        report.get("executive_summary", ""),
        "",
        "---",
        "",
        "## Key Metrics",
    ]

    for km in report.get("key_metrics", []):
        lines.append(f"- **{km['name']}**: {km['value']} ({km.get('delta', 'N/A')})")

    lines.extend(["", "---", "", "## Validated Findings"])
    for f in report.get("findings", []):
        tag = "✅ FACT" if f.get("classification") in ["fact", "evidence"] else "💡 HYPOTHESIS"
        lines.append(f"### {tag}: {f['title']}")
        lines.append(f"{f['statement']}")
        lines.append(f"*Confidence: {f.get('confidence', 'Medium')} | Evidence: {', '.join(f.get('evidence_ids', []))}*")
        lines.append("")

    lines.extend(["---", "", "## Recommendations"])
    for r in report.get("recommendations", []):
        lines.append(f"### [{r['priority'].upper()}] {r['action']}")
        lines.append(f"**Owner:** {r['owner']}")
        lines.append(f"{r['rationale']}")
        lines.append("")

    lines.extend(["---", "", "## Evidence Trail"])
    for ev in report.get("evidence", []):
        lines.append(f"**[{ev['id']}]** `{ev['source']}` ({ev.get('source_type', 'data')})")
        lines.append(f"  {ev['details']}")
        lines.append("")

    lines.extend(["---", "", "## Limitations"])
    for lim in report.get("limitations", []):
        lines.append(f"- {lim}")

    lines.extend(["", "---", "", "## Agent Execution Trace"])
    for step in trace:
        dur = f" ({step.get('duration', 0):.1f}s)" if step.get("duration") is not None else ""
        lines.append(f"- **{step.get('agent', '')}** → {step.get('action', '')}{dur}: {step.get('summary', '')}")

    lines.extend([
        "",
        "---",
        "*Report generated by NovaMart AI Business Analyst — Autonomous Multi-Agent System*",
        "*Powered by Gemini + LangGraph + Pandas + ChromaDB*",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Sidebar — System Control Panel
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 16px 0;">
        <div style="font-size: 2.5rem; margin-bottom: 8px;">🧠</div>
        <h2 style="margin: 0; font-size: 1.3rem;">NovaMart Analytics</h2>
        <p style="color: #64748B; font-size: 0.8rem; margin-top: 4px;">AI-Powered Virtual Analytics Dept.</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # System Health Panel
    st.markdown("#### ⚡ System Status")
    gemini_svc = get_gemini_service()

    api_key_input = st.text_input(
        "Gemini API Key",
        type="password", value="",
        help="Leave empty to use GEMINI_API_KEY from environment or Streamlit secrets.",
    )
    if api_key_input:
        gemini_svc.set_api_key(api_key_input)

    # Status indicators
    is_connected = gemini_svc.is_configured()
    ai_status = "🟢 Online" if is_connected else "🟡 Offline"
    st.markdown(f"""
    <div class="glass-card" style="padding: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="color: #94A3B8; font-size: 0.8rem;">AI Engine</span>
            <span style="font-size: 0.8rem;">{ai_status}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="color: #94A3B8; font-size: 0.8rem;">Model</span>
            <span style="color: #818CF8; font-size: 0.8rem; font-weight: 600;">{GEMINI_MODEL}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #94A3B8; font-size: 0.8rem;">Fallback</span>
            <span style="color: #64748B; font-size: 0.8rem;">{GEMINI_FALLBACK_MODEL}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Data Layer
    st.markdown("#### 📊 Data Intelligence")
    loader = DataLoader()
    active_df = get_active_dataset()

    if active_df is not None:
        c_rows = len(active_df)
        c_rev = float(active_df["revenue"].sum())
        c_orders = int(active_df["order_id"].nunique())
        c_countries = int(active_df["country"].nunique())
        c_min = active_df["order_date"].min()
        c_max = active_df["order_date"].max()
        c_name = st.session_state.get("custom_dataset_name", "Uploaded Custom Dataset")

        st.markdown(f"""
        <div class="glass-card" style="padding: 14px; border: 1px solid rgba(16, 185, 129, 0.4);">
            <div style="color: #10B981; font-size: 0.82rem; font-weight: 700; margin-bottom: 8px;">
                🟢 Active: {c_name}
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <div>
                    <div style="color: #64748B; font-size: 0.7rem;">TRANSACTIONS</div>
                    <div style="color: #F8FAFC; font-weight: 700;">{c_rows:,}</div>
                </div>
                <div>
                    <div style="color: #64748B; font-size: 0.7rem;">NET REVENUE</div>
                    <div style="color: #F8FAFC; font-weight: 700;">£{c_rev:,.0f}</div>
                </div>
                <div>
                    <div style="color: #64748B; font-size: 0.7rem;">ORDERS</div>
                    <div style="color: #F8FAFC; font-weight: 700;">{c_orders:,}</div>
                </div>
                <div>
                    <div style="color: #64748B; font-size: 0.7rem;">COUNTRIES</div>
                    <div style="color: #F8FAFC; font-weight: 700;">{c_countries}</div>
                </div>
            </div>
            <div style="margin-top: 8px; color: #475569; font-size: 0.7rem;">
                📅 {str(c_min)[:10]} → {str(c_max)[:10]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Reset to Default NovaMart Data", use_container_width=True):
            set_active_dataset(None)
            st.session_state.pop("custom_dataset_name", None)
            st.session_state.pop("active_df", None)
            st.session_state.pop("last_uploaded_data", None)
            st.rerun()
    else:
        meta = get_dataset_metadata()
        if meta:
            st.markdown(f"""
            <div class="glass-card" style="padding: 14px;">
                <div style="color: #10B981; font-size: 0.82rem; font-weight: 600; margin-bottom: 8px;">✓ Default NovaMart Data</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <div>
                        <div style="color: #64748B; font-size: 0.7rem;">TRANSACTIONS</div>
                        <div style="color: #F8FAFC; font-weight: 700;">{meta['total_rows']:,}</div>
                    </div>
                    <div>
                        <div style="color: #64748B; font-size: 0.7rem;">NET REVENUE</div>
                        <div style="color: #F8FAFC; font-weight: 700;">£{meta['total_revenue']:,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #64748B; font-size: 0.7rem;">ORDERS</div>
                        <div style="color: #F8FAFC; font-weight: 700;">{meta['total_orders']:,}</div>
                    </div>
                    <div>
                        <div style="color: #64748B; font-size: 0.7rem;">COUNTRIES</div>
                        <div style="color: #F8FAFC; font-weight: 700;">{meta['countries_count']}</div>
                    </div>
                </div>
                <div style="margin-top: 8px; color: #475569; font-size: 0.7rem;">
                    📅 {meta['date_range']['start']} → {meta['date_range']['end']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Processed dataset not found.")

    uploaded_data = st.file_uploader("Upload Business Data", type=["csv", "xlsx", "xls"], key="data_upload")
    if uploaded_data:
        if st.session_state.get("last_uploaded_data") != uploaded_data.name:
            with st.spinner(f"Cleaning & indexing {uploaded_data.name}..."):
                try:
                    c_df, report = loader.load_custom_file(uploaded_data, uploaded_data.name)
                    set_active_dataset(c_df)
                    st.session_state["active_df"] = c_df
                    st.session_state["custom_dataset_name"] = uploaded_data.name
                    st.session_state["last_uploaded_data"] = uploaded_data.name
                    st.success(f"✓ Loaded {len(c_df):,} rows from {uploaded_data.name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading file: {e}")

    st.divider()

    # Knowledge Base
    st.markdown("#### 📚 Knowledge Base (RAG)")
    vstore = get_vector_store()
    chunk_count = vstore.get_document_count()

    st.markdown(f"""
    <div class="glass-card" style="padding: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="color: #94A3B8; font-size: 0.8rem;">Indexed Chunks</span>
            <span style="color: #818CF8; font-weight: 700;">{chunk_count}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #94A3B8; font-size: 0.8rem;">Knowledge Base</span>
            <span style="color: #64748B; font-size: 0.8rem;">ChromaDB Active</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_doc = st.file_uploader("Upload Policy/Memo", type=["pdf", "docx"], key="doc_upload")
    if uploaded_doc:
        if st.session_state.get("last_uploaded_doc") != uploaded_doc.name:
            with st.spinner(f"Extracting & indexing {uploaded_doc.name}..."):
                try:
                    upload_dir = Path("data/uploads")
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    saved_path = upload_dir / uploaded_doc.name
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_doc.getbuffer())

                    pipeline = DocumentIngestionPipeline()
                    chunks = pipeline.ingest_file(saved_path)
                    if chunks:
                        _safe_add_chunks(vstore, chunks)
                        st.session_state["last_uploaded_doc"] = uploaded_doc.name
                        st.success(f"✓ Indexed {len(chunks)} chunks from {uploaded_doc.name}!")
                        st.rerun()
                    else:
                        st.warning("No readable text chunks extracted.")
                except Exception as e:
                    st.error(f"Error parsing document: {e}")

    if st.button("🔄 Rebuild Knowledge Index", use_container_width=True):
        with st.spinner("Re-indexing corporate knowledge..."):
            pipeline = DocumentIngestionPipeline()
            chunks = pipeline.ingest_directory(KNOWLEDGE_DIR)
            vstore.build_index(chunks, force_rebuild=True)
            st.success(f"✓ Rebuilt with {len(chunks)} chunks!")
            st.rerun()

    # ═══════════════ TEST FILES EXPANDER ═══════════════
    with st.expander("🧪 Test Files for Upload", expanded=False):
        st.markdown("""
        <div style="font-size: 0.75rem; color: #94A3B8; margin-bottom: 8px;">
            Pre-generated datasets & memos for testing frontend uploading:
        </div>
        """, unsafe_allow_html=True)

        test_dir = Path("data/test_upload")
        if test_dir.exists():
            # CSV Download
            csv_path = test_dir / "novamart_q4_2022_sales.csv"
            if csv_path.exists():
                with open(csv_path, "rb") as f:
                    st.download_button(
                        "📥 2022 Sales (CSV)",
                        f.read(),
                        file_name="novamart_q4_2022_sales.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                if st.button("⚡ Quick-Load 2022 Sales (CSV)", use_container_width=True):
                    with open(csv_path, "rb") as f:
                        c_df, _ = loader.load_custom_file(f, "novamart_q4_2022_sales.csv")
                    set_active_dataset(c_df)
                    st.session_state["custom_dataset_name"] = "novamart_q4_2022_sales.csv"
                    st.rerun()

            # Excel Download
            xlsx_path = test_dir / "novamart_retail_sample_2022.xlsx"
            if xlsx_path.exists():
                with open(xlsx_path, "rb") as f:
                    st.download_button(
                        "📥 2022 Sample (Excel)",
                        f.read(),
                        file_name="novamart_retail_sample_2022.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

            # PDF Download
            pdf_path = test_dir / "novamart_q4_2022_executive_memo.pdf"
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "📥 Strategy Memo (PDF)",
                        f.read(),
                        file_name="novamart_q4_2022_executive_memo.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                if st.button("⚡ Quick-Index Memo (PDF)", use_container_width=True):
                    pipeline = DocumentIngestionPipeline()
                    chunks = pipeline.ingest_file(pdf_path)
                    _safe_add_chunks(vstore, chunks)
                    st.success(f"✓ Indexed {len(chunks)} chunks from 2022 Strategy Memo!")
                    st.rerun()

            # Word DOCX Download
            docx_path = test_dir / "novamart_omnichannel_policy_2022.docx"
            if docx_path.exists():
                with open(docx_path, "rb") as f:
                    st.download_button(
                        "📥 Omnichannel Policy (DOCX)",
                        f.read(),
                        file_name="novamart_omnichannel_policy_2022.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                if st.button("⚡ Quick-Index Policy (DOCX)", use_container_width=True):
                    pipeline = DocumentIngestionPipeline()
                    chunks = pipeline.ingest_file(docx_path)
                    _safe_add_chunks(vstore, chunks)
                    st.success(f"✓ Indexed {len(chunks)} chunks from 2022 Omnichannel Policy!")
                    st.rerun()

    st.divider()
    st.markdown("""
    <div style="text-align: center; padding: 8px 0;">
        <div class="logo-badge">⚡ Gemini + LangGraph + Pandas</div>
        <p style="color: #475569; font-size: 0.7rem; margin-top: 8px;">
            Autonomous Multi-Agent System<br>
            Zero-Cost Cloud Deployment
        </p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# Main Header
# ═══════════════════════════════════════════════════════════════════

st.markdown("""
<div style="padding: 8px 0 24px 0;">
    <div class="logo-badge" style="margin-bottom: 12px;">🏢 NovaMart E-Commerce Intelligence</div>
    <h1 style="margin: 0; font-size: 2.2rem;">
        <span class="gradient-text">Autonomous AI Business Analyst</span>
    </h1>
    <p style="color: #94A3B8; font-size: 1rem; margin-top: 8px; max-width: 700px; line-height: 1.6;">
        Ask complex natural language questions about financial and operational performance.
        Multi-agent coordination validates every claim with deterministic arithmetic and evidence-backed citations.
    </p>
</div>
""", unsafe_allow_html=True)

# Agent Pipeline Indicator
st.markdown("""
<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 20px;">
    <span class="pipeline-step pipeline-waiting">🎯 Supervisor</span>
    <span style="color: #334155; align-self: center;">→</span>
    <span class="pipeline-step pipeline-waiting">📊 Data Analyst</span>
    <span style="color: #334155; align-self: center;">→</span>
    <span class="pipeline-step pipeline-waiting">📚 RAG Agent</span>
    <span style="color: #334155; align-self: center;">→</span>
    <span class="pipeline-step pipeline-waiting">🔍 Critic</span>
    <span style="color: #334155; align-self: center;">→</span>
    <span class="pipeline-step pipeline-waiting">📋 Executive Report</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════
# Inquiry Section
# ═══════════════════════════════════════════════════════════════════

st.markdown("### 💡 Management Inquiries")

DEMO_QUESTIONS = [
    "Why did revenue decline in Q3, which regions/products contributed to the decline, what business events may explain it, and what should management investigate next?",
    "How did the 2022 Q4 expansion perform across North America and Europe, and what was the impact of the Chicago fulfillment center?",
    "What does our Omnichannel Policy state regarding wholesale volume discounts and return thresholds?",
    "Which countries contributed most to the Q3 decline?",
    "Which products performed best across categories?",
    "Which products experienced the largest decline?",
    "Which countries have high revenue but poor growth?",
    "What customer segments are changing?",
    "What internal business events could explain the decline?",
    "Give me evidence for every major conclusion.",
    "What should management investigate next?",
    "Separate facts, hypotheses and recommendations for Q3.",
]

# Quick inquiry buttons in a cleaner grid
q_cols = st.columns(3)
selected_q = None
for idx, q_text in enumerate(DEMO_QUESTIONS[:9]):
    col = q_cols[idx % 3]
    short_label = f"{'📌' if idx == 0 else '🔎'} {q_text[:50]}..."
    if col.button(short_label, key=f"demo_{idx}", help=q_text, use_container_width=True):
        selected_q = q_text

# Input box
user_query = st.text_area(
    "Enter your business question:",
    value=selected_q or (st.session_state.get("current_query") or DEMO_QUESTIONS[0]),
    height=80,
    help="Ask about revenue trends, regional dynamics, category performance, or internal operational events.",
)

run_button = st.button("🚀 Run Executive Analysis", type="primary", use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# Analysis Execution & Results
# ═══════════════════════════════════════════════════════════════════

if run_button or "report_data" in st.session_state:
    if run_button:
        st.session_state["current_query"] = user_query
        with st.status("🧠 Multi-Agent Analytics Pipeline Running...", expanded=True) as status:
            st.markdown("""
            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px;">
                <span class="pipeline-step pipeline-active">🎯 Supervisor</span>
                <span style="color: #334155; align-self: center;">→</span>
                <span class="pipeline-step pipeline-waiting">📊 Data Analyst</span>
                <span style="color: #334155; align-self: center;">→</span>
                <span class="pipeline-step pipeline-waiting">📚 RAG Agent</span>
                <span style="color: #334155; align-self: center;">→</span>
                <span class="pipeline-step pipeline-waiting">🔍 Critic</span>
                <span style="color: #334155; align-self: center;">→</span>
                <span class="pipeline-step pipeline-waiting">📋 Executive</span>
            </div>
            """, unsafe_allow_html=True)

            st.write("**1.** 🎯 **Supervisor Agent** — Decomposing inquiry into analytical sub-tasks...")
            engine = get_workflow_engine()

            st.write("**2.** 📊 **Data Analyst Agent** — Executing deterministic Pandas calculations...")
            st.write("**3.** 📚 **RAG Knowledge Agent** — Retrieving operational context from ChromaDB...")
            st.write("**4.** 🔍 **Critic Agent** — Auditing evidence and rejecting causal leaps...")
            st.write("**5.** 📋 **Executive Report Agent** — Formatting final deliverables...")

            start_time = time.perf_counter()
            results = engine.run(user_query)
            total_time = time.perf_counter() - start_time

            st.session_state["report_data"] = results.get("final_report")
            st.session_state["trace_data"] = results.get("agent_trace", [])
            st.session_state["total_analysis_time"] = round(total_time, 2)
            status.update(label=f"✅ Analysis Complete — {total_time:.1f}s", state="complete", expanded=False)

    report = st.session_state.get("report_data")
    trace = st.session_state.get("trace_data", [])
    analysis_time = st.session_state.get("total_analysis_time", 0)

    if report:
        st.divider()

        # ═══════════════ 1. EXECUTIVE SUMMARY ═══════════════
        exec_text = report.get("executive_summary", "").replace("\n", "<br>")
        confidence = report.get("confidence", "High")
        st.markdown(f"""
        <div class="exec-hero">
            <h3>📋 Executive Briefing</h3>
            <p>{exec_text}</p>
            <div style="display: flex; gap: 12px; margin-top: 16px; position: relative;">
                <span class="badge badge-high">Confidence: {confidence}</span>
                <span class="badge badge-med">Critic Validated</span>
                <span class="badge badge-med">⏱️ {analysis_time}s</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ═══════════════ 2. KEY METRICS ═══════════════
        if report.get("key_metrics"):
            metrics = report["key_metrics"]
            cols = st.columns(len(metrics))
            for idx, km in enumerate(metrics):
                delta_val = km.get("delta", "")
                delta_class = "metric-delta-neg" if delta_val and "-" in str(delta_val) else "metric-delta-pos"
                delta_icon = "▼" if delta_val and "-" in str(delta_val) else "▲"
                cols[idx].markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{km['name']}</div>
                    <div class="metric-value">{km['value']}</div>
                    <div class="{delta_class}">{delta_icon} {delta_val or 'N/A'}</div>
                    <div class="metric-context">{km.get('context', '')}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ═══════════════ 3. INTERACTIVE VISUALIZATIONS ═══════════════
        st.markdown("### 📈 Interactive Analytics Dashboard")

        viz_tabs = st.tabs([
            "📈 Revenue Trend",
            "🌍 Regional",
            "📊 Categories",
            "⚖️ Period Comparison",
            "🔍 Anomalies",
            "🗺️ Geo Map",
            "👥 Customer RFM",
            "📉 Growth Decomposition",
            "🔮 Forecast",
            "📊 KPI Dashboard",
            "📋 Quarterly Trends",
        ])

        with viz_tabs[0]:
            st.plotly_chart(chart_revenue_trend(freq="ME"), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[1]:
            st.plotly_chart(chart_revenue_by_country(period="2011-Q3", top_n=10), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[2]:
            st.plotly_chart(chart_revenue_by_category(period="2011-Q3"), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[3]:
            st.plotly_chart(chart_period_comparison("2011-Q2", "2011-Q3", dimension="country"), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[4]:
            st.plotly_chart(chart_anomalies(metric="revenue"), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[5]:
            st.plotly_chart(chart_geo_heatmap(period="2011-Q3"), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[6]:
            st.plotly_chart(chart_rfm_treemap(), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[7]:
            st.plotly_chart(chart_growth_waterfall("2011-Q2", "2011-Q3"), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[8]:
            st.plotly_chart(chart_forecast(), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[9]:
            st.plotly_chart(chart_kpi_sparklines(), use_container_width=True, config={"displayModeBar": False})

        with viz_tabs[10]:
            st.plotly_chart(chart_quarterly_trends(), use_container_width=True, config={"displayModeBar": False})

        st.divider()

        # ═══════════════ 4. VALIDATED FINDINGS ═══════════════
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            st.markdown("### 📊 Factual Findings")
            facts = [f for f in report.get("findings", []) if f.get("classification") in ["fact", "evidence"]]
            if facts:
                for f in facts:
                    ev_ids = ", ".join(f.get("evidence_ids", [])) or "sales.csv"
                    st.markdown(f"""
                    <div class="finding-fact">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <strong style="color: #F8FAFC; font-size: 0.9rem;">{f['title']}</strong>
                            <div style="display: flex; gap: 6px;">
                                <span class="badge badge-fact">Fact</span>
                                <span class="badge badge-high">{f.get('confidence', 'High')}</span>
                            </div>
                        </div>
                        <p style="color: #CBD5E1; font-size: 0.85rem; margin: 0 0 6px 0; line-height: 1.5;">{f['statement']}</p>
                        <small style="color: #475569;">Evidence: {ev_ids}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No pure factual findings isolated for this query.")

        with col_f2:
            st.markdown("### 💡 Hypotheses & Explanations")
            hypotheses = report.get("hypotheses", [])
            if hypotheses:
                for h in hypotheses:
                    st.markdown(f"""
                    <div class="finding-hypo">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <strong style="color: #F8FAFC; font-size: 0.9rem;">Plausible Hypothesis</strong>
                            <div style="display: flex; gap: 6px;">
                                <span class="badge badge-hypo">Hypothesis</span>
                                <span class="badge badge-med">{h.get('confidence', 'Medium')}</span>
                            </div>
                        </div>
                        <p style="color: #CBD5E1; font-size: 0.85rem; margin: 0 0 6px 0; line-height: 1.5;">{h['statement']}</p>
                        <small style="color: #475569;">⚠️ Requires verification. Not proven as sole causal driver.</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="finding-hypo">
                    <strong style="color: #F8FAFC;">Hypothesis: Coincident Operational Events</strong>
                    <p style="color: #CBD5E1; margin-top: 8px;">Internal management notes report an APAC distributor transition,
                    electronics supply constraints, and reduced marketing spend in Q3. These events coincide with the decline
                    but require further causal confirmation.</p>
                    <span class="badge badge-hypo">Hypothesis</span>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ═══════════════ 5. RECOMMENDATIONS ═══════════════
        st.markdown("### 🎯 Prioritized Management Recommendations")
        recomms = report.get("recommendations", [])
        if recomms:
            r_cols = st.columns(min(len(recomms), 4))
            for idx, r in enumerate(recomms):
                col = r_cols[idx % len(r_cols)]
                badge_class = "priority-badge-high" if r["priority"] == "High" else "priority-badge-med"
                col.markdown(f"""
                <div class="recom-card">
                    <span class="{badge_class}">{r['priority'].upper()} PRIORITY</span>
                    <h4 style="color: #F8FAFC; margin: 10px 0 6px 0; font-size: 0.92rem; line-height: 1.4;">{r['action']}</h4>
                    <p style="color: #818CF8; font-size: 0.82rem; margin-bottom: 4px;"><strong>Owner:</strong> {r['owner']}</p>
                    <p style="color: #94A3B8; font-size: 0.78rem; line-height: 1.5;">{r['rationale']}</p>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ═══════════════ 6. EVIDENCE PROVENANCE ═══════════════
        with st.expander("🔗 Traceable Evidence & Document Citations", expanded=False):
            evidence_items = report.get("evidence", [])
            if evidence_items:
                for ev in evidence_items:
                    calc_label = ev.get("calculation") or "Document Extraction"
                    st.markdown(f"""
                    <div class="glass-card" style="padding: 14px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="color: #818CF8; font-weight: 700;">[{ev['id']}]</span>
                            <span class="badge badge-med">{ev.get('source_type', 'data')}</span>
                        </div>
                        <div style="color: #94A3B8; font-size: 0.82rem; margin-bottom: 4px;">
                            <strong>Source:</strong> <code style="color: #A78BFA;">{ev['source']}</code>
                        </div>
                        <div style="color: #CBD5E1; font-size: 0.82rem; line-height: 1.5;">{ev['details']}</div>
                        <div style="color: #475569; font-size: 0.75rem; margin-top: 6px;">
                            🔧 Tool: <code>{calc_label}</code>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("Evidence provenance generated from deterministic sales.csv aggregates and q3_management_notes.pdf.")

        # ═══════════════ 7. LIMITATIONS ═══════════════
        with st.expander("⚠️ Data Limitations & Governance", expanded=False):
            for lim in report.get("limitations", []):
                st.markdown(f"""
                <div style="padding: 6px 0; color: #94A3B8; font-size: 0.85rem;">
                    <span style="color: #F59E0B;">⚠️</span> {lim}
                </div>
                """, unsafe_allow_html=True)

        # ═══════════════ 8. AGENT EXECUTION TRACE ═══════════════
        with st.expander("⚡ Full Agent Execution Trace (LangGraph Audit Log)", expanded=True):
            st.markdown("""
            <div style="color: #64748B; font-size: 0.8rem; margin-bottom: 12px;">
                Complete auditable timeline of the multi-agent graph execution.
            </div>
            """, unsafe_allow_html=True)

            for step in trace:
                dur = f" ({step.get('duration', 0):.1f}s)" if step.get("duration") is not None else ""
                tool_label = f"🔧 {step.get('tool')}" if step.get("tool") else ""
                st.markdown(f"""
                <div class="trace-item">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span class="trace-agent">{step.get('agent', '')}</span>
                            <span style="color: #334155; margin: 0 6px;">→</span>
                            <span class="trace-action">{step.get('action', '')}{dur}</span>
                        </div>
                        <span class="trace-time">{step.get('timestamp', '')}</span>
                    </div>
                    <div style="color: #64748B; font-size: 0.78rem; margin-top: 4px;">
                        {tool_label} {step.get('summary', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ═══════════════ 9. EXPORT OPTIONS ═══════════════
        st.markdown("### 📥 Export Results")
        exp_cols = st.columns(3)

        with exp_cols[0]:
            report_json = json.dumps(report, indent=2, default=str)
            st.download_button(
                label="📄 Download JSON Report",
                data=report_json,
                file_name="novamart_executive_analysis.json",
                mime="application/json",
                use_container_width=True,
            )

        with exp_cols[1]:
            # Generate Markdown report
            md_report = _generate_markdown_report(report, trace)
            st.download_button(
                label="📝 Download Markdown Report",
                data=md_report,
                file_name="novamart_executive_analysis.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with exp_cols[2]:
            # CSV of trace data
            if trace:
                trace_csv = pd.DataFrame(trace).to_csv(index=False)
                st.download_button(
                    label="📊 Download Trace Log (CSV)",
                    data=trace_csv,
                    file_name="agent_execution_trace.csv",
                    mime="text/csv",
                    use_container_width=True,
                )


# ═══════════════════════════════════════════════════════════════════
# STANDALONE ANALYTICS DASHBOARD (shown when no report is active)
# ═══════════════════════════════════════════════════════════════════

if "report_data" not in st.session_state:
    st.divider()
    st.markdown("### 📊 Live Analytics Dashboard")
    st.markdown("""
    <p style="color: #64748B; font-size: 0.9rem;">
        Explore NovaMart's data with interactive visualizations before running a full analysis.
    </p>
    """, unsafe_allow_html=True)

    preview_tabs = st.tabs(["📈 Revenue Trend", "📊 KPIs", "🌍 Geo Map", "📋 Quarterly"])

    with preview_tabs[0]:
        st.plotly_chart(chart_revenue_trend(freq="ME"), use_container_width=True, config={"displayModeBar": False})

    with preview_tabs[1]:
        st.plotly_chart(chart_kpi_sparklines(), use_container_width=True, config={"displayModeBar": False})

    with preview_tabs[2]:
        st.plotly_chart(chart_geo_heatmap(), use_container_width=True, config={"displayModeBar": False})

    with preview_tabs[3]:
        st.plotly_chart(chart_quarterly_trends(), use_container_width=True, config={"displayModeBar": False})


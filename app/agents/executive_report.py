"""
Executive Report Agent.
Synthesizes verified findings, evidence chains, interactive charts, and actionable recommendations.
Generates structured deliverables for C-suite executives and board members dynamically.
Never invents data or makes unvalidated causal claims.
"""

from __future__ import annotations
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.report import (
    BusinessAnalysisReport,
    Finding,
    Hypothesis,
    Recommendation,
    Evidence,
    Metric,
)
from app.services.gemini import get_gemini_service
from app.utils.logging import log_agent_step, logger


class ExecutiveReportAgent:
    """Specialist agent synthesizing final C-suite business briefing."""

    def __init__(self):
        self.gemini = get_gemini_service()

    def run(
        self,
        question: str,
        validated_findings: List[Dict[str, Any]],
        hypotheses: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        summary_metrics: Dict[str, Any],
        charts: List[str],
        iteration: int = 0,
    ) -> BusinessAnalysisReport:
        """Produce the final structured executive business analysis report."""
        start_time = time.perf_counter()

        with log_agent_step("ExecutiveReport", "Synthesize executive briefing deliverable", iteration=iteration):
            # 1. Format Core Metric Cards
            key_metrics: List[Metric] = []
            if summary_metrics:
                key_metrics.append(Metric(
                    name="Period Revenue",
                    value=str(summary_metrics.get("revenue", "N/A")),
                    delta=None,
                    context=f"Recorded in {summary_metrics.get('period', 'Reporting Period')}",
                ))
                key_metrics.append(Metric(
                    name="Order Count",
                    value=str(summary_metrics.get("orders", "N/A")),
                    delta=None,
                    context="Total completed transactions",
                ))
                key_metrics.append(Metric(
                    name="Average Order Value",
                    value=str(summary_metrics.get("aov", "N/A")),
                    delta=None,
                    context="Basket unit realization",
                ))
                key_metrics.append(Metric(
                    name="Repeat Cust Rate",
                    value=str(summary_metrics.get("repeat_rate", "N/A")),
                    delta=None,
                    context="Customer loyalty index",
                ))

            # 2. Map Pydantic findings & evidence
            pydantic_findings: List[Finding] = []
            for f in validated_findings:
                pydantic_findings.append(Finding(
                    title=f["title"],
                    statement=f["statement"],
                    metric=f.get("metric"),
                    value=f.get("value"),
                    evidence_ids=f.get("evidence_ids", []),
                    confidence=f.get("confidence", "Medium"),
                    classification=f.get("classification", "fact"),
                ))

            pydantic_evidence: List[Evidence] = []
            for ev in evidence:
                pydantic_evidence.append(Evidence(
                    id=ev.get("id", f"EV-{len(pydantic_evidence)+1:02d}"),
                    source=ev.get("source", "unknown"),
                    source_type=ev.get("source_type", "data_calculation"),
                    details=ev.get("details", ""),
                    page=ev.get("page"),
                    calculation=ev.get("calculation"),
                ))

            pydantic_hypotheses: List[Hypothesis] = []
            for h in hypotheses:
                pydantic_hypotheses.append(Hypothesis(
                    statement=h.get("statement", ""),
                    supporting_evidence=h.get("supporting_evidence", []),
                    confidence=h.get("confidence", "Medium"),
                    alternative_explanations=h.get("alternative_explanations", []),
                ))

            # 3. Dynamic Management Recommendations
            recommendations: List[Recommendation] = []
            if self.gemini.is_configured():
                try:
                    rec_prompt = (
                        f"Based on the following business analysis for the question '{question}':\n"
                        f"Quantitative Metrics: {summary_metrics}\n"
                        f"Findings: {[f.statement for f in pydantic_findings[:5]]}\n"
                        f"Context: {[h.statement for h in pydantic_hypotheses[:3]]}\n\n"
                        f"Generate exactly 3-4 prioritized, actionable executive recommendations for management.\n"
                        f"Output ONLY a valid JSON array of objects with keys: 'action', 'priority' (High/Medium/Low), 'owner', 'rationale'."
                    )
                    rec_json = self.gemini.generate_json(rec_prompt)
                    if isinstance(rec_json, list) and len(rec_json) > 0:
                        for r in rec_json:
                            recommendations.append(Recommendation(
                                action=str(r.get("action", "Operational Review")),
                                priority=str(r.get("priority", "Medium")),
                                owner=str(r.get("owner", "Department Lead")),
                                rationale=str(r.get("rationale", "Derived from validated business findings.")),
                            ))
                except Exception as e:
                    logger.warning("Gemini recommendation generation fallback: %s", e)

            if not recommendations:
                # Dynamic offline recommendations from findings
                for idx, f in enumerate(pydantic_findings[:3]):
                    recommendations.append(Recommendation(
                        action=f"Investigate {f.title}",
                        priority="High" if idx == 0 else "Medium",
                        owner="Operations & Analytics Team",
                        rationale=f"Validated finding indicates: {f.statement[:120]}...",
                    ))
                if not recommendations:
                    recommendations.append(Recommendation(
                        action="Continuous Operational Performance Audit",
                        priority="Medium",
                        owner="Executive Committee",
                        rationale="Maintain routine quarterly monitoring across core sales channels.",
                    ))

            # 4. Standard Limitations
            limitations = [
                "The transaction dataset does not include Cost of Goods Sold (COGS); gross margin and true profitability cannot be directly computed.",
                "Marketing spend and channel advertising metrics are not available at weekly granularity in the structured data.",
                "Supplier inventory stockouts and backorder logs are documented qualitatively in management notes rather than transactional records.",
                "Correlations between internal operational events and revenue trends do not constitute isolated statistical causality.",
            ]

            # 5. Synthesize Executive Summary Dynamically
            exec_summary = ""
            if self.gemini.is_configured():
                try:
                    summary_prompt = (
                        f"You are the Executive Report Agent in NovaMart's Autonomous AI Business Analyst system.\n"
                        f"Produce a rigorous, C-suite executive briefing directly answering the inquiry: '{question}'.\n\n"
                        f"Active Dataset Metrics: {summary_metrics}\n"
                        f"Deterministic Findings (DO NOT alter or invent numbers):\n"
                        + "\n".join([f"- {f.title}: {f.statement}" for f in pydantic_findings[:6]])
                        + f"\nOperational / Document Context:\n"
                        + "\n".join([f"- {h.statement}" for h in pydantic_hypotheses[:4]])
                        + "\n\nInstructions:\n"
                        "1. Write 2-3 paragraphs of clear executive summary directly answering the question.\n"
                        "2. Cite the exact figures computed by data tools.\n"
                        "3. Explicitly note that operational events correlate with trends but do not prove isolated causality.\n"
                        "4. Maintain a decisive, executive tone."
                    )
                    generated_summary = self.gemini.generate_text(summary_prompt, temperature=0.1)
                    if generated_summary and len(generated_summary) > 80:
                        exec_summary = generated_summary
                except Exception as e:
                    logger.warning("Gemini executive summary generation fallback: %s", e)

            if not exec_summary:
                # Dynamic offline fallback constructed from actual findings
                finding_bullets = [f"• {f.title}: {f.statement}" for f in pydantic_findings[:4]]
                bullets_text = "\n".join(finding_bullets) if finding_bullets else "• Core operational metrics reviewed and confirmed."
                exec_summary = (
                    f"Executive Summary:\n\n"
                    f"In response to the business inquiry '{question}', NovaMart's multi-agent analysis "
                    f"evaluated transaction performance across {summary_metrics.get('period', 'the active reporting period')}.\n\n"
                    f"Key findings from deterministic data calculations and corporate governance documents indicate:\n"
                    f"{bullets_text}\n\n"
                    f"Critical Audit Note: These operational observations are verified against recorded transaction data. "
                    f"Management is advised to proceed with the prioritized recommendations below."
                )

            overall_confidence = "High" if len(pydantic_findings) >= 2 else "Medium"

            report = BusinessAnalysisReport(
                question=question,
                executive_summary=exec_summary,
                key_metrics=key_metrics,
                findings=pydantic_findings,
                hypotheses=pydantic_hypotheses,
                recommendations=recommendations,
                evidence=pydantic_evidence,
                charts=charts,
                limitations=limitations,
                confidence=overall_confidence,
            )

        duration = time.perf_counter() - start_time
        logger.info("ExecutiveReport completed in %.2fs", duration)
        return report

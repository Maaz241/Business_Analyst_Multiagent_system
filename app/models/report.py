"""
Domain Pydantic Models for Business Analysis Reports, Findings, and Evidence Provenance.
Ensures strict schema adherence across all agent outputs.
"""

from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Metric(BaseModel):
    """Business performance metric."""
    name: str = Field(description="Name of the metric (e.g., 'Q3 Revenue', 'AOV', 'Growth Rate')")
    value: str = Field(description="Formatted value (e.g., '£3.20M', '£245.50')")
    delta: Optional[str] = Field(default=None, description="Change vs prior period (e.g., '-15.8%', '+4.2%')")
    context: Optional[str] = Field(default=None, description="Contextual note or period")


class Evidence(BaseModel):
    """Evidence traceability unit."""
    id: str = Field(description="Unique evidence identifier (e.g., 'EV-01')")
    source: str = Field(description="Data file or document name (e.g., 'sales.csv', 'q3_management_notes.pdf')")
    source_type: Literal["data_calculation", "document_passage", "company_target"] = Field(
        description="Type of source backing the claim"
    )
    details: str = Field(description="Exact calculation output or quoted passage")
    page: Optional[int] = Field(default=None, description="Document page number if applicable")
    calculation: Optional[str] = Field(default=None, description="Name of deterministic tool used")


class Finding(BaseModel):
    """Atomic business finding with strict classification."""
    title: str = Field(description="Brief headline summarizing the finding")
    statement: str = Field(description="Comprehensive statement explaining the finding")
    metric: Optional[str] = Field(default=None, description="Associated metric name")
    value: Optional[str] = Field(default=None, description="Associated metric value")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of evidence supporting this finding")
    confidence: Literal["High", "Medium", "Low"] = Field(description="Confidence rating based on evidence sufficiency")
    classification: Literal["fact", "evidence", "hypothesis", "recommendation"] = Field(
        description="Clear distinction between facts and hypotheses"
    )


class Hypothesis(BaseModel):
    """Plausible explanation not proven by available data."""
    statement: str = Field(description="Hypothetical business explanation")
    supporting_evidence: List[str] = Field(default_factory=list, description="Document passages or trends suggesting this")
    confidence: Literal["High", "Medium", "Low"] = Field(default="Medium")
    alternative_explanations: List[str] = Field(default_factory=list, description="Alternative factors to consider")


class Recommendation(BaseModel):
    """Recommended next operational or analytical action."""
    action: str = Field(description="Actionable management step")
    priority: Literal["High", "Medium", "Low"] = Field(description="Urgency/Impact priority")
    owner: str = Field(description="Responsible stakeholder (e.g., 'Regional Sales Lead', 'Supply Chain')")
    rationale: str = Field(description="Reasoning backed by data findings")


class BusinessAnalysisReport(BaseModel):
    """The master executive deliverable contract."""
    question: str = Field(description="The user's original business question")
    executive_summary: str = Field(description="Synthesized high-level executive summary")
    key_metrics: List[Metric] = Field(default_factory=list, description="Primary KPI summary cards")
    findings: List[Finding] = Field(default_factory=list, description="Validated findings classified into facts/hypotheses")
    hypotheses: List[Hypothesis] = Field(default_factory=list, description="Potential explanations requiring investigation")
    recommendations: List[Recommendation] = Field(default_factory=list, description="Concrete management recommendations")
    evidence: List[Evidence] = Field(default_factory=list, description="Complete audit trail of all citations and calculations")
    charts: List[str] = Field(default_factory=list, description="Recommended chart types to display")
    limitations: List[str] = Field(default_factory=list, description="Data limitations, absent variables (COGS, etc.)")
    confidence: Literal["High", "Medium", "Low"] = Field(description="Overall report confidence")

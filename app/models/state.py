"""
LangGraph State Definitions for Multi-Agent Workflow.
Stores execution context, plans, tool outputs, critic feedback, and the trace.

Enhanced v2.0: Adds evidence chain tracking, summary_metrics, and hypotheses state.
"""

from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional


class AnalysisState(TypedDict, total=False):
    """The central state passed across LangGraph nodes."""
    user_question: str
    dataset_info: Dict[str, Any]
    plan: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    data_findings: List[Dict[str, Any]]
    rag_findings: List[Dict[str, Any]]
    research_findings: List[Dict[str, Any]]
    critic_findings: List[Dict[str, Any]]
    validated_findings: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    charts: List[str]
    recommendations: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    summary_metrics: Dict[str, Any]
    confidence: str
    limitations: List[str]
    agent_trace: List[Dict[str, Any]]
    iteration: int
    needs_replanning: bool
    replan_reason: Optional[str]
    final_report: Optional[Dict[str, Any]]

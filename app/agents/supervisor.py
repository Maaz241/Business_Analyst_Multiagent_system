"""
Supervisor Agent.
Orchestrates the multi-agent business analysis workflow.
Parses the user's business inquiry, devises an analytical execution plan,
delegates tasks to specialist agents, and coordinates validation cycles.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List, Optional
from app.config import MAX_REPLANS
from app.data.loader import DataLoader
from app.utils.logging import log_agent_step, logger


class SupervisorAgent:
    """Master workflow coordinator and planner."""

    def __init__(self):
        self.loader = DataLoader()

    def create_plan(self, question: str, iteration: int = 0, replan_reason: Optional[str] = None) -> List[Dict[str, Any]]:
        """Decompose business question into ordered analytical steps."""
        q_lower = question.lower()
        plan: List[Dict[str, Any]] = []

        with log_agent_step("Supervisor", "Formulate analysis plan", iteration=iteration):
            # Step 1: Baseline Quantitative Metrics
            plan.append({
                "step": 1,
                "agent": "DataAnalyst",
                "action": "calculate_baseline_metrics",
                "description": "Calculate total revenue, completed orders count, and AOV for relevant periods.",
            })

            # Step 2: Period-over-period comparison if trend/decline/growth question
            if any(term in q_lower for term in ["decline", "fall", "drop", "growth", "why", "quarter", "q3", "compare"]):
                plan.append({
                    "step": 2,
                    "agent": "DataAnalyst",
                    "action": "compare_periods",
                    "description": "Execute period-over-period comparison (e.g. Q2 vs Q3 2011) to isolate absolute and percentage changes.",
                })
                plan.append({
                    "step": 3,
                    "agent": "DataAnalyst",
                    "action": "dimensional_breakdown",
                    "description": "Break down revenue variances by country, product category, and customer segment.",
                })

            # Step 3: Document Retrieval (RAG)
            plan.append({
                "step": len(plan) + 1,
                "agent": "RAGAnalyst",
                "action": "retrieve_contextual_evidence",
                "description": "Search corporate knowledge documents, management memos, and strategic targets for concurrent operational events.",
            })

            # Step 4: Critical Audit
            plan.append({
                "step": len(plan) + 1,
                "agent": "Critic",
                "action": "validate_findings",
                "description": "Audit calculations, verify evidence attribution, and reject unsupported causal assertions (correlation vs causation).",
            })

            # Step 5: Executive Report Synthesis
            plan.append({
                "step": len(plan) + 1,
                "agent": "ExecutiveReport",
                "action": "synthesize_report",
                "description": "Compile validated findings, interactive charts, traceable evidence, and actionable recommendations.",
            })

            if replan_reason:
                logger.info("Supervisor adapted plan for iteration %d: %s", iteration, replan_reason)

        return plan

    def should_replan(self, needs_replanning: bool, current_iteration: int) -> bool:
        """Determine whether workflow should loop back for re-planning."""
        return needs_replanning and current_iteration < MAX_REPLANS

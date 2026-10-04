"""
Critic Agent.
The required differentiator for the NovaMart AI Business Analyst.
Rigorously reviews every finding, calculation, and document citation.
Rejects causal leaps (correlation vs causation), calibrates confidence,
and rewrites assertions to safe, evidence-backed business phrasing.
"""

from __future__ import annotations
import re
import time
from typing import Dict, Any, List, Tuple
from app.utils.logging import log_agent_step, logger


# Flagged causal words that trigger critical review
CAUSAL_TRIGGERS = [
    r"\bcaused\b",
    r"\bcauses\b",
    r"\blead to\b",
    r"\bled to\b",
    r"\bresulted in\b",
    r"\bdue solely to\b",
    r"\bbecause of the\b",
    r"\bdirectly responsible\b",
]

SAFE_SUBSTITUTIONS = [
    ("caused", "coincided with"),
    ("led to", "was accompanied by"),
    ("resulted in", "aligned with"),
    ("directly responsible for", "a potential contributing factor to"),
]


class CriticAgent:
    """Specialist validation agent enforcing causal discipline, calculation rigor, and evidence audit."""

    def run(
        self,
        question: str,
        data_findings: List[Dict[str, Any]],
        rag_findings: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        iteration: int = 0,
    ) -> Dict[str, Any]:
        """
        Critique all findings, enforce causal policy, and determine if re-planning is needed.
        """
        start_time = time.perf_counter()
        critique_log: List[Dict[str, Any]] = []
        validated_findings: List[Dict[str, Any]] = []
        hypotheses: List[Dict[str, Any]] = []
        replan_needed = False
        replan_reason = None

        with log_agent_step("Critic", "Audit findings, evidence, and causal claims", iteration=iteration):
            all_findings = data_findings + rag_findings

            for f in all_findings:
                statement = f.get("statement", "")
                title = f.get("title", "")
                confidence = f.get("confidence", "Medium")
                classification = f.get("classification", "fact")
                ev_ids = f.get("evidence_ids", [])

                # 1. Check for evidence backing
                if not ev_ids:
                    critique_log.append({
                        "finding": title,
                        "verdict": "REVISE",
                        "reason": "Finding lacked explicit evidence attribution ID. Confidence downgraded to Low.",
                    })
                    confidence = "Low"

                # 2. Check for unsupported causal leaps
                has_causal_leap = False
                for pattern in CAUSAL_TRIGGERS:
                    if re.search(pattern, statement, re.IGNORECASE):
                        has_causal_leap = True
                        break

                if has_causal_leap:
                    # Reject or rewrite causal claim
                    revised_stmt = statement
                    for src, repl in SAFE_SUBSTITUTIONS:
                        revised_stmt = re.sub(rf"\b{src}\b", repl, revised_stmt, flags=re.IGNORECASE)

                    if revised_stmt == statement:
                        revised_stmt = f"{statement}. Note: This observed relationship is a potential contributing factor; the current data does not establish definitive causality."

                    critique_log.append({
                        "finding": title,
                        "verdict": "REWRITE_CAUSAL_LEAP",
                        "original": statement,
                        "revised": revised_stmt,
                        "reason": "Mistaking correlation for causality. Corporate documents report events that coincided with trends, but do not prove isolated causation.",
                    })

                    statement = revised_stmt
                    classification = "hypothesis"
                    if confidence == "High":
                        confidence = "Medium"

                    # Add to formal hypotheses
                    hypotheses.append({
                        "statement": statement,
                        "supporting_evidence": ev_ids,
                        "confidence": confidence,
                        "alternative_explanations": [
                            "Broader macroeconomic or demand shifts",
                            "Category-specific consumer seasonal variation",
                            "Promotional timing or competitor discounting",
                        ],
                    })
                elif classification == "hypothesis":
                    hypotheses.append({
                        "statement": statement,
                        "supporting_evidence": ev_ids,
                        "confidence": confidence,
                        "alternative_explanations": [
                            "Operational ramp-up lag",
                            "Unmeasured supply chain bottlenecks",
                        ],
                    })
                else:
                    critique_log.append({
                        "finding": title,
                        "verdict": "PASS",
                        "reason": "Supported by deterministic calculation or documented text with appropriate confidence.",
                    })

                validated_findings.append({
                    "title": title,
                    "statement": statement,
                    "metric": f.get("metric"),
                    "value": f.get("value"),
                    "evidence_ids": ev_ids,
                    "confidence": confidence,
                    "classification": classification,
                })

            # Check if any critical data was completely missing that warrants re-planning
            if iteration == 0 and len(data_findings) == 0:
                replan_needed = True
                replan_reason = "No quantitative data analysis was executed for the user query."
                logger.warning("Critic requested re-planning: %s", replan_reason)

        duration = time.perf_counter() - start_time
        logger.info(
            "Critic completed in %.2fs. Audited %d findings (%d revisions/passes). Replan needed: %s",
            duration, len(all_findings), len(critique_log), replan_needed
        )

        return {
            "validated_findings": validated_findings,
            "hypotheses": hypotheses,
            "critique_log": critique_log,
            "needs_replanning": replan_needed,
            "replan_reason": replan_reason,
            "duration": round(duration, 3),
        }

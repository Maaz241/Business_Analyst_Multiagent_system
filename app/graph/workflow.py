"""
LangGraph Multi-Agent Orchestration Workflow.
Coordinates Supervisor, Data Analyst, RAG Analyst, Critic, and Executive Report agents.
Includes iterative validation loop with Critic feedback and MAX_REPLANS guardrail.
"""

from __future__ import annotations
import time
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END

from app.config import MAX_REPLANS
from app.graph.state import AnalysisState
from app.agents.supervisor import SupervisorAgent
from app.agents.data_analyst import DataAnalystAgent
from app.agents.rag_analyst import RAGAnalystAgent
from app.agents.critic import CriticAgent
from app.agents.executive_report import ExecutiveReportAgent
from app.utils.logging import AgentTraceEvent, logger


def _add_trace(state: AnalysisState, agent: str, action: str, summary: str, tool: str = "", duration: float = 0.0) -> list:
    trace = list(state.get("agent_trace", []))
    event = AgentTraceEvent(
        agent=agent,
        action=action,
        status="completed",
        tool=tool,
        duration=duration,
        summary=summary,
        iteration=state.get("iteration", 0),
    )
    trace.append(event.to_dict())
    return trace


def supervisor_node(state: AnalysisState) -> Dict[str, Any]:
    """Supervisor parses question, generates or updates analysis plan."""
    start = time.perf_counter()
    question = state["user_question"]
    iteration = state.get("iteration", 0)
    replan_reason = state.get("replan_reason")

    agent = SupervisorAgent()
    plan = agent.create_plan(question, iteration=iteration, replan_reason=replan_reason)
    duration = time.perf_counter() - start

    action_label = "revised_plan" if iteration > 0 else "created_plan"
    summary_text = f"Formulated {len(plan)}-step plan for inquiry." if iteration == 0 else f"Re-planned based on Critic review: {replan_reason}"
    trace = _add_trace(state, "Supervisor", action_label, summary_text, duration=duration)

    return {
        "plan": plan,
        "iteration": iteration + 1,
        "needs_replanning": False,
        "replan_reason": None,
        "agent_trace": trace,
    }


def data_analyst_node(state: AnalysisState) -> Dict[str, Any]:
    """Data Analyst executes deterministic Pandas operations."""
    start = time.perf_counter()
    question = state["user_question"]
    plan = state.get("plan", [])
    iteration = state.get("iteration", 0)

    agent = DataAnalystAgent()
    res = agent.run(question, plan_tasks=plan, iteration=iteration)
    duration = time.perf_counter() - start

    trace = _add_trace(
        state,
        "Data Analyst",
        "executed_analytics",
        f"Executed {len(res['tool_results'])} analytical tools, identified {len(res['findings'])} quantitative facts.",
        tool="Pandas Analytics",
        duration=duration,
    )

    # Combine existing evidence with new findings
    existing_ev = list(state.get("evidence", []))
    existing_ev.extend(res.get("evidence", []))

    return {
        "data_findings": res.get("findings", []),
        "tool_results": res.get("tool_results", []),
        "citations": state.get("citations", []),
        "charts": res.get("charts", ["revenue_trend"]),
        "summary_metrics": res.get("summary_metrics", {}),
        "evidence": existing_ev,
        "agent_trace": trace,
    }


def rag_analyst_node(state: AnalysisState) -> Dict[str, Any]:
    """RAG Analyst searches internal company knowledge for contextual evidence."""
    start = time.perf_counter()
    question = state["user_question"]
    plan = state.get("plan", [])
    iteration = state.get("iteration", 0)

    agent = RAGAnalystAgent()
    res = agent.run(question, plan_tasks=plan, iteration=iteration)
    duration = time.perf_counter() - start

    trace = _add_trace(
        state,
        "RAG Agent",
        "retrieved_documents",
        f"Retrieved {len(res['citations'])} corporate document citations from ChromaDB knowledge base.",
        tool="ChromaDB Semantic Search",
        duration=duration,
    )

    combined_ev = list(state.get("evidence", []))
    combined_ev.extend(res["evidence"])

    return {
        "rag_findings": res["findings"],
        "citations": res["citations"],
        "evidence": combined_ev,
        "agent_trace": trace,
    }


def critic_node(state: AnalysisState) -> Dict[str, Any]:
    """Critic validates all claims, checks calculations, and rejects causal leaps."""
    start = time.perf_counter()
    question = state["user_question"]
    data_findings = state.get("data_findings", [])
    rag_findings = state.get("rag_findings", [])
    evidence = state.get("evidence", [])
    iteration = state.get("iteration", 0)

    agent = CriticAgent()
    critique = agent.run(
        question=question,
        data_findings=data_findings,
        rag_findings=rag_findings,
        evidence=evidence,
        iteration=iteration,
    )
    duration = time.perf_counter() - start

    rejections = [c for c in critique["critique_log"] if c["verdict"] != "PASS"]
    if rejections:
        summary_text = f"Critic reviewed findings: {len(rejections)} claim(s) rewritten to distinguish correlation from causation."
    else:
        summary_text = f"Critic passed all {len(critique['validated_findings'])} findings with validated evidence attribution."

    trace = _add_trace(
        state,
        "Critic",
        "validated_claims",
        summary_text,
        duration=duration,
    )

    return {
        "validated_findings": critique["validated_findings"],
        "hypotheses": critique["hypotheses"],
        "critic_findings": critique["critique_log"],
        "needs_replanning": critique["needs_replanning"],
        "replan_reason": critique["replan_reason"],
        "agent_trace": trace,
    }


def executive_report_node(state: AnalysisState) -> Dict[str, Any]:
    """Executive Report Agent produces the final structured report."""
    start = time.perf_counter()
    question = state["user_question"]
    val_findings = state.get("validated_findings", [])
    hypotheses = state.get("hypotheses", [])
    evidence = state.get("evidence", [])
    metrics = state.get("summary_metrics", {})
    charts = state.get("charts", [])
    iteration = state.get("iteration", 0)

    agent = ExecutiveReportAgent()
    report = agent.run(
        question=question,
        validated_findings=val_findings,
        hypotheses=hypotheses,
        evidence=evidence,
        summary_metrics=metrics,
        charts=charts,
        iteration=iteration,
    )
    duration = time.perf_counter() - start

    trace = _add_trace(
        state,
        "Executive Agent",
        "generated_report",
        f"Produced comprehensive executive report ({len(report.findings)} findings, {len(report.recommendations)} recommendations).",
        duration=duration,
    )

    return {
        "final_report": report.model_dump(),
        "agent_trace": trace,
    }


def should_replan_edge(state: AnalysisState) -> Literal["supervisor", "executive_report"]:
    """Conditional router: loop back to supervisor if Critic demands re-planning, else finish."""
    needs_replanning = state.get("needs_replanning", False)
    iteration = state.get("iteration", 0)

    if needs_replanning and iteration < MAX_REPLANS:
        logger.info("Critic requested re-planning -> routing to Supervisor (iteration %d)", iteration)
        return "supervisor"
    return "executive_report"


def build_analysis_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph multi-agent workflow."""
    workflow = StateGraph(AnalysisState)

    # Add agent nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("data_analyst", data_analyst_node)
    workflow.add_node("rag_analyst", rag_analyst_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("executive_report", executive_report_node)

    # Connect nodes
    workflow.add_edge(START, "supervisor")
    workflow.add_edge("supervisor", "data_analyst")
    workflow.add_edge("data_analyst", "rag_analyst")
    workflow.add_edge("rag_analyst", "critic")

    # Conditional validation edge
    workflow.add_conditional_edges(
        "critic",
        should_replan_edge,
        {
            "supervisor": "supervisor",
            "executive_report": "executive_report",
        },
    )

    workflow.add_edge("executive_report", END)

    return workflow.compile()


class BusinessAnalysisWorkflow:
    """High-level runner for the compiled LangGraph workflow."""

    def __init__(self):
        self.app = build_analysis_graph()

    def run(self, question: str) -> Dict[str, Any]:
        """Execute end-to-end multi-agent analysis on a business inquiry."""
        initial_state: AnalysisState = {
            "user_question": question,
            "dataset_info": {},
            "plan": [],
            "tool_results": [],
            "data_findings": [],
            "rag_findings": [],
            "research_findings": [],
            "critic_findings": [],
            "validated_findings": [],
            "hypotheses": [],
            "charts": [],
            "recommendations": [],
            "citations": [],
            "evidence": [],
            "summary_metrics": {},
            "confidence": "High",
            "limitations": [],
            "agent_trace": [],
            "iteration": 0,
            "needs_replanning": False,
            "replan_reason": None,
            "final_report": None,
        }

        logger.info("Starting LangGraph workflow for question: '%s'", question)
        final_state = self.app.invoke(initial_state)
        logger.info("LangGraph workflow finished with %d trace steps.", len(final_state.get("agent_trace", [])))
        return final_state

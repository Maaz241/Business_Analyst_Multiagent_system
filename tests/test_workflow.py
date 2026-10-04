"""
Multi-Agent Workflow Test Suite for NovaMart.
Validates individual agent behavior, Critic validation/re-planning,
and end-to-end LangGraph execution.
"""

import pytest
from app.agents.supervisor import SupervisorAgent
from app.agents.data_analyst import DataAnalystAgent
from app.agents.rag_analyst import RAGAnalystAgent
from app.agents.critic import CriticAgent
from app.agents.executive_report import ExecutiveReportAgent
from app.graph.workflow import BusinessAnalysisWorkflow, build_analysis_graph
from app.config import MAX_REPLANS


def test_supervisor_planning():
    """Verify Supervisor produces structured analytical plans."""
    supervisor = SupervisorAgent()
    plan = supervisor.create_plan("Why did Q3 revenue decline?")
    assert len(plan) >= 4
    agent_names = [step["agent"] for step in plan]
    assert "DataAnalyst" in agent_names
    assert "Critic" in agent_names
    assert "ExecutiveReport" in agent_names


def test_data_agent_execution():
    """Verify Data Analyst generates quantitative findings with evidence attribution."""
    agent = DataAnalystAgent()
    res = agent.run("Why did Q3 revenue decline?", plan_tasks=[])
    assert "findings" in res
    assert "tool_results" in res
    assert "evidence" in res
    assert len(res["findings"]) > 0


def test_critic_rejects_causal_leap():
    """Verify Critic flags and rewrites unproven causal assertions."""
    critic = CriticAgent()
    flawed_findings = [{
        "title": "Distributor Impact",
        "statement": "The distributor transition caused the APAC revenue decline.",
        "evidence_ids": ["EV-01"],
        "confidence": "High",
        "classification": "fact",
    }]

    critique = critic.run(
        question="Why did APAC decline?",
        data_findings=flawed_findings,
        rag_findings=[],
        evidence=[{"id": "EV-01", "source": "q3_management_notes.pdf", "details": "Transition occurred in Q3"}],
    )

    rejections = [c for c in critique["critique_log"] if c["verdict"] == "REWRITE_CAUSAL_LEAP"]
    assert len(rejections) == 1
    # Check that causal language was rewritten
    revised = critique["validated_findings"][0]["statement"]
    assert "caused" not in revised.lower()
    assert "coincided with" in revised.lower()


def test_critic_demands_replan_when_data_missing():
    """Verify Critic requests re-planning if no quantitative data was produced."""
    critic = CriticAgent()
    critique = critic.run(
        question="What was Q3 revenue?",
        data_findings=[],
        rag_findings=[],
        evidence=[],
        iteration=0,
    )
    assert critique["needs_replanning"] is True
    assert critique["replan_reason"] is not None


def test_final_report_generation():
    """Verify Executive Report Agent produces valid BusinessAnalysisReport contract."""
    exec_agent = ExecutiveReportAgent()
    report = exec_agent.run(
        question="Why did Q3 revenue decline?",
        validated_findings=[{
            "title": "Quarterly Decline",
            "statement": "Revenue declined 15.8% in Q3.",
            "evidence_ids": ["EV-01"],
            "confidence": "High",
            "classification": "fact",
        }],
        hypotheses=[],
        evidence=[{
            "id": "EV-01",
            "source": "sales.csv",
            "source_type": "data_calculation",
            "details": "compare_periods: Q2 vs Q3",
        }],
        summary_metrics={"revenue": "£3.20M", "growth": "-15.8%", "orders": "40,000", "aov": "£80.00"},
        charts=["revenue_trend", "period_comparison"],
    )

    assert report.question == "Why did Q3 revenue decline?"
    assert len(report.key_metrics) == 4
    assert len(report.recommendations) > 0
    assert len(report.limitations) > 0
    assert report.confidence in ["High", "Medium", "Low"]


def test_end_to_end_workflow():
    """Verify complete LangGraph workflow execution on the flagship question."""
    workflow = BusinessAnalysisWorkflow()
    result = workflow.run("Why did Q3 revenue decline?")

    assert "final_report" in result
    assert result["final_report"] is not None
    assert "agent_trace" in result
    assert len(result["agent_trace"]) >= 4

    # Ensure max replan guardrail is respected
    assert result.get("iteration", 0) <= MAX_REPLANS + 1

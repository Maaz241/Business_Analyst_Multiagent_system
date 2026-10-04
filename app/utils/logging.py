"""
Structured, human-readable logging utility for multi-agent workflows.
Safe: Never logs API keys, tokens, or PII.
"""

from __future__ import annotations
import logging
import sys
import time
from typing import Any, Optional
from contextlib import contextmanager

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("NovaMartAI")


def get_agent_logger(agent_name: str) -> logging.Logger:
    """Return a scoped logger for an individual agent."""
    return logging.getLogger(f"NovaMart.{agent_name}")


class AgentTraceEvent:
    """Structured representation of an agent trace event."""
    def __init__(
        self,
        agent: str,
        action: str,
        status: str = "running",
        tool: Optional[str] = None,
        duration: Optional[float] = None,
        summary: Optional[str] = None,
        details: Optional[Any] = None,
        iteration: int = 0,
    ):
        self.timestamp = time.strftime("%H:%M:%S")
        self.agent = agent
        self.action = action
        self.status = status
        self.tool = tool
        self.duration = duration
        self.summary = summary or ""
        self.details = details
        self.iteration = iteration

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "action": self.action,
            "status": self.status,
            "tool": self.tool,
            "duration": round(self.duration, 3) if self.duration is not None else None,
            "summary": self.summary,
            "iteration": self.iteration,
        }

    def __repr__(self) -> str:
        dur_str = f" ({self.duration:.2f}s)" if self.duration is not None else ""
        tool_str = f" [{self.tool}]" if self.tool else ""
        return f"[{self.timestamp}] {self.agent}{tool_str} -> {self.action} ({self.status}){dur_str}: {self.summary}"


@contextmanager
def log_agent_step(agent_name: str, action: str, tool: Optional[str] = None, iteration: int = 0):
    """Context manager to log and time agent or tool steps."""
    start_time = time.perf_counter()
    sub_logger = get_agent_logger(agent_name)
    sub_logger.info("START: %s | tool=%s | iter=%d", action, tool or "none", iteration)
    try:
        yield
        duration = time.perf_counter() - start_time
        sub_logger.info("COMPLETED: %s | tool=%s | duration=%.2fs", action, tool or "none", duration)
    except Exception as e:
        duration = time.perf_counter() - start_time
        sub_logger.error("FAILED: %s | tool=%s | error=%s | duration=%.2fs", action, tool or "none", str(e), duration)
        raise

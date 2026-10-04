"""
Formatting helpers for business metrics, currency, percentages, and display text.
"""

from __future__ import annotations
from typing import Any, Union


def format_currency(value: Union[int, float], currency_symbol: str = "£") -> str:
    """Format numeric value into readable currency with M, K, or full numbers."""
    if value is None:
        return "N/A"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return str(value)

    abs_val = abs(val)
    sign = "-" if val < 0 else ""

    if abs_val >= 1_000_000_000:
        return f"{sign}{currency_symbol}{abs_val / 1_000_000_000:.2f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}{currency_symbol}{abs_val / 1_000_000:.2f}M"
    elif abs_val >= 1_000:
        return f"{sign}{currency_symbol}{abs_val / 1_000:.2f}K"
    else:
        return f"{sign}{currency_symbol}{abs_val:,.2f}"


def format_percent(value: Union[int, float], include_sign: bool = True) -> str:
    """Format decimal or percentage into readable % string (e.g., +15.8% or -24.0%)."""
    if value is None:
        return "N/A"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return str(value)

    # If value is in decimal format (e.g. 0.158 instead of 15.8), handle appropriately if needed.
    # By convention, if abs(val) <= 1.0 and non-zero, it could be decimal, but we expect standard 100-based percentage.
    sign = "+" if val > 0 and include_sign else ""
    return f"{sign}{val:.1f}%"


def format_number(value: Union[int, float]) -> str:
    """Format integers or counts with thousands commas."""
    if value is None:
        return "N/A"
    try:
        val = float(value)
        if val.is_integer():
            return f"{int(val):,}"
        return f"{val:,.2f}"
    except (ValueError, TypeError):
        return str(value)


def sanitize_text(text: str) -> str:
    """Sanitize arbitrary user or document text for display."""
    if not text:
        return ""
    # Strip dangerous controls or excessive blank space
    return text.strip()

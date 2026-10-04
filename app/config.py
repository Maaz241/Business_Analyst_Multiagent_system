"""
Application configuration for NovaMart AI Business Analyst.
Supports loading from environment variables or Streamlit secrets with sensible defaults.
"""

from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = ROOT_DIR / "app"
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
KNOWLEDGE_DIR = ROOT_DIR / "knowledge"
CHROMA_DIR = ROOT_DIR / "chroma_db"

# Ensure runtime directories exist
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)


def get_secret(key: str, default: str = "") -> str:
    """Retrieve secret from Streamlit secrets or OS environment."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


# General App Config
APP_NAME: str = get_secret("APP_NAME", "NovaMart AI Business Analyst")
APP_VERSION: str = "2.0.0"

# Gemini Model Settings
GEMINI_API_KEY: str = get_secret("GEMINI_API_KEY", "")
GEMINI_MODEL: str = get_secret("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_FALLBACK_MODEL: str = get_secret("GEMINI_FALLBACK_MODEL", "gemini-flash-latest")
GEMINI_EMBEDDING_MODEL: str = get_secret("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

# Agent & Workflow Limits
MAX_AGENT_STEPS: int = int(get_secret("MAX_AGENT_STEPS", "12"))
MAX_REPLANS: int = int(get_secret("MAX_REPLANS", "2"))
RAG_TOP_K: int = int(get_secret("RAG_TOP_K", "5"))
MAX_UPLOAD_MB: int = int(get_secret("MAX_UPLOAD_MB", "50"))
MAX_DOCUMENT_CHARS_PER_RESULT: int = int(get_secret("MAX_DOCUMENT_CHARS_PER_RESULT", "6000"))
MAX_TOOL_RESULT_ROWS: int = int(get_secret("MAX_TOOL_RESULT_ROWS", "100"))

# Default demo data file paths
DEFAULT_SALES_FILE = PROCESSED_DATA_DIR / "sales.csv"
DEFAULT_CUSTOMERS_FILE = PROCESSED_DATA_DIR / "customers.csv"
DEFAULT_PRODUCTS_FILE = PROCESSED_DATA_DIR / "products.csv"
DEFAULT_TARGETS_FILE = PROCESSED_DATA_DIR / "targets.csv"
DEFAULT_RAW_FILE = RAW_DATA_DIR / "online_retail_II.xlsx"

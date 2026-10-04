"""
Demo Documents Verification and Generator Script for NovaMart.
Validates the presence of the 8 required knowledge documents in knowledge/.
"""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import KNOWLEDGE_DIR

EXPECTED_DOCS = [
    "company_profile.pdf",
    "kpi_definitions.pdf",
    "management_targets.pdf",
    "pricing_policy.pdf",
    "regional_strategy.pdf",
    "product_strategy.pdf",
    "q3_management_notes.pdf",
    "Business_glossary.pdf",
]


def main():
    print("==================================================")
    print("      NovaMart Knowledge Documents Verifier      ")
    print("==================================================\n")

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    all_present = True

    print(f"Checking directory: {KNOWLEDGE_DIR}...")
    for doc in EXPECTED_DOCS:
        doc_path = KNOWLEDGE_DIR / doc
        if doc_path.exists() and doc_path.stat().st_size > 0:
            print(f"  [OK] {doc} ({doc_path.stat().st_size:,} bytes)")
        else:
            print(f"  [MISSING] {doc}")
            all_present = False

    print("--------------------------------------------------")
    if all_present:
        print("[SUCCESS] All 8 required knowledge documents are present and ready!")
    else:
        print("[WARNING] One or more knowledge documents are missing.")
    print("--------------------------------------------------\n")


if __name__ == "__main__":
    main()

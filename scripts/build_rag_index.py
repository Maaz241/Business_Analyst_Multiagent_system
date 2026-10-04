"""
CLI script to build or rebuild the RAG knowledge index from knowledge/ directory.

Usage:
    python scripts/build_rag_index.py [--force]
"""

import sys
import argparse
from pathlib import Path

# Ensure standard UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import KNOWLEDGE_DIR
from app.rag.ingestion import DocumentIngestionPipeline
from app.rag.vector_store import get_vector_store


def main():
    parser = argparse.ArgumentParser(description="Build NovaMart RAG knowledge index.")
    parser.add_argument("--force", action="store_true", help="Force complete rebuild of the vector index.")
    args = parser.parse_args()

    print("==================================================")
    print("       NovaMart RAG Knowledge Index Builder       ")
    print("==================================================\n")

    if not KNOWLEDGE_DIR.exists():
        print(f"Error: Knowledge directory not found at: {KNOWLEDGE_DIR}")
        sys.exit(1)

    print(f"Scanning knowledge directory: {KNOWLEDGE_DIR}...")
    pipeline = DocumentIngestionPipeline()
    chunks = pipeline.ingest_directory(KNOWLEDGE_DIR)

    if not chunks:
        print("Error: No valid document chunks were extracted.")
        sys.exit(1)

    docs_summary = {}
    for c in chunks:
        docs_summary[c.source_file] = docs_summary.get(c.source_file, 0) + 1

    print("\n--- Extracted Knowledge Documents ---")
    for doc_name, count in sorted(docs_summary.items()):
        print(f"  {doc_name:<30} : {count} chunks")
    print("-------------------------------------")
    print(f"Total Chunks Extracted: {len(chunks)}\n")

    print(f"Generating embeddings and building vector store index (force={args.force})...")
    vector_store = get_vector_store()
    vector_store.build_index(chunks, force_rebuild=args.force)

    total_count = vector_store.get_document_count()
    print(f"\n[SUCCESS] Vector index built successfully! Total indexed chunks: {total_count}\n")


if __name__ == "__main__":
    main()

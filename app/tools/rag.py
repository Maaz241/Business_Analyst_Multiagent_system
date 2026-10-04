"""
RAG and Business Knowledge Search Tools.
Provides structured query access to internal NovaMart policies, notes, and strategies.
Includes prompt-injection wrapping and precise citation attribution.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from app.rag.vector_store import get_vector_store
from app.config import RAG_TOP_K, MAX_DOCUMENT_CHARS_PER_RESULT
from app.utils.security import wrap_untrusted_context
from app.utils.logging import logger


def search_company_knowledge(
    query: str,
    top_k: int = RAG_TOP_K,
    source_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search NovaMart's internal documents for policies, strategy notes, and operational context.

    Args:
        query: Natural language query (e.g., 'APAC distributor transition', 'Q3 electronics inventory').
        top_k: Number of relevant passages to retrieve (default 5).
        source_filter: Optional specific document name (e.g., 'q3_management_notes.pdf').

    Returns:
        Structured dictionary with matched passages, source metadata, and citation references.
    """
    vector_store = get_vector_store()

    # Rebuild on the fly if unindexed (Section 20: Free deployment auto-rebuild)
    if not vector_store.is_indexed():
        logger.info("Vector store index is missing or empty. Auto-indexing knowledge documents...")
        from app.rag.ingestion import DocumentIngestionPipeline
        ingestion = DocumentIngestionPipeline()
        chunks = ingestion.ingest_directory()
        vector_store.build_index(chunks)

    raw_results = vector_store.search(query=query, top_k=top_k, source_filter=source_filter)

    if not raw_results:
        return {
            "status": "not_found",
            "query": query,
            "message": "No supporting company document was found for this query.",
            "citations": [],
            "count": 0,
        }

    citations = []
    total_chars = 0

    for res in raw_results:
        text = res["content_excerpt"]
        if len(text) > 1500:
            text = text[:1500] + "..."

        if total_chars + len(text) > MAX_DOCUMENT_CHARS_PER_RESULT:
            break

        total_chars += len(text)
        citations.append({
            "source_file": res["source_file"],
            "page": res["page"],
            "chunk_id": res["chunk_id"],
            "relevance_score": res["relevance_score"],
            "document_type": res["document_type"],
            "content": wrap_untrusted_context(text, res["source_file"]),
            "raw_text": text,
        })

    logger.info("RAG search for '%s' returned %d citations", query, len(citations))
    return {
        "status": "success",
        "query": query,
        "count": len(citations),
        "citations": citations,
    }

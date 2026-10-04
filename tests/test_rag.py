"""
RAG and Vector Search Test Suite for NovaMart.
Validates document ingestion, chunking, semantic retrieval, and metadata attribution.
"""

import pytest
from pathlib import Path
from app.config import KNOWLEDGE_DIR
from app.rag.ingestion import DocumentIngestionPipeline, DocumentChunk
from app.rag.embeddings import GeminiEmbeddings
from app.rag.vector_store import get_vector_store
from app.tools.rag import search_company_knowledge


def test_document_ingestion():
    """Verify document chunking extracts text and metadata from PDF files."""
    pipeline = DocumentIngestionPipeline(chunk_size=500, chunk_overlap=50)
    pdf_path = KNOWLEDGE_DIR / "q3_management_notes.pdf"
    assert pdf_path.exists(), "q3_management_notes.pdf must exist in knowledge/"

    chunks = pipeline.ingest_file(pdf_path)
    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert isinstance(first_chunk, DocumentChunk)
    assert first_chunk.source_file == "q3_management_notes.pdf"
    assert first_chunk.page >= 1
    assert len(first_chunk.text) > 0


def test_embedding_creation():
    """Verify embedding function generates valid vector outputs."""
    embedder = GeminiEmbeddings()
    sample_texts = ["NovaMart quarterly sales report", "APAC distributor transition note"]
    vectors = embedder.embed_documents(sample_texts)

    assert len(vectors) == 2
    assert len(vectors[0]) > 0
    assert isinstance(vectors[0][0], float)


def test_retrieval():
    """Verify semantic search retrieves relevant chunks for business queries."""
    res = search_company_knowledge(query="distributor transition in APAC", top_k=3)
    assert res["status"] == "success"
    assert res["count"] > 0
    assert len(res["citations"]) > 0


def test_source_metadata():
    """Verify all returned citations contain mandatory audit metadata."""
    res = search_company_knowledge(query="electronics inventory constraints", top_k=3)
    assert res["status"] == "success"

    for cit in res["citations"]:
        assert "source_file" in cit
        assert "page" in cit
        assert "chunk_id" in cit
        assert "relevance_score" in cit
        assert "content" in cit
        assert cit["source_file"].endswith((".pdf", ".docx", ".txt"))

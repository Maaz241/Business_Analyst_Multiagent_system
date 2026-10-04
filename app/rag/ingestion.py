"""
Document Ingestion Pipeline for NovaMart RAG Knowledge Base.
Extracts text from PDF, DOCX, and TXT files, chunks with metadata,
and applies prompt injection sanitization.
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import KNOWLEDGE_DIR
from app.utils.security import sanitize_document_text
from app.utils.logging import logger


class DocumentChunk:
    """Represents a chunk of corporate document text with full provenance."""
    def __init__(
        self,
        chunk_id: str,
        text: str,
        source_file: str,
        page: int,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.source_file = source_file
        self.page = page
        self.document_type = document_type
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "page": self.page,
            "document_type": self.document_type,
            "uploaded_at": self.metadata.get("uploaded_at", time.strftime("%Y-%m-%d %H:%M:%S")),
        }


class DocumentIngestionPipeline:
    """Extracts, cleans, and chunks corporate documents for vector indexing."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def extract_from_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract text page by page from PDF."""
        pages = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                sanitized = sanitize_document_text(text)
                if sanitized.strip():
                    pages.append({"page": idx + 1, "text": sanitized})
        except Exception as e:
            logger.error("Error reading PDF %s: %s", file_path.name, e)
        return pages

    def extract_from_docx(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract text from DOCX document."""
        pages = []
        try:
            doc = docx.Document(str(file_path))
            full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            sanitized = sanitize_document_text(full_text)
            if sanitized.strip():
                pages.append({"page": 1, "text": sanitized})
        except Exception as e:
            logger.error("Error reading DOCX %s: %s", file_path.name, e)
        return pages

    def extract_from_txt(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract text from plain text file."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            sanitized = sanitize_document_text(text)
            return [{"page": 1, "text": sanitized}]
        except Exception as e:
            logger.error("Error reading TXT %s: %s", file_path.name, e)
            return []

    def ingest_file(self, file_path: Path) -> List[DocumentChunk]:
        """Process a single document file into chunked objects with metadata."""
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            pages_data = self.extract_from_pdf(file_path)
            doc_type = "PDF Policy/Report"
        elif ext in [".docx", ".doc"]:
            pages_data = self.extract_from_docx(file_path)
            doc_type = "Word Strategy Document"
        elif ext == ".txt":
            pages_data = self.extract_from_txt(file_path)
            doc_type = "Text Note"
        else:
            logger.warning("Unsupported document format: %s", ext)
            return []

        chunks: List[DocumentChunk] = []
        doc_name = file_path.name

        for p_info in pages_data:
            page_num = p_info["page"]
            page_text = p_info["text"]
            splits = self.splitter.split_text(page_text)

            for s_idx, split_text in enumerate(splits):
                chunk_id = f"{file_path.stem}_p{page_num}_c{s_idx + 1}"
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    text=split_text,
                    source_file=doc_name,
                    page=page_num,
                    document_type=doc_type,
                    metadata={"uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S")},
                )
                chunks.append(chunk)

        logger.info("Ingested %s: %d pages -> %d chunks", doc_name, len(pages_data), len(chunks))
        return chunks

    def ingest_directory(self, dir_path: Optional[Path] = None) -> List[DocumentChunk]:
        """Ingest all knowledge documents in the knowledge directory."""
        directory = dir_path or KNOWLEDGE_DIR
        all_chunks: List[DocumentChunk] = []

        if not directory.exists():
            logger.warning("Knowledge directory does not exist: %s", directory)
            return all_chunks

        for file_path in sorted(directory.iterdir()):
            if file_path.suffix.lower() in [".pdf", ".docx", ".txt"]:
                all_chunks.extend(self.ingest_file(file_path))

        logger.info("Total knowledge chunks ingested from %s: %d", directory.name, len(all_chunks))
        return all_chunks

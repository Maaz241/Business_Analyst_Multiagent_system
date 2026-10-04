"""
Vector Store Management for NovaMart RAG.
Supports ChromaDB with fallback to fast in-memory cosine vector store.
Complies with zero-cost rebuildable requirement for ephemeral deployment.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from app.config import CHROMA_DIR, RAG_TOP_K
from app.rag.ingestion import DocumentChunk, DocumentIngestionPipeline
from app.rag.embeddings import GeminiEmbeddings
from app.utils.logging import logger


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pure NumPy cosine similarity with zero native C-extension dependencies."""
    norm_a = np.linalg.norm(a, axis=1, keepdims=True)
    norm_b = np.linalg.norm(b, axis=1, keepdims=True)
    norm_a = np.where(norm_a == 0, 1e-9, norm_a)
    norm_b = np.where(norm_b == 0, 1e-9, norm_b)
    return np.dot(a / norm_a, (b / norm_b).T)

# Safety patch for Windows AppLocker environments where grpc DLL is blocked
for mod in ["grpc", "grpc._cython", "grpc._cython.cygrpc",
            "opentelemetry.exporter.otlp.proto.grpc",
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"]:
    if mod not in sys.modules:
        from unittest.mock import MagicMock
        sys.modules[mod] = MagicMock()


class MemoryVectorStore:
    """Fast, zero-dependency in-memory vector store using cosine similarity."""

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.embeddings: np.ndarray = np.empty((0, 768))

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        if not chunks:
            return
        self.chunks.extend(chunks)
        target_dim = 768
        clean_embeddings = []
        for vec in embeddings:
            if not isinstance(vec, (list, np.ndarray)) or len(vec) == 0:
                clean_embeddings.append([0.0] * target_dim)
            elif len(vec) > target_dim:
                clean_embeddings.append(list(vec[:target_dim]))
            elif len(vec) < target_dim:
                clean_embeddings.append(list(vec) + [0.0] * (target_dim - len(vec)))
            else:
                clean_embeddings.append(list(vec))

        new_vecs = np.array(clean_embeddings, dtype=np.float32)
        if self.embeddings.size == 0:
            self.embeddings = new_vecs
        else:
            self.embeddings = np.vstack([self.embeddings, new_vecs])

    def similarity_search(self, query_vec: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.chunks or self.embeddings.size == 0:
            return []

        q_arr = np.array([query_vec], dtype=np.float32)
        scores = cosine_similarity(q_arr, self.embeddings)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            score = float(scores[idx])
            results.append({
                "chunk_id": chunk.chunk_id,
                "source_file": chunk.source_file,
                "page": chunk.page,
                "document_type": chunk.document_type,
                "relevance_score": round(score, 4),
                "content_excerpt": chunk.text,
            })
        return results


class VectorStoreManager:
    """Manages creation, indexing, and querying of internal knowledge chunks."""

    COLLECTION_NAME = "novamart_knowledge"

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or CHROMA_DIR
        self.embeddings = GeminiEmbeddings()
        self.memory_store = MemoryVectorStore()
        self.chroma_client = None
        self.collection = None
        self._init_chroma()

    def _init_chroma(self):
        """Attempt to initialize ChromaDB; fallback to memory store if unavailable."""
        try:
            import chromadb
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB initialized with collection '%s'", self.COLLECTION_NAME)
        except Exception as e:
            logger.warning("Could not initialize persistent ChromaDB (%s). Using high-speed in-memory store.", e)
            self.chroma_client = None
            self.collection = None

    def is_indexed(self) -> bool:
        """Check if vector store contains documents."""
        if self.collection is not None:
            try:
                count = self.collection.count()
                return count > 0
            except Exception:
                pass
        return len(self.memory_store.chunks) > 0

    def get_document_count(self) -> int:
        """Return number of indexed chunks."""
        if self.collection is not None:
            try:
                return self.collection.count()
            except Exception:
                pass
        return len(self.memory_store.chunks)

    def build_index(self, chunks: List[DocumentChunk], force_rebuild: bool = False):
        """Build or rebuild vector index from a list of DocumentChunks."""
        if not chunks:
            logger.warning("No chunks provided to build_index.")
            return

        logger.info("Building vector index for %d chunks...", len(chunks))

        texts = [c.text for c in chunks]
        embed_vecs = self.embeddings.embed_documents(texts)

        # 1. Update in-memory store
        self.memory_store = MemoryVectorStore()
        self.memory_store.add_chunks(chunks, embed_vecs)

        # 2. Update ChromaDB if active
        if self.chroma_client is not None:
            try:
                if force_rebuild:
                    try:
                        self.chroma_client.delete_collection(self.COLLECTION_NAME)
                    except Exception:
                        pass
                    self.collection = self.chroma_client.create_collection(
                        name=self.COLLECTION_NAME,
                        metadata={"hnsw:space": "cosine"}
                    )

                ids = [c.chunk_id for c in chunks]
                metadatas = [
                    {
                        "source_file": c.source_file,
                        "page": c.page,
                        "document_type": c.document_type,
                    }
                    for c in chunks
                ]

                # Chroma add in batches of 100
                batch_size = 100
                for i in range(0, len(chunks), batch_size):
                    end = i + batch_size
                    self.collection.add(
                        ids=ids[i:end],
                        embeddings=embed_vecs[i:end],
                        documents=texts[i:end],
                        metadatas=metadatas[i:end],
                    )
                logger.info("Successfully added %d chunks to ChromaDB collection.", len(chunks))
            except Exception as e:
                logger.warning("Error populating ChromaDB (%s). In-memory fallback will handle queries.", e)

    def add_chunks(self, chunks: List[DocumentChunk]):
        """Add new document chunks to the existing vector index without wiping existing documents."""
        if not chunks:
            return
        texts = [c.text for c in chunks]
        embed_vecs = self.embeddings.embed_documents(texts)
        self.memory_store.add_chunks(chunks, embed_vecs)
        if self.collection is not None:
            try:
                ids = [c.chunk_id for c in chunks]
                metadatas = [
                    {
                        "source_file": c.source_file,
                        "page": c.page,
                        "document_type": c.document_type,
                    }
                    for c in chunks
                ]
                self.collection.add(
                    ids=ids,
                    embeddings=embed_vecs,
                    documents=texts,
                    metadatas=metadatas,
                )
                logger.info("Successfully appended %d chunks to ChromaDB collection.", len(chunks))
            except Exception as e:
                logger.warning("Error appending chunks to ChromaDB: %s", e)

    def search(
        self,
        query: str,
        top_k: int = RAG_TOP_K,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute semantic similarity search for query.
        Returns top-k matching chunks with complete provenance metadata.
        """
        query_vec = self.embeddings.embed_query(query)

        # Try Chroma query first if collection available
        if self.collection is not None and self.collection.count() > 0:
            try:
                where_filter = {"source_file": source_filter} if source_filter else None
                results = self.collection.query(
                    query_embeddings=[query_vec],
                    n_results=top_k,
                    where=where_filter,
                )
                formatted = []
                if results and results.get("ids") and len(results["ids"][0]) > 0:
                    for i in range(len(results["ids"][0])):
                        meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                        doc_text = results["documents"][0][i] if results.get("documents") else ""
                        dist = results["distances"][0][i] if results.get("distances") else 0.0
                        # Cosine distance to similarity: 1 - distance
                        score = max(0.0, min(1.0, 1.0 - dist))
                        formatted.append({
                            "chunk_id": results["ids"][0][i],
                            "source_file": meta.get("source_file", "unknown"),
                            "page": meta.get("page", 1),
                            "document_type": meta.get("document_type", "Document"),
                            "relevance_score": round(score, 4),
                            "content_excerpt": doc_text,
                        })
                    return formatted
            except Exception as e:
                logger.warning("Chroma search failed (%s), falling back to memory store.", e)

        # In-memory search fallback
        results = self.memory_store.similarity_search(query_vec, top_k=top_k)
        if source_filter:
            results = [r for r in results if r["source_file"] == source_filter]
        return results


_GLOBAL_VECTOR_STORE: Optional[VectorStoreManager] = None


def get_vector_store() -> VectorStoreManager:
    """Singleton provider for vector store manager."""
    global _GLOBAL_VECTOR_STORE
    if _GLOBAL_VECTOR_STORE is None or not hasattr(_GLOBAL_VECTOR_STORE, "add_chunks"):
        _GLOBAL_VECTOR_STORE = VectorStoreManager()
    return _GLOBAL_VECTOR_STORE

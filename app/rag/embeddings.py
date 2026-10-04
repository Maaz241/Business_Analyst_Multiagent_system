"""
Embeddings generator for NovaMart RAG knowledge base.
Uses Gemini embedding models with automatic fallback.
"""

from __future__ import annotations
from typing import List, Optional
from app.services.gemini import get_gemini_service
from app.config import GEMINI_EMBEDDING_MODEL
from app.utils.logging import logger


class GeminiEmbeddings:
    """Wrapper for generating vector embeddings via Google Gemini API."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or GEMINI_EMBEDDING_MODEL
        self.gemini_service = get_gemini_service()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of document chunk strings."""
        if not texts:
            return []
        return self.gemini_service.embed_texts(texts, model=self.model_name)

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector for a single search query."""
        results = self.gemini_service.embed_texts([text], model=self.model_name)
        if results:
            return results[0]
        # Return fallback zero vector
        return [0.0] * 768

    def __call__(self, input: List[str]) -> List[List[float]]:
        """ChromaDB embedding function interface compatibility."""
        return self.embed_documents(input)

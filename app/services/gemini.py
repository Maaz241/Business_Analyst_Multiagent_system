"""
Centralized Google Gemini Service.
Unified interface for LLM completions, structured Pydantic outputs, and embeddings.
Implements model fallback, retries with backoff, and robust error handling.
"""

from __future__ import annotations
import json
import time
from typing import Any, Optional, Type, TypeVar, List, Dict
from pydantic import BaseModel
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODEL,
    GEMINI_EMBEDDING_MODEL,
)
from app.utils.logging import logger

T = TypeVar("T", bound=BaseModel)


class GeminiService:
    """Singleton service for all interactions with the Google Gemini API."""

    _instance: Optional["GeminiService"] = None

    def __new__(cls) -> "GeminiService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.api_key = GEMINI_API_KEY
        self.primary_model = GEMINI_MODEL
        self.fallback_model = GEMINI_FALLBACK_MODEL
        self.embedding_model = GEMINI_EMBEDDING_MODEL
        self._client: Optional[genai.Client] = None

        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Gemini client with model %s", self.primary_model)
            except Exception as e:
                logger.warning("Failed to initialize Gemini client: %s", e)
        else:
            logger.warning("No GEMINI_API_KEY found. Operating in offline/graceful mode.")

        self._initialized = True

    def is_configured(self) -> bool:
        """Check if a valid Gemini API key is configured."""
        return bool(self.api_key and self._client)

    def set_api_key(self, api_key: str):
        """Dynamically update API key (e.g. from UI input)."""
        self.api_key = api_key.strip()
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Updated Gemini API client dynamically.")
            except Exception as e:
                logger.error("Error setting API key: %s", e)

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        model: Optional[str] = None,
        max_output_tokens: int = 4096,
    ) -> str:
        """Generate plain text completion with retry and fallback."""
        if not self.is_configured():
            return "Gemini API key is not configured. Please supply an API key in .env or the Streamlit sidebar."

        model_name = model or self.primary_model
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        try:
            return self._call_generate(model_name, prompt, config)
        except Exception as primary_err:
            logger.warning("Primary model %s failed (%s). Retrying with fallback %s...", model_name, primary_err, self.fallback_model)
            try:
                return self._call_generate(self.fallback_model, prompt, config)
            except Exception as fallback_err:
                logger.error("Fallback model failed: %s", fallback_err)
                raise RuntimeError(f"Gemini API failure: {fallback_err}") from fallback_err

    def generate_structured_output(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        model: Optional[str] = None,
    ) -> T:
        """Generate structured Pydantic object from Gemini with schema enforcement."""
        if not self.is_configured():
            raise RuntimeError("Gemini API key is required for structured agent generation.")

        model_name = model or self.primary_model
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        try:
            raw_text = self._call_generate(model_name, prompt, config)
            return response_schema.model_validate_json(raw_text)
        except Exception as e:
            logger.warning("Structured generation with %s failed (%s). Trying fallback %s...", model_name, e, self.fallback_model)
            try:
                raw_text = self._call_generate(self.fallback_model, prompt, config)
                return response_schema.model_validate_json(raw_text)
            except Exception as err:
                logger.error("Structured generation fallback failed: %s", err)
                raise err

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _call_generate(self, model: str, prompt: str, config: types.GenerateContentConfig) -> str:
        """Internal worker calling Google GenAI API with retry."""
        if not self._client:
            raise RuntimeError("GenAI client not initialized.")
        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    def embed_texts(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        if not self.is_configured():
            # Return deterministic fallback embeddings if API not configured
            logger.warning("Generating offline pseudo-embeddings since Gemini API is not configured.")
            return [self._pseudo_embed(t) for t in texts]

        model_name = model or self.embedding_model
        embeddings: List[List[float]] = []

        # Batch embed or embed iteratively
        for chunk in texts:
            try:
                res = self._client.models.embed_content(
                    model=model_name,
                    contents=chunk,
                )
                if hasattr(res, "embedding") and hasattr(res.embedding, "values"):
                    embeddings.append(res.embedding.values)
                elif hasattr(res, "embeddings") and res.embeddings:
                    embeddings.append(res.embeddings[0].values)
                else:
                    embeddings.append(self._pseudo_embed(chunk))
            except Exception as e:
                logger.warning("Embed error for chunk (%s). Using fallback embedding.", e)
                embeddings.append(self._pseudo_embed(chunk))

        return embeddings

    def _pseudo_embed(self, text: str, dim: int = 768) -> List[float]:
        """Deterministic hash-based embedding fallback for offline testing and demos."""
        import hashlib
        import numpy as np
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Seed pseudo-random generator with hash to get stable vector
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


def get_gemini_service() -> GeminiService:
    """Get the singleton GeminiService instance."""
    return GeminiService()

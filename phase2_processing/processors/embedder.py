"""
processors/embedder.py
─────────────────────────────────────────────────────────────────────────────
Step 6: Embedding Generation
Architecture Ref: Phase 2 § 2.2 / § 2.6

Generates dense vector representation of review texts.
Supports:
1. Local SentenceTransformers (all-MiniLM-L6-v2) - 384 dimensions, GDPR-safe, fast.
2. OpenAI Embeddings API (text-embedding-3-small) - 1536 dimensions (if key is set).
3. Google Gemini Embeddings API (text-embedding-004) - 768 dimensions (if key is set).
4. Fallback Dummy Embedder (for local development without internet/dependencies).
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import requests
from loguru import logger

# Initialize model placeholder
_sentence_transformer_model = None


def _init_local_model():
    """Lazily load sentence-transformers model if installed."""
    global _sentence_transformer_model
    if _sentence_transformer_model is not None:
        return _sentence_transformer_model

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("[Embedder] Loading local SentenceTransformer 'all-MiniLM-L6-v2'...")
        _sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
        return _sentence_transformer_model
    except ImportError:
        logger.debug("[Embedder] sentence-transformers package not installed. Skipping local embedding.")
    except Exception as exc:
        logger.warning(f"[Embedder] Failed to load local SentenceTransformer: {exc}")
    
    return None


def _embed_via_gemini(text: str, api_key: str) -> list[float] | None:
    """Call Gemini Embedding API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text}]
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result["embedding"]["values"]
        else:
            logger.warning(f"[Embedder] Gemini Embed API status {response.status_code}: {response.text}")
    except Exception as exc:
        logger.warning(f"[Embedder] Gemini Embed API error: {exc}")
    return None


def _embed_via_openai(text: str, api_key: str) -> list[float] | None:
    """Call OpenAI Embedding API."""
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result["data"][0]["embedding"]
        else:
            logger.warning(f"[Embedder] OpenAI Embed API status {response.status_code}: {response.text}")
    except Exception as exc:
        logger.warning(f"[Embedder] OpenAI Embed API error: {exc}")
    return None


def _get_dummy_embedding(text: str, dimensions: int = 384) -> list[float]:
    """
    Generate a deterministic dummy embedding vector based on text hash.
    Used for local testing when no external APIs or libraries are available.
    """
    import hashlib
    base_hash = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(dimensions):
        # Create a unique hash for each dimension index
        h = hashlib.sha256(base_hash + str(i).encode("utf-8")).digest()
        # Convert first 4 bytes of hash to signed integer
        val = int.from_bytes(h[:4], byteorder="big", signed=True)
        # Normalize to [-1.0, 1.0]
        float_val = val / 2147483648.0
        vec.append(round(float_val, 5))
    return vec


def generate_embedding(text: str) -> tuple[list[float], int]:
    """
    Generate a vector embedding for the given text.

    Returns:
        A tuple of (embedding_vector_list, dimensions_integer).
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("YOUTUBE_API_KEY")

    # 1. Try local sentence-transformers if available
    local_model = _init_local_model()
    if local_model:
        logger.debug("[Embedder] Generating local sentence-transformer embedding...")
        vector = local_model.encode(text).tolist()
        return vector, len(vector)

    # 2. Try Gemini API
    if gemini_key and not gemini_key.startswith("your_") and not gemini_key.startswith("GOCSPX"):
        logger.debug("[Embedder] Generating embedding via Gemini API...")
        vector = _embed_via_gemini(text, gemini_key)
        if vector:
            return vector, len(vector)

    # 3. Try OpenAI API
    if openai_key and not openai_key.startswith("your_"):
        logger.debug("[Embedder] Generating embedding via OpenAI API...")
        vector = _embed_via_openai(text, openai_key)
        if vector:
            return vector, len(vector)

    # 4. Fallback to dummy
    logger.debug("[Embedder] Falling back to dummy embedding (dimensions=384)...")
    vector = _get_dummy_embedding(text, 384)
    return vector, 384

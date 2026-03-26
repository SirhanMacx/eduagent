"""Embedding providers for episodic memory.

Priority:
1. Ollama embeddings (if local Ollama running — free, best quality)
2. TF-IDF with bigrams (no dependencies, always works)
"""
from __future__ import annotations

import logging
import math
import re

logger = logging.getLogger(__name__)


def _simple_stem(word: str) -> str:
    """Minimal suffix-stripping stemmer (no dependencies)."""
    if len(word) <= 3:
        return word
    for suffix in ("ation", "tion", "sion", "ness", "ment", "ible", "able",
                   "ing", "ies", "ous", "ive", "ful", "ess", "ize",
                   "ed", "ly", "er", "al", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


class OllamaEmbedder:
    """Uses local Ollama for embeddings — best quality, free."""

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "mxbai-embed-large") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def embed(self, text: str) -> list[float]:
        import httpx
        resp = httpx.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns {"embeddings": [[...]]} for single input
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        return data.get("embedding", [])

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (norm_a * norm_b)


class TFIDFEmbedder:
    """TF-IDF with bigrams — no dependencies, always available."""

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._next_idx = 0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase, strip non-alpha, stem, and generate bigrams."""
        raw = re.findall(r"[a-z]+", text.lower())
        stemmed = [_simple_stem(w) for w in raw]
        # Add bigrams for better short-phrase discrimination
        bigrams = [f"{stemmed[i]}_{stemmed[i+1]}" for i in range(len(stemmed) - 1)]
        return stemmed + bigrams

    def embed(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        for t in tokens:
            if t not in self._vocab:
                self._vocab[t] = self._next_idx
                self._next_idx += 1
        vec = [0.0] * len(self._vocab)
        for t in tokens:
            vec[self._vocab[t]] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        max_len = max(len(a), len(b))
        a = a + [0.0] * (max_len - len(a))
        b = b + [0.0] * (max_len - len(b))
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (norm_a * norm_b)


def get_embedder() -> OllamaEmbedder | TFIDFEmbedder:
    """Get the best available embedder.

    Tries Ollama first (if running locally with an embedding model),
    falls back to TF-IDF with bigrams.
    """
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            # Check for embedding models
            embed_models = [m for m in models if "embed" in m.lower()]
            if embed_models:
                logger.debug("Using Ollama embedder: %s", embed_models[0])
                return OllamaEmbedder(model=embed_models[0])
    except Exception:
        pass

    logger.debug("Using TF-IDF embedder (install Ollama + embedding model for better recall)")
    return TFIDFEmbedder()

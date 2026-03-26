"""Embedding providers for episodic memory.

Default: TF-IDF (no dependencies, always works).
Upgrade: ONNX all-MiniLM-L6-v2 (pip install 'clawed[memory]').
Upgrade: Ollama mxbai-embed-large (if Ollama running locally).
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
    # Order matters: try longest suffixes first
    for suffix in ("ation", "tion", "sion", "ness", "ment", "ible", "able",
                   "ing", "ies", "ous", "ive", "ful", "ess", "ize",
                   "ed", "ly", "er", "al", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


class TFIDFEmbedder:
    """Simple TF-IDF based embedder — no dependencies, always available."""

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._next_idx = 0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase, strip non-alpha, and stem."""
        raw = re.findall(r"[a-z]+", text.lower())
        return [_simple_stem(w) for w in raw]

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


def get_embedder() -> TFIDFEmbedder:
    """Get the best available embedder. Currently returns TF-IDF."""
    return TFIDFEmbedder()

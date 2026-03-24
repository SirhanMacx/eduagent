"""Image sourcing for slide presentations.

Fetches relevant educational images from Unsplash (free tier) with local
caching.  Falls back gracefully to ``None`` when no API key is configured
or the request fails — slides still look good without images.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".eduagent" / "cache" / "images"

# Subject-aware keywords that help Unsplash return education-relevant images
_SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "history": ["history", "education", "vintage"],
    "social studies": ["history", "education", "vintage"],
    "science": ["science", "education", "laboratory"],
    "biology": ["biology", "science", "nature"],
    "chemistry": ["chemistry", "science", "laboratory"],
    "physics": ["physics", "science", "education"],
    "math": ["mathematics", "education", "classroom"],
    "mathematics": ["mathematics", "education", "classroom"],
    "algebra": ["mathematics", "algebra", "classroom"],
    "geometry": ["mathematics", "geometry", "education"],
    "ela": ["reading", "literature", "education"],
    "english": ["reading", "literature", "education"],
    "language arts": ["reading", "literature", "education"],
}


def _build_search_query(topic: str, subject: str = "") -> str:
    """Convert a lesson topic into a good image search query.

    Examples::

        >>> _build_search_query('The American Revolution', 'history')
        'american revolution history education'
        >>> _build_search_query('Photosynthesis', 'science')
        'photosynthesis science education'
        >>> _build_search_query('Solving Linear Equations', 'math')
        'solving linear equations mathematics education'
    """
    # Clean up the topic: strip punctuation, lower-case
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", topic).strip().lower()

    # Remove very common filler words to keep query focused
    stopwords = {"the", "a", "an", "of", "in", "on", "for", "and", "to", "is", "are"}
    words = [w for w in cleaned.split() if w not in stopwords]
    query_base = " ".join(words) if words else cleaned

    # Append subject-specific keywords
    subject_lower = subject.strip().lower()
    extra = _SUBJECT_KEYWORDS.get(subject_lower, ["education"])
    # Avoid duplicating words already in the query
    existing = set(query_base.split())
    suffix = " ".join(w for w in extra if w not in existing)

    return f"{query_base} {suffix}".strip()


def _cache_path(query: str) -> Path:
    """Return the local cache path for a given query."""
    h = hashlib.sha256(query.encode()).hexdigest()[:16]
    return _CACHE_DIR / f"{h}.jpg"


def _get_unsplash_key() -> Optional[str]:
    """Return the Unsplash access key from env or config, or None."""
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if key:
        return key
    # Try the secure config store
    try:
        from eduagent.config import get_api_key

        return get_api_key("unsplash")
    except Exception:
        return None


async def fetch_slide_image(
    topic: str,
    subject: str = "",
    cache_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Fetch a relevant image for a slide topic.

    Returns path to downloaded image, or ``None`` if unavailable.
    Caches images locally to avoid re-fetching.

    Parameters
    ----------
    topic:
        The slide topic / title (e.g. "The American Revolution").
    subject:
        Optional subject area for better search results.
    cache_dir:
        Override cache directory (useful for tests).
    """
    access_key = _get_unsplash_key()
    if not access_key:
        logger.debug("No Unsplash API key configured — skipping image fetch")
        return None

    query = _build_search_query(topic, subject)
    base = cache_dir or _CACHE_DIR
    cached = base / f"{hashlib.sha256(query.encode()).hexdigest()[:16]}.jpg"

    if cached.exists() and cached.stat().st_size > 0:
        logger.debug("Image cache hit for query: %s", query)
        return cached

    import httpx

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": 1,
        "orientation": "landscape",
    }
    headers = {"Authorization": f"Client-ID {access_key}"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            if not results:
                logger.debug("No Unsplash results for query: %s", query)
                return None

            image_url = results[0]["urls"].get("regular") or results[0]["urls"].get("small")
            if not image_url:
                return None

            # Download the image
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()

            base.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(img_resp.content)
            logger.info("Downloaded slide image for '%s' -> %s", query, cached)
            return cached

    except Exception as e:
        logger.debug("Image fetch failed for '%s': %s", query, e)
        return None

"""Image sourcing for slide presentations.

Fetches relevant educational images from multiple academic sources:

1. **Library of Congress** (free, no key, public domain) -- historical images,
   maps, documents.  Ideal for history / social studies / civics.
2. **Wikimedia Commons** (free, no key, CC-licensed) -- scientific diagrams,
   paintings, illustrations.  Good for all subjects.
3. **Unsplash** (free with API key) -- modern photographs.  Generic fallback.

Sources are tried in subject-aware priority order.  All images are cached
locally at ``~/.eduagent/cache/images/<source>/<hash>.jpg``.

Falls back gracefully to ``None`` when no image can be found -- slides still
look good without images.
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

# Per-image network timeout (seconds)
_FETCH_TIMEOUT = 5.0

# ── Subject-aware query enrichment ───────────────────────────────────

_SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "history": ["historical", "primary source"],
    "social studies": ["historical", "primary source"],
    "civics": ["historical", "government"],
    "government": ["historical", "government"],
    "science": ["diagram", "illustration"],
    "biology": ["diagram", "biology"],
    "chemistry": ["diagram", "chemistry"],
    "physics": ["diagram", "physics"],
    "math": ["mathematics", "education"],
    "mathematics": ["mathematics", "education"],
    "algebra": ["mathematics", "algebra"],
    "geometry": ["mathematics", "geometry"],
    "art": ["painting", "artwork"],
    "music": ["music", "artwork"],
    "ela": ["reading", "literature", "education"],
    "english": ["reading", "literature", "education"],
    "language arts": ["reading", "literature", "education"],
}


def _extract_key_concepts(text: str, max_concepts: int = 3) -> list[str]:
    """Extract key nouns/concepts from text for targeted image search.

    Uses simple heuristics -- capitalized proper nouns, quoted terms,
    and subject-specific keywords.
    """
    concepts: list[str] = []

    # Extract proper nouns (capitalized multi-word phrases)
    proper_nouns = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+', text)
    concepts.extend(proper_nouns[:2])

    # Extract quoted terms
    quoted = re.findall(r'"([^"]+)"', text) + re.findall(r"'([^']+)'", text)
    concepts.extend(quoted[:2])

    # Extract terms after "about", "of", "on" (topic indicators)
    topic_phrases = re.findall(
        r'(?:about|of|on|regarding|concerning)\s+(?:the\s+)?([A-Z][\w\s]{3,30})',
        text,
    )
    concepts.extend(topic_phrases[:1])

    # Deduplicate and limit
    seen: set[str] = set()
    unique: list[str] = []
    for c in concepts:
        c_lower = c.lower().strip()
        if c_lower not in seen and len(c_lower) > 3:
            seen.add(c_lower)
            unique.append(c)
    return unique[:max_concepts]


# ── Subject-specific query refinement ────────────────────────────────

_SUBJECT_QUERY_STYLE: dict[str, str] = {
    "history": "event_person_document",
    "social studies": "event_person_document",
    "civics": "event_person_document",
    "government": "event_person_document",
    "science": "process_organism_diagram",
    "biology": "process_organism_diagram",
    "chemistry": "process_organism_diagram",
    "physics": "process_organism_diagram",
    "math": "visual_representation",
    "mathematics": "visual_representation",
    "algebra": "visual_representation",
    "geometry": "visual_representation",
    "ela": "author_literary_period",
    "english": "author_literary_period",
    "language arts": "author_literary_period",
}


def _build_search_query(topic: str, subject: str = "") -> str:
    """Convert a lesson topic into a good image search query.

    Builds subject-aware queries that target specific visual content:
    - History: the specific event, person, or document mentioned
    - Science: the specific process or organism
    - Math: the specific visual representation
    - ELA: the author or literary period

    Examples::

        >>> _build_search_query('The American Revolution', 'history')
        'american revolution historical primary source'
        >>> _build_search_query('Photosynthesis', 'science')
        'photosynthesis diagram illustration'
        >>> _build_search_query('Solving Linear Equations', 'math')
        'solving linear equations mathematics education'
    """
    # Clean up the topic: strip punctuation, lower-case
    cleaned = re.sub(r"[^a-zA-Z0-9\\s]", "", topic).strip().lower()

    # Remove very common filler words to keep query focused
    stopwords = {"the", "a", "an", "of", "in", "on", "for", "and", "to", "is", "are"}
    words = [w for w in cleaned.split() if w not in stopwords]
    query_base = " ".join(words) if words else cleaned

    # Append subject-specific keywords
    subject_lower = subject.strip().lower()
    style = _SUBJECT_QUERY_STYLE.get(subject_lower, "")
    extra = _SUBJECT_KEYWORDS.get(subject_lower, ["education"])

    # Subject-style refinements: add specific qualifiers
    if style == "event_person_document":
        # History: look for dates, specific events
        date_match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', topic)
        if date_match:
            extra = [date_match.group()] + extra[:1]
    elif style == "process_organism_diagram":
        extra = ["diagram"] + extra[:1]
    elif style == "visual_representation":
        extra = ["graph", "diagram"] + extra[:1]
    elif style == "author_literary_period":
        extra = ["portrait", "literature"] + extra[:1]

    # Avoid duplicating words already in the query
    existing = set(query_base.split())
    suffix = " ".join(w for w in extra if w not in existing)

    return f"{query_base} {suffix}".strip()


# ── Source selection ─────────────────────────────────────────────────


def _select_sources(subject: str, topic: str = "") -> list[str]:
    """Pick the best image sources for this subject.

    Returns an ordered list of source identifiers to try.
    """
    subject_lower = subject.strip().lower()
    if any(s in subject_lower for s in ("history", "social", "civics", "government")):
        return ["loc", "wikimedia", "unsplash"]
    elif any(s in subject_lower for s in ("science", "biology", "chemistry", "physics")):
        return ["wikimedia", "unsplash"]
    elif any(s in subject_lower for s in ("art", "music")):
        return ["wikimedia", "unsplash"]
    else:
        return ["unsplash", "wikimedia"]


# ── Cache helpers ────────────────────────────────────────────────────


def _cache_path(source: str, query: str, base: Optional[Path] = None) -> Path:
    """Return the local cache path for a given source + query."""
    h = hashlib.sha256(f"{source}:{query}".encode()).hexdigest()[:16]
    root = base or _CACHE_DIR
    return root / source / f"{h}.jpg"


def _check_cache(source: str, query: str, base: Optional[Path] = None) -> Optional[Path]:
    """Return cached image path if it exists and is non-empty."""
    path = _cache_path(source, query, base)
    if path.exists() and path.stat().st_size > 0:
        logger.debug("Image cache hit [%s] for query: %s", source, query)
        return path
    return None


def _save_to_cache(
    data: bytes, source: str, query: str, base: Optional[Path] = None,
) -> Path:
    """Write image bytes to the cache and return the path."""
    path = _cache_path(source, query, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


# ── Individual source fetchers ───────────────────────────────────────


async def _fetch_loc(
    query: str, cache_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Fetch an image from the Library of Congress free API.

    Endpoint returns JSON with ``results[].image_url`` (list) or
    ``results[].thumb_gallery``.
    """
    import httpx

    cached = _check_cache("loc", query, cache_dir)
    if cached:
        return cached

    url = "https://www.loc.gov/search/"
    params = {
        "q": query,
        "fa": "online-format:image",
        "fo": "json",
        "c": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            image_url: Optional[str] = None
            for item in results:
                # Prefer image_url (list of URLs)
                urls = item.get("image_url", [])
                if urls:
                    image_url = urls[0]
                    break
                # Fallback to thumb_gallery
                thumb = item.get("thumb_gallery")
                if thumb:
                    image_url = thumb
                    break

            if not image_url:
                logger.debug("No LOC results for query: %s", query)
                return None

            img_resp = await client.get(image_url, timeout=_FETCH_TIMEOUT)
            img_resp.raise_for_status()

            path = _save_to_cache(img_resp.content, "loc", query, cache_dir)
            logger.info("Downloaded LOC image for '%s' -> %s", query, path)
            return path

    except Exception as e:
        logger.debug("LOC fetch failed for '%s': %s", query, e)
        return None


async def _fetch_wikimedia(
    query: str, cache_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Fetch an image from Wikimedia Commons API."""
    import httpx

    cached = _check_cache("wikimedia", query, cache_dir)
    if cached:
        return cached

    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "1024",
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            image_url: Optional[str] = None
            for _page_id, page in pages.items():
                info_list = page.get("imageinfo", [])
                if info_list:
                    # Use the thumbnail URL (scaled to 1024px width)
                    image_url = info_list[0].get("thumburl") or info_list[0].get("url")
                    if image_url:
                        break

            if not image_url:
                logger.debug("No Wikimedia results for query: %s", query)
                return None

            img_resp = await client.get(image_url, timeout=_FETCH_TIMEOUT)
            img_resp.raise_for_status()

            path = _save_to_cache(img_resp.content, "wikimedia", query, cache_dir)
            logger.info("Downloaded Wikimedia image for '%s' -> %s", query, path)
            return path

    except Exception as e:
        logger.debug("Wikimedia fetch failed for '%s': %s", query, e)
        return None


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


async def _fetch_unsplash(
    query: str, cache_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Fetch an image from the Unsplash API (requires API key)."""
    import httpx

    access_key = _get_unsplash_key()
    if not access_key:
        logger.debug("No Unsplash API key configured -- skipping")
        return None

    cached = _check_cache("unsplash", query, cache_dir)
    if cached:
        return cached

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": 1,
        "orientation": "landscape",
    }
    headers = {"Authorization": f"Client-ID {access_key}"}

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
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

            img_resp = await client.get(image_url, timeout=_FETCH_TIMEOUT)
            img_resp.raise_for_status()

            path = _save_to_cache(img_resp.content, "unsplash", query, cache_dir)
            logger.info("Downloaded Unsplash image for '%s' -> %s", query, path)
            return path

    except Exception as e:
        logger.debug("Unsplash fetch failed for '%s': %s", query, e)
        return None


# Source name -> fetcher function mapping
_SOURCE_FETCHERS: dict = {
    "loc": _fetch_loc,
    "wikimedia": _fetch_wikimedia,
    "unsplash": _fetch_unsplash,
}


# ── Public API ───────────────────────────────────────────────────────


async def fetch_slide_image(
    topic: str,
    subject: str = "",
    cache_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Fetch a relevant image for a slide topic.

    Tries multiple academic sources in subject-aware priority order.
    Returns path to downloaded image, or ``None`` if unavailable.
    Caches images locally to avoid re-fetching.

    Parameters
    ----------
    topic:
        The slide topic / title (e.g. "The American Revolution").
    subject:
        Optional subject area for better source routing.
    cache_dir:
        Override cache directory (useful for tests).
    """
    query = _build_search_query(topic, subject)
    sources = _select_sources(subject, topic)

    for source_name in sources:
        fetcher = _SOURCE_FETCHERS.get(source_name)
        if not fetcher:
            continue
        try:
            path = await fetcher(query, cache_dir)
            if path:
                return path
        except Exception as e:
            logger.debug("Source %s failed for '%s': %s", source_name, query, e)
            continue

    logger.debug("No image found from any source for '%s'", query)
    return None


async def fetch_content_image(
    content_text: str,
    subject: str = "",
    fallback_topic: str = "",
    cache_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Fetch an image based on the *content* of a slide, not just the title.

    Extracts key concepts from ``content_text`` and searches for each one
    individually, returning the first good result.  Falls back to
    ``fallback_topic`` (typically the lesson title) if no concept-specific
    image is found.

    Parameters
    ----------
    content_text:
        The slide body text to extract search concepts from.
    subject:
        Subject area for source routing and query enrichment.
    fallback_topic:
        Lesson title used as a last resort if concept extraction
        yields no results.
    cache_dir:
        Override cache directory (useful for tests).
    """
    concepts = _extract_key_concepts(content_text)

    for concept in concepts:
        query = _build_search_query(concept, subject)
        sources = _select_sources(subject, concept)

        for source_name in sources:
            fetcher = _SOURCE_FETCHERS.get(source_name)
            if not fetcher:
                continue
            try:
                path = await fetcher(query, cache_dir)
                if path:
                    logger.info(
                        "Content image found via concept '%s' -> %s",
                        concept, path,
                    )
                    return path
            except Exception as e:
                logger.debug(
                    "Source %s failed for concept '%s': %s",
                    source_name, concept, e,
                )
                continue

    # Fallback to lesson title
    if fallback_topic:
        logger.debug(
            "No concept-specific image found, falling back to topic: %s",
            fallback_topic,
        )
        return await fetch_slide_image(fallback_topic, subject, cache_dir)

    return None

"""Image sourcing for slide presentations.

Fetches relevant educational images from multiple academic sources:

1. **Teacher's own images** (highest priority -- personalized curriculum material)
2. **Library of Congress** (free, no key, public domain) -- historical images,
   maps, documents.  Ideal for history / social studies / civics.
3. **Wikimedia Commons** (free, no key, CC-licensed) -- scientific diagrams,
   paintings, illustrations.  Good for all subjects.
4. **Unsplash** (free with API key) -- modern photographs.  Generic fallback.

Sources are tried in subject-aware priority order.  Teacher images are always
checked first.  All external images are cached locally at
``~/.eduagent/cache/images/<source>/<hash>.jpg``.

Falls back gracefully to ``None`` when no image can be found -- slides still
look good without images.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".eduagent" / "cache" / "images"

# Per-image network timeout (seconds)
_FETCH_TIMEOUT = 5.0

# ── Cache eviction settings ──────────────────────────────────────────
MAX_CACHE_AGE_DAYS = 30
_cache_cleaned_this_session = False


def _cleanup_cache(cache_dir: Optional[Path] = None) -> None:
    """Remove cached images older than MAX_CACHE_AGE_DAYS to prevent unbounded growth.

    Called once per session (guarded by module-level flag) at the start of
    image fetching.  Silently ignores errors on individual files.
    """
    global _cache_cleaned_this_session
    if _cache_cleaned_this_session:
        return
    _cache_cleaned_this_session = True

    root = cache_dir or _CACHE_DIR
    if not root.exists():
        return

    cutoff = time.time() - (MAX_CACHE_AGE_DAYS * 86400)
    removed = 0
    for source_dir in root.iterdir():
        if not source_dir.is_dir():
            continue
        for f in source_dir.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except OSError:
                pass  # file may have been removed concurrently
    if removed:
        logger.info("Cache cleanup: removed %d images older than %d days", removed, MAX_CACHE_AGE_DAYS)

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


def extract_image_subjects(lesson) -> list[dict]:
    """Extract specific people, places, and artifacts from lesson content for targeted image search.

    Instead of searching for generic lesson titles ("Age of Absolutism"),
    extracts specific entities like "Louis XIV", "Palace of Versailles",
    "Treaty of Westphalia" that produce relevant image results.
    """
    subjects: list[dict] = []
    all_text = " ".join(filter(None, [
        getattr(lesson, 'title', ''),
        getattr(lesson, 'objective', ''),
        getattr(lesson, 'do_now', ''),
        getattr(lesson, 'direct_instruction', ''),
        getattr(lesson, 'guided_practice', ''),
    ]))

    # Named historical figures
    # Pattern 1: Titled names (King Louis, President Lincoln, etc.)
    # Pattern 2: Known first names of historical figures
    # Pattern 3: Any "Firstname Lastname" that appears near historical context
    common_non_names = {
        "The", "This", "That", "These", "Those", "When", "Where", "What",
        "How", "Why", "Each", "Every", "Your", "Their", "Some", "Many",
        "Most", "Both", "Other", "Such", "More", "Less", "New", "Old",
        "First", "Last", "Next", "Direct", "Independent", "Guided",
        "Exit", "Essential", "Key", "Primary", "Source", "Document",
        "Group", "Social", "Studies", "Grade", "Unit", "Lesson",
        "Common", "American", "English", "French", "British", "European",
        "Civil", "World", "Cold", "Middle", "South", "North", "West", "East",
        "Analyze", "Compare", "Evaluate", "Describe", "Explain", "Identify",
        "Test", "Review", "Movement", "Act", "Age", "Era", "Period",
    }
    people_patterns = [
        r"((?:King |Queen |Emperor |Empress |President |Pope |Tsar |Czar )"
        r"[A-Z][a-z]+(?: [A-Z][a-z]+)*(?: the Great| [IVX]+)?)",
        r"((?:Louis|Peter|Frederick|Catherine|Elizabeth|Napoleon|Alexander)"
        r" (?:the Great|[IVX]+|[A-Z][a-z]+))",
        # General: Firstname Lastname (two+ capitalized words, not common English)
        r"\b([A-Z][a-z]{2,12} [A-Z][a-z]{2,15})\b",
        # Three-word names (Martin Luther King, John Quincy Adams)
        r"\b([A-Z][a-z]{2,12} [A-Z][a-z]{2,12} [A-Z][a-z]{2,12})\b",
    ]
    people_found: set[str] = set()
    for pattern in people_patterns:
        for match in re.findall(pattern, all_text):
            name = match.strip()
            if len(name) > 5:
                first_word = name.split()[0]
                if first_word not in common_non_names:
                    people_found.add(name)
    for person in list(people_found)[:5]:
        subjects.append({"query": f"{person} portrait", "type": "person", "label": person})

    # Named places/buildings
    place_patterns = re.findall(
        r"((?:Palace|Castle|Cathedral|Battle|Siege|Fort) of [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        all_text,
    )
    for place in set(place_patterns[:3]):
        subjects.append({"query": f"{place} historical", "type": "place", "label": place})

    # Named places without "of" (e.g., "Versailles", "Bastille")
    famous_places = re.findall(
        r"\b(Versailles|Bastille|Kremlin|Vatican|Parliament|Westminster|Colosseum|Parthenon|Stonehenge)\b",
        all_text,
    )
    for place in set(famous_places[:2]):
        subjects.append({"query": f"{place} historical photograph", "type": "place", "label": place})

    # Historical documents/treaties
    doc_patterns = re.findall(
        r"((?:Treaty|Declaration|Constitution|Bill|Act|Edict|Manifesto|Charter) of [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        all_text,
    )
    for doc_name in set(doc_patterns[:2]):
        subjects.append({"query": f"{doc_name} historical document", "type": "document", "label": doc_name})

    # Fallback: lesson title
    if not subjects:
        title = getattr(lesson, 'title', 'lesson')
        subjects.append({"query": title, "type": "topic", "label": title})

    return subjects


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
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", topic).strip().lower()

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
    Teacher's own images are always checked first.
    Only uses academic sources (LOC, Wikimedia). No stock photos.
    """
    subject_lower = subject.strip().lower()
    if any(s in subject_lower for s in ("history", "social", "civics", "government")):
        return ["teacher_files", "loc", "wikimedia"]
    elif any(s in subject_lower for s in ("science", "biology", "chemistry", "physics")):
        return ["teacher_files", "wikimedia", "loc"]
    elif any(s in subject_lower for s in ("art", "music")):
        return ["teacher_files", "wikimedia", "loc"]
    else:
        return ["teacher_files", "loc", "wikimedia"]


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
                    # Take highest resolution (last URL), strip fragment
                    image_url = urls[-1].split("#")[0]
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
        headers = {"User-Agent": "ClawED/1.0 (https://github.com/SirhanMacx/Claw-ED; educational)"}
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT, headers=headers) as client:
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
        from clawed.config import get_api_key

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


def _score_teacher_image_row(
    row: object,
    keywords: list[str],
    query_lower: str,
) -> int:
    """Score a teacher image row by relevance to the search keywords.

    Scoring rules:
    - Exact phrase match in context/title: +5
    - Keyword found in filename (basename of image_path): +3 per keyword
    - Keyword found in context_text or asset title: +2 per keyword
    - Partial word match (e.g. "suffrage" in "suffragist"): +1 per keyword
    """
    context = (row["context_text"] or "").lower()
    title = (row["title"] or "").lower()
    image_path = (row["image_path"] or "").lower()
    filename = Path(image_path).stem.replace("_", " ").replace("-", " ").lower()
    combined = f"{context} {title}"

    score = 0

    # Exact phrase match in content gets big bonus
    if query_lower in combined:
        score += 5

    # Keyword matches -- filename matches are weighted higher
    for kw in keywords:
        if kw in filename:
            score += 3
        if kw in combined:
            score += 2

    # Partial word matches (e.g., "suffrage" matches "suffragist")
    for kw in keywords:
        if kw not in combined and kw not in filename:
            all_words = combined.split() + filename.split()
            for word in all_words:
                if len(kw) >= 4 and len(word) >= 4:
                    if kw in word or word in kw:
                        score += 1
                        break

    return score


def _query_teacher_images_db(
    search_keywords: list[str],
    limit: int = 150,
) -> list:
    """Run a SQL query against the teacher's image database.

    Returns matching rows with image_path, context_text, and title.
    Uses OR matching so any single keyword can surface results.
    """
    import sqlite3

    db_path = Path.home() / ".eduagent" / "memory" / "curriculum_kb.db"
    if not db_path.exists():
        return []

    if not search_keywords:
        return []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        like_clauses = " OR ".join(
            "(lower(ai.context_text) LIKE '%' || ? || '%'"
            " OR lower(a.title) LIKE '%' || ? || '%'"
            " OR lower(ai.image_path) LIKE '%' || ? || '%')"
            for _ in search_keywords[:8]
        )
        params: list[str] = []
        for kw in search_keywords[:8]:
            params.extend([kw, kw, kw])
        rows = conn.execute(
            f"SELECT ai.image_path, ai.context_text, a.title "
            f"FROM asset_images ai "
            f"JOIN assets a ON ai.asset_id = a.id "
            f"WHERE ai.image_path != '' AND ({like_clauses}) "
            f"LIMIT {limit}",
            params,
        ).fetchall()
    return rows


def _best_from_rows(
    rows: list,
    keywords: list[str],
    query_lower: str,
    min_score: int = 4,
) -> Optional[Path]:
    """Pick the best image from a set of DB rows, respecting a minimum score."""
    if not rows:
        return None

    scored: list[tuple[int, str]] = []
    for row in rows:
        s = _score_teacher_image_row(row, keywords, query_lower)
        if s >= min_score:
            scored.append((s, row["image_path"]))

    if not scored:
        return None

    # Sort descending by score, take best
    scored.sort(key=lambda x: x[0], reverse=True)
    # Return the top match if file actually exists
    for _score, path_str in scored[:5]:
        p = Path(path_str)
        if p.exists():
            return p

    return None


async def _fetch_teacher_image(
    query: str,
    cache_dir: Optional[Path] = None,
    subject: str = "",
) -> Optional[Path]:
    """Search the teacher's extracted images with progressive broadening.

    Checks the asset_images table for images whose context_text, parent
    asset title, or filename has keyword overlap with the query.  Uses a
    three-stage search strategy:

    1. **Full query** -- all keywords combined (high precision)
    2. **Individual keywords** -- each significant keyword independently
       (broader recall), scored by how many terms match
    3. **Subject fallback** -- just the subject name (broadest)

    Returns the local image path if found -- no network call needed.
    """
    try:
        # Stage 1: Full query -- all keywords at once
        all_keywords = [w.lower() for w in query.split() if len(w) > 2]
        if not all_keywords:
            return None

        query_lower = query.lower()
        rows = _query_teacher_images_db(all_keywords)

        result = _best_from_rows(rows, all_keywords, query_lower, min_score=6)
        if result:
            logger.info(
                "Teacher image match (full query) for '%s' -> %s", query, result,
            )
            return result

        # Stage 2: Try individual significant keywords (drop stopwords + short words)
        # Sort keywords longest-first so the most specific term is tried first
        stopwords = {"the", "a", "an", "of", "in", "on", "for", "and", "to", "is", "are", "was", "were"}
        significant = sorted(
            [w for w in all_keywords if w not in stopwords and len(w) > 3],
            key=len,
            reverse=True,
        )

        for kw in significant:
            kw_rows = _query_teacher_images_db([kw])
            # Score against all original keywords even though we searched by one
            result = _best_from_rows(kw_rows, all_keywords, query_lower, min_score=4)
            if result:
                logger.info(
                    "Teacher image match (keyword '%s') for '%s' -> %s",
                    kw, query, result,
                )
                return result

        # Stage 3: Subject-name fallback (e.g., "history", "biology")
        if subject:
            subj_lower = subject.strip().lower()
            subj_keywords = [w for w in subj_lower.split() if len(w) > 2]
            if subj_keywords:
                subj_rows = _query_teacher_images_db(subj_keywords)
                result = _best_from_rows(
                    subj_rows, all_keywords + subj_keywords, query_lower, min_score=3,
                )
                if result:
                    logger.info(
                        "Teacher image match (subject '%s') for '%s' -> %s",
                        subject, query, result,
                    )
                    return result

    except Exception as e:
        logger.debug("Teacher image lookup failed: %s", e)
    return None


# Source name -> fetcher function mapping
_SOURCE_FETCHERS: dict = {
    "teacher_files": _fetch_teacher_image,
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

    Tries sources in priority order:
      1. Teacher's own uploaded images (personalized, no network needed)
      2. Library of Congress (free, public domain, high quality)
      3. Wikimedia Commons (free, CC-licensed)
      4. Unsplash (requires API key, may not be configured)

    If a teacher image is found, external sources are skipped entirely.
    Failures at each level cascade to the next source.

    Parameters
    ----------
    topic:
        The slide topic / title (e.g. "The American Revolution").
    subject:
        Optional subject area for better source routing and teacher image search.
    cache_dir:
        Override cache directory (useful for tests).
    """
    # Run cache cleanup once per session
    _cleanup_cache(cache_dir)

    query = _build_search_query(topic, subject)
    sources = _select_sources(subject, topic)

    for source_name in sources:
        fetcher = _SOURCE_FETCHERS.get(source_name)
        if not fetcher:
            continue
        try:
            # Pass subject to teacher image fetcher for subject-aware broadening
            if source_name == "teacher_files":
                path = await fetcher(query, cache_dir, subject=subject)
            else:
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
                if source_name == "teacher_files":
                    path = await fetcher(query, cache_dir, subject=subject)
                else:
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

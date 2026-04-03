"""Parallel image fetching pipeline for MasterContent.

Collects all unique image_spec strings from a MasterContent object,
fetches them in parallel with timeout, and returns a mapping of
spec -> local Path.  Failures are logged but never block lesson generation.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawed.master_content import MasterContent
    from clawed.models import AppConfig

logger = logging.getLogger(__name__)

_CONCURRENT_LIMIT = 5


def _collect_image_specs(master: "MasterContent") -> dict[str, str]:
    """Collect image_spec strings with their content context.

    Returns {spec: context_text} — the context helps the image search
    find content-relevant images instead of generic skill-based ones.
    """
    specs: dict[str, str] = {}

    for entry in master.vocabulary:
        if entry.image_spec:
            specs[entry.image_spec] = f"{entry.term}: {entry.definition}"

    for ps in master.primary_sources:
        if ps.image_spec:
            specs[ps.image_spec] = getattr(ps, "title", "") or ps.image_spec

    for section in master.direct_instruction:
        if section.image_spec:
            content = getattr(section, "content", "") or getattr(section, "title", "")
            specs[section.image_spec] = content[:200] if content else section.image_spec

    for sq in master.exit_ticket:
        if sq.stimulus_image_spec:
            specs[sq.stimulus_image_spec] = getattr(sq, "question", "") or sq.stimulus_image_spec

    return specs


async def _fetch_one(
    spec: str, subject: str = "", context: str = "", timeout: int = 15,
) -> tuple[str, Path | None]:
    """Fetch a single image by spec. Returns (spec, path) or (spec, None).

    When context is provided, uses it to build a more content-specific
    search query instead of the generic topic-based one.
    """
    try:
        from clawed.slide_images import fetch_content_image, fetch_slide_image

        # Prefer content-aware search when context is available
        if context:
            try:
                path = await asyncio.wait_for(
                    fetch_content_image(context, subject=subject, fallback_topic=spec),
                    timeout=timeout,
                )
                if path and path.exists():
                    logger.info("Fetched content image for: %s", spec[:80])
                    return spec, path
            except Exception:
                pass  # Fall through to topic-based search

        path = await asyncio.wait_for(
            fetch_slide_image(spec, subject=subject),
            timeout=timeout,
        )
        if path and path.exists():
            logger.info("Fetched image for: %s", spec[:80])
            return spec, path
    except asyncio.TimeoutError:
        logger.warning("Image fetch timed out for: %s", spec[:80])
    except Exception as e:
        logger.debug("Image fetch failed for %s: %s", spec[:80], e)

    return spec, None


async def fetch_all_images(
    master: "MasterContent",
    config: "AppConfig | None" = None,
) -> dict[str, Path]:
    """Fetch all images referenced in a MasterContent in parallel.

    Args:
        master: The MasterContent object with image_spec fields.
        config: Optional config for timeout settings.

    Returns:
        A dict mapping image_spec strings to local file Paths.
        Only specs that were successfully fetched are included.
    """
    spec_map = _collect_image_specs(master)
    if not spec_map:
        return {}

    timeout = 15
    if config and hasattr(config, "image_fetch_timeout"):
        timeout = config.image_fetch_timeout

    subject = getattr(master, "subject", "")

    logger.info(
        "Fetching %d images (timeout=%ds, subject=%s, concurrency=%d)",
        len(spec_map), timeout, subject, _CONCURRENT_LIMIT,
    )

    semaphore = asyncio.Semaphore(_CONCURRENT_LIMIT)

    async def _limited_fetch(spec: str, context: str) -> tuple[str, Path | None]:
        async with semaphore:
            return await _fetch_one(spec, subject=subject, context=context, timeout=timeout)

    tasks = [_limited_fetch(spec, ctx) for spec, ctx in spec_map.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    images: dict[str, Path] = {}
    for result in results:
        if isinstance(result, Exception):
            logger.debug("Image fetch raised: %s", result)
            continue
        spec, path = result
        if path is not None:
            images[spec] = path

    logger.info("Successfully fetched %d of %d images", len(images), len(spec_map))
    return images

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


def _collect_image_specs(master: "MasterContent") -> set[str]:
    """Collect all unique non-empty image_spec strings from a MasterContent."""
    specs: set[str] = set()

    for entry in master.vocabulary:
        if entry.image_spec:
            specs.add(entry.image_spec)

    for ps in master.primary_sources:
        if ps.image_spec:
            specs.add(ps.image_spec)

    for section in master.direct_instruction:
        if section.image_spec:
            specs.add(section.image_spec)

    for sq in master.exit_ticket:
        if sq.stimulus_image_spec:
            specs.add(sq.stimulus_image_spec)

    return specs


async def _fetch_one(spec: str, subject: str = "", timeout: int = 15) -> tuple[str, Path | None]:
    """Fetch a single image by spec. Returns (spec, path) or (spec, None).

    Uses :func:`clawed.slide_images.fetch_slide_image` which already handles
    caching, multi-source fallback, and subject-aware query building.
    """
    try:
        from clawed.slide_images import fetch_slide_image

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
    specs = _collect_image_specs(master)
    if not specs:
        return {}

    timeout = 15
    if config and hasattr(config, "image_fetch_timeout"):
        timeout = config.image_fetch_timeout

    subject = getattr(master, "subject", "")

    logger.info("Fetching %d images (timeout=%ds, subject=%s)", len(specs), timeout, subject)

    tasks = [_fetch_one(spec, subject=subject, timeout=timeout) for spec in specs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    images: dict[str, Path] = {}
    for result in results:
        if isinstance(result, Exception):
            logger.debug("Image fetch raised: %s", result)
            continue
        spec, path = result
        if path is not None:
            images[spec] = path

    logger.info("Successfully fetched %d of %d images", len(images), len(specs))
    return images

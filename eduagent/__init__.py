"""EDUagent — Your teaching files, your AI co-teacher."""

import re

__version__ = "0.1.3"
__author__ = "Jon Maccarello & EDUagent Contributors"
__description__ = "Your teaching files, your AI co-teacher"


def _safe_filename(title: str) -> str:
    """Sanitize a title for use as a filename on all platforms.

    Strips characters that are illegal on Windows NTFS (colons create
    Alternate Data Streams, resulting in 0-byte files) and other OS-level
    reserved characters.
    """
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = safe.strip().lower().replace(" ", "_")[:50]
    return safe or "untitled"

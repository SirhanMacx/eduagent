"""EDUagent — Your teaching files, your AI co-teacher."""

import re

__version__ = "0.2.0"
__author__ = "Jon Maccarello & EDUagent Contributors"
__description__ = "Your teaching files, your AI co-teacher"

# Central I/O — the canonical way to handle files across all modules
from eduagent.io import output_dir, read_text, safe_filename, save_output, write_text


def _safe_filename(title: str) -> str:
    """Sanitize a title for use as a filename on all platforms.

    .. deprecated:: 0.2.0
        Use :func:`eduagent.io.safe_filename` instead.

    Strips characters that are illegal on Windows NTFS (colons create
    Alternate Data Streams, resulting in 0-byte files) and other OS-level
    reserved characters.
    """
    return safe_filename(title, max_len=50)

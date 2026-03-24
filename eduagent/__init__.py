"""EDUagent — Your teaching files, your AI co-teacher."""

__version__ = "0.2.0"
__author__ = "Jon Maccarello & EDUagent Contributors"
__description__ = "Your teaching files, your AI co-teacher"

# Central I/O — re-exported for convenience
from eduagent.io import output_dir as output_dir  # noqa: F401
from eduagent.io import read_text as read_text  # noqa: F401
from eduagent.io import safe_filename as safe_filename  # noqa: F401
from eduagent.io import save_output as save_output  # noqa: F401
from eduagent.io import write_text as write_text  # noqa: F401


def _safe_filename(title: str) -> str:
    """Sanitize a title for use as a filename on all platforms.

    .. deprecated:: 0.2.0
        Use :func:`eduagent.io.safe_filename` instead.

    Strips characters that are illegal on Windows NTFS (colons create
    Alternate Data Streams, resulting in 0-byte files) and other OS-level
    reserved characters.
    """
    return safe_filename(title, max_len=50)

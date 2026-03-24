"""Claw-ED — Your teaching files, your AI co-teacher."""

__version__ = "0.3.0"
__author__ = "Jon Maccarello & Claw-ED contributors"
__description__ = "Your teaching files, your AI co-teacher"

# Central I/O — re-exported for convenience
from clawed.io import output_dir as output_dir  # noqa: F401
from clawed.io import read_text as read_text  # noqa: F401
from clawed.io import safe_filename as safe_filename  # noqa: F401
from clawed.io import save_output as save_output  # noqa: F401
from clawed.io import write_text as write_text  # noqa: F401


def _safe_filename(title: str) -> str:
    """.. deprecated:: 0.2.0 Use :func:`clawed.io.safe_filename` instead."""
    return safe_filename(title, max_len=50)

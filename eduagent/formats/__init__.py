"""Format-specific extractors for curriculum file ingestion.

Each extractor is a plugin that handles a specific file format used by teachers.
"""

from eduagent.formats.flipchart import extract_flipchart
from eduagent.formats.notebook import extract_notebook
from eduagent.formats.xbk import extract_xbk

__all__ = ["extract_notebook", "extract_xbk", "extract_flipchart"]

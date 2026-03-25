"""Claw-ED document export -- facade module.

Public API re-exported from the split modules for backward compatibility.
"""

from clawed.export_docx import export_lesson_docx, export_student_handout  # noqa: F401
from clawed.export_pdf import export_lesson_pdf  # noqa: F401
from clawed.export_pptx import export_lesson_pptx  # noqa: F401
from clawed.export_theme import get_color_theme  # noqa: F401

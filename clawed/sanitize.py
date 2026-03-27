"""Output sanitization — clean LLM artifacts before export."""
from __future__ import annotations

import re


def sanitize_text(text: str) -> str:
    """Remove non-Latin character leakage from multilingual LLM output.

    Strips isolated CJK character runs that appear between ASCII text —
    these are model artifacts, not intentional content.
    """
    # Remove CJK runs between Latin characters
    text = re.sub(
        r'(?<=[a-zA-Z0-9.,;:!?\s])'
        r'[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f'
        r'\u30a0-\u30ff\u3040-\u309f]+'
        r'(?=[\sa-zA-Z0-9.,;:!?])',
        '',
        text,
    )
    # Clean up resulting double spaces
    text = re.sub(r'  +', ' ', text)
    return text

"""Text-to-speech narration for slide presentations.

Generates MP3 audio files from slide content so teachers can create
narrated presentations without recording their own voice. Uses Google
Text-to-Speech (free, no API key required).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def synthesize_text(text: str, output_path: Path, lang: str = "en") -> Path:
    """Generate MP3 from text using gTTS."""
    try:
        from gtts import gTTS
    except ImportError:
        logger.warning("gTTS not installed. Run: pip install gTTS")
        raise

    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(str(output_path))
    logger.info("Narration saved: %s (%d chars)", output_path.name, len(text))
    return output_path


def narrate_slides(pptx_path: Path, slide_texts: list[str]) -> list[Path]:
    """Generate MP3 narration for each slide.

    Args:
        pptx_path: Path to the PPTX file (MP3s saved alongside it)
        slide_texts: List of narration text for each slide

    Returns:
        List of MP3 file paths
    """
    narration_dir = pptx_path.parent / f"{pptx_path.stem}_narration"
    narration_dir.mkdir(parents=True, exist_ok=True)

    mp3_paths = []
    for i, text in enumerate(slide_texts, 1):
        if not text or not text.strip():
            continue
        mp3_path = narration_dir / f"slide_{i:02d}.mp3"
        try:
            synthesize_text(text, mp3_path)
            mp3_paths.append(mp3_path)
        except Exception as e:
            logger.warning("Failed to narrate slide %d: %s", i, e)

    if mp3_paths:
        logger.info("Generated %d narration files in %s", len(mp3_paths), narration_dir)

    return mp3_paths

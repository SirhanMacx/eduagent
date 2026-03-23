"""Tests for voice note transcription."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from eduagent.voice import AUDIO_EXTENSIONS, is_audio_file, transcribe_audio


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.run(coro)


# ── is_audio_file ──────────────────────────────────────────────────


class TestIsAudioFile:
    def test_supported_extensions(self):
        for ext in AUDIO_EXTENSIONS:
            assert is_audio_file(f"/tmp/recording{ext}") is True

    def test_uppercase_extension(self):
        assert is_audio_file("/tmp/recording.MP3") is True
        assert is_audio_file("/tmp/recording.WAV") is True

    def test_non_audio_files(self):
        assert is_audio_file("/tmp/document.pdf") is False
        assert is_audio_file("/tmp/lesson.docx") is False
        assert is_audio_file("/tmp/image.png") is False
        assert is_audio_file("/tmp/noext") is False

    def test_path_object(self):
        assert is_audio_file(Path("/tmp/voice.ogg")) is True
        assert is_audio_file(Path("/tmp/notes.txt")) is False


# ── transcribe_audio ───────────────────────────────────────────────


class TestTranscribeAudio:
    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _run(transcribe_audio(tmp_path / "nonexistent.mp3"))

    def test_unsupported_format(self, tmp_path):
        bad_file = tmp_path / "file.xyz"
        bad_file.write_text("not audio")
        with pytest.raises(ValueError, match="Unsupported audio format"):
            _run(transcribe_audio(bad_file))

    def test_no_backend_available(self, tmp_path):
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch("eduagent.voice._transcribe_faster_whisper", side_effect=ImportError),
            patch("eduagent.voice.shutil.which", return_value=None),
        ):
            with pytest.raises(RuntimeError, match="No transcription backend"):
                _run(transcribe_audio(audio))

    def test_faster_whisper_backend(self, tmp_path):
        audio = tmp_path / "test.ogg"
        audio.write_bytes(b"OggS" + b"\x00" * 100)

        with patch(
            "eduagent.voice._transcribe_faster_whisper",
            new_callable=AsyncMock,
            return_value="Hello from the teacher",
        ):
            result = _run(transcribe_audio(audio))
            assert result == "Hello from the teacher"

    def test_whisper_cli_fallback(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\xff\xfb" + b"\x00" * 100)

        with (
            patch("eduagent.voice._transcribe_faster_whisper", side_effect=ImportError),
            patch("eduagent.voice.shutil.which", return_value="/usr/bin/whisper"),
            patch(
                "eduagent.voice._transcribe_whisper_cli",
                new_callable=AsyncMock,
                return_value="Student question about homework",
            ),
        ):
            result = _run(transcribe_audio(audio))
            assert result == "Student question about homework"


# ── _transcribe_attachments (via openclaw_plugin) ──────────────────


class TestTranscribeAttachments:
    def test_transcribe_audio_attachments(self, tmp_path):
        from eduagent.openclaw_plugin import _transcribe_attachments

        audio = tmp_path / "voice.ogg"
        audio.write_bytes(b"OggS" + b"\x00" * 100)

        with patch(
            "eduagent.voice.transcribe_audio",
            new_callable=AsyncMock,
            return_value="transcribed text",
        ):
            result = _run(_transcribe_attachments([str(audio)]))
            assert result == "transcribed text"

    def test_skip_non_audio_attachments(self, tmp_path):
        from eduagent.openclaw_plugin import _transcribe_attachments

        pdf = tmp_path / "lesson.pdf"
        pdf.write_bytes(b"%PDF" + b"\x00" * 100)

        result = _run(_transcribe_attachments([str(pdf)]))
        assert result == ""

    def test_mixed_attachments(self, tmp_path):
        from eduagent.openclaw_plugin import _transcribe_attachments

        audio = tmp_path / "voice.m4a"
        audio.write_bytes(b"\x00" * 100)
        doc = tmp_path / "notes.docx"
        doc.write_bytes(b"\x00" * 100)

        with patch(
            "eduagent.voice.transcribe_audio",
            new_callable=AsyncMock,
            return_value="voice content",
        ):
            result = _run(_transcribe_attachments([str(audio), str(doc)]))
            assert result == "voice content"

    def test_failed_transcription_skipped(self, tmp_path):
        from eduagent.openclaw_plugin import _transcribe_attachments

        audio = tmp_path / "bad.wav"
        audio.write_bytes(b"\x00" * 100)

        with patch(
            "eduagent.voice.transcribe_audio",
            new_callable=AsyncMock,
            side_effect=RuntimeError("backend failed"),
        ):
            result = _run(_transcribe_attachments([str(audio)]))
            assert result == ""

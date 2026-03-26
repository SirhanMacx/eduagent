"""Tests for clawed.drive — Google Drive folder ingestion."""

from __future__ import annotations

import asyncio
import tempfile
import zipfile
from pathlib import Path

import pytest

from clawed.drive import extract_folder_id, ingest_drive_zip


def _run(coro):
    """Run an async coroutine synchronously for testing."""
    return asyncio.run(coro)


class TestExtractFolderId:
    def test_standard_url(self):
        url = "https://drive.google.com/drive/folders/1ABCdef_GHI-jkl"
        assert extract_folder_id(url) == "1ABCdef_GHI-jkl"

    def test_url_with_sharing_param(self):
        url = "https://drive.google.com/drive/folders/1ABCdef_GHI-jkl?usp=sharing"
        assert extract_folder_id(url) == "1ABCdef_GHI-jkl"

    def test_url_with_user_path(self):
        url = "https://drive.google.com/drive/u/0/folders/1ABCdef_GHI-jkl"
        assert extract_folder_id(url) == "1ABCdef_GHI-jkl"

    def test_open_id_format(self):
        url = "https://drive.google.com/open?id=1ABCdef_GHI-jkl"
        assert extract_folder_id(url) == "1ABCdef_GHI-jkl"

    def test_invalid_url(self):
        assert extract_folder_id("https://example.com/not-a-drive-link") is None

    def test_empty_string(self):
        assert extract_folder_id("") is None

    def test_plain_text(self):
        assert extract_folder_id("my google drive folder") is None


class TestIngestDriveZip:
    def test_ingest_zip_with_txt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "lessons.zip"
            with zipfile.ZipFile(str(zip_path), "w") as zf:
                zf.writestr("lesson1.txt", "Today we will learn about fractions.")
                zf.writestr("lesson2.txt", "Photosynthesis converts light energy to chemical energy.")
            docs = ingest_drive_zip(zip_path)
            assert len(docs) == 2
            titles = {d.title.lower() for d in docs}
            assert "lesson1" in titles or "lesson 1" in titles

    def test_ingest_zip_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            ingest_drive_zip("/tmp/does_not_exist_edu_test.zip")

    def test_ingest_zip_not_a_zip(self):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"this is not a zip file")
            f.flush()
            with pytest.raises(ValueError, match="Not a valid ZIP"):
                ingest_drive_zip(f.name)

    def test_ingest_zip_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "empty.zip"
            with zipfile.ZipFile(str(zip_path), "w") as zf:
                zf.writestr("image.png", b"\x89PNG fake image data")
            docs = ingest_drive_zip(zip_path)
            assert docs == []


class TestIngestDriveFolder:
    def test_invalid_url_raises(self):
        from clawed.drive import ingest_drive_folder

        with pytest.raises(ValueError, match="Could not parse"):
            _run(ingest_drive_folder("https://example.com/not-drive"))


class TestDriveAuth:
    def test_token_save_and_load(self, tmp_path):
        from clawed.agent_core.drive.auth import load_token, save_token
        token_data = {
            "access_token": "ya29.abc",
            "refresh_token": "1//xyz",
            "expiry": "2026-04-01T00:00:00",
        }
        save_token(token_data, token_path=tmp_path / "drive_token.json")
        loaded = load_token(token_path=tmp_path / "drive_token.json")
        assert loaded["access_token"] == "ya29.abc"

    def test_load_token_missing(self, tmp_path):
        from clawed.agent_core.drive.auth import load_token
        result = load_token(token_path=tmp_path / "nonexistent.json")
        assert result is None

    def test_is_authenticated(self, tmp_path):
        from clawed.agent_core.drive.auth import is_authenticated, save_token
        assert not is_authenticated(token_path=tmp_path / "nope.json")
        save_token(
            {"access_token": "test", "refresh_token": "test"},
            token_path=tmp_path / "token.json",
        )
        assert is_authenticated(token_path=tmp_path / "token.json")


class TestRateLimiter:
    def test_allows_initial(self):
        from clawed.agent_core.drive.client import RateLimiter
        rl = RateLimiter(max_per_hour=100)
        assert rl.allow()

    def test_blocks_excess(self):
        from clawed.agent_core.drive.client import RateLimiter
        rl = RateLimiter(max_per_hour=2)
        assert rl.allow()
        assert rl.allow()
        assert not rl.allow()


class TestDriveClient:
    @pytest.mark.asyncio
    async def test_not_authenticated(self, tmp_path):
        from clawed.agent_core.drive.client import DriveClient
        client = DriveClient(token_path=tmp_path / "nope.json")
        with pytest.raises(RuntimeError, match="not authenticated"):
            await client.list_files()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, tmp_path):
        from clawed.agent_core.drive.auth import save_token
        from clawed.agent_core.drive.client import DriveClient
        # Create a token so auth check passes
        save_token({"access_token": "test", "refresh_token": "test"},
                   token_path=tmp_path / "token.json")
        client = DriveClient(token_path=tmp_path / "token.json", max_per_hour=0)
        with pytest.raises(RuntimeError, match="rate limit"):
            await client.list_files()

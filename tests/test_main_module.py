"""Tests for the __main__ entry point module."""
from unittest.mock import MagicMock, patch

from clawed.__main__ import _handle_error, main


def test_handle_error_connection_error():
    """ConnectionError shows Ollama hint."""
    err = ConnectionError("refused")
    with patch("rich.console.Console") as mock_cls:
        console = MagicMock()
        mock_cls.return_value = console
        _handle_error(err)
        call_text = console.print.call_args_list[0][0][0]
        assert "AI model" in call_text


def test_handle_error_file_not_found():
    """FileNotFoundError shows path."""
    err = FileNotFoundError("/tmp/missing.txt")
    with patch("rich.console.Console") as mock_cls:
        console = MagicMock()
        mock_cls.return_value = console
        _handle_error(err)
        call_text = console.print.call_args_list[0][0][0]
        assert "File not found" in call_text


def test_handle_error_auth_401():
    """401 in message shows auth hint."""
    err = RuntimeError("HTTP 401 Unauthorized")
    with patch("rich.console.Console") as mock_cls:
        console = MagicMock()
        mock_cls.return_value = console
        _handle_error(err)
        call_text = console.print.call_args_list[0][0][0]
        assert "Authentication" in call_text


def test_handle_error_model_not_found():
    """404 with model in message shows model hint."""
    err = RuntimeError("404 model not found")
    with patch("rich.console.Console") as mock_cls:
        console = MagicMock()
        mock_cls.return_value = console
        _handle_error(err)
        call_text = console.print.call_args_list[0][0][0]
        assert "Model not found" in call_text


def test_handle_error_generic():
    """Unknown error shows generic message."""
    err = RuntimeError("something weird")
    with patch("rich.console.Console") as mock_cls:
        console = MagicMock()
        mock_cls.return_value = console
        _handle_error(err)
        call_text = console.print.call_args_list[0][0][0]
        assert "something weird" in call_text


def test_handle_error_validation_error():
    """ValidationError shows retry hint."""
    err = type("ValidationError", (Exception,), {})("bad data")
    with patch("rich.console.Console") as mock_cls:
        console = MagicMock()
        mock_cls.return_value = console
        _handle_error(err)
        call_text = console.print.call_args_list[0][0][0]
        assert "unexpected data" in call_text


def test_main_handles_keyboard_interrupt():
    """main() catches KeyboardInterrupt and exits with 130."""
    import pytest

    with patch("clawed._entry_router.main", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 130


def test_main_handles_generic_exception():
    """main() catches generic exceptions and calls _handle_error."""
    with patch("clawed._entry_router.main", side_effect=RuntimeError("boom")):
        import pytest
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

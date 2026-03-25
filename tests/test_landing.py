"""Tests for the landing page."""

from pathlib import Path


class TestLandingPage:
    def test_landing_page_exists(self):
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        assert landing.exists()

    def test_landing_page_has_required_content(self):
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        content = landing.read_text()
        # Required elements from spec
        assert "Your AI co-teacher that sounds like you" in content
        assert "Claw-ED" in content
        assert "waitlist-form" in content or "install-steps" in content  # install steps or form
        assert "github.com/SirhanMacx/Claw-ED" in content  # GitHub link
        assert "Open Source" in content

    def test_landing_page_is_self_contained(self):
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        content = landing.read_text()
        assert "<style>" in content  # inline CSS
        assert "<!DOCTYPE html>" in content

    def test_landing_page_mobile_responsive(self):
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        content = landing.read_text()
        assert "viewport" in content
        assert "width=device-width" in content

    def test_landing_page_dark_theme(self):
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        content = landing.read_text()
        # Dark background colors
        assert "#0f0f1a" in content or "#1a1a2e" in content or "#16213e" in content

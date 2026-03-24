"""Tests for the landing page."""

from pathlib import Path


class TestLandingPage:
    def test_landing_page_exists(self):
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        assert landing.exists()

    def test_landing_page_has_required_content(self):
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        content = landing.read_text()
        # Required elements from spec
        assert "Your AI co-teacher that sounds like you" in content
        assert "EDUagent" in content
        assert "waitlist-form" in content  # email capture form (Netlify Forms)
        assert "github.com/SirhanMacx/eduagent" in content  # GitHub link
        assert "Open Source" in content

    def test_landing_page_is_self_contained(self):
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        content = landing.read_text()
        assert "<style>" in content  # inline CSS
        assert "<!DOCTYPE html>" in content

    def test_landing_page_mobile_responsive(self):
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        content = landing.read_text()
        assert "viewport" in content
        assert "width=device-width" in content

    def test_landing_page_dark_theme(self):
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        content = landing.read_text()
        # Dark background colors
        assert "#0f0f1a" in content or "#1a1a2e" in content or "#16213e" in content

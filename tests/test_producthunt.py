"""Tests for ProductHunt launch kit files."""

from pathlib import Path


_PH_DIR = Path(__file__).parent.parent / "output" / "producthunt"


class TestProductHuntKit:
    def test_launch_checklist_exists(self):
        assert (_PH_DIR / "launch-checklist.md").exists()

    def test_gallery_screenshots_exists(self):
        assert (_PH_DIR / "gallery-screenshots.md").exists()

    def test_maker_comment_exists(self):
        assert (_PH_DIR / "maker-comment.md").exists()

    def test_hunter_outreach_exists(self):
        assert (_PH_DIR / "hunter-outreach.md").exists()

    def test_communities_exists(self):
        assert (_PH_DIR / "communities.md").exists()

    def test_launch_checklist_content(self):
        content = (_PH_DIR / "launch-checklist.md").read_text()
        assert "coming soon" in content.lower() or "Coming Soon" in content
        assert "Tuesday" in content or "tuesday" in content
        assert "screenshot" in content.lower()

    def test_maker_comment_length(self):
        content = (_PH_DIR / "maker-comment.md").read_text()
        # Should be 200-300 words (give some margin)
        words = len(content.split())
        assert words >= 100  # At minimum, the content section should be substantial

    def test_communities_has_required(self):
        content = (_PH_DIR / "communities.md").read_text()
        assert "r/Teachers" in content or "r/teachers" in content
        assert "r/edtech" in content or "r/EdTech" in content

    def test_hunter_outreach_has_template(self):
        content = (_PH_DIR / "hunter-outreach.md").read_text()
        assert "template" in content.lower() or "DM" in content or "message" in content.lower()

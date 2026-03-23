"""Tests for waitlist manager and email capture."""

import pytest

from eduagent.waitlist import WaitlistManager


@pytest.fixture
def wm(tmp_path):
    """Create a temporary WaitlistManager for testing."""
    mgr = WaitlistManager(tmp_path / "test.db")
    yield mgr
    mgr.close()


class TestWaitlistManager:
    def test_add_signup(self, wm):
        wm.add_signup("teacher@school.edu")
        assert wm.count() == 1

    def test_add_signup_with_role(self, wm):
        wm.add_signup("admin@school.edu", role="admin", notes="District admin")
        signups = wm.list_all()
        assert len(signups) == 1
        assert signups[0]["role"] == "admin"
        assert signups[0]["notes"] == "District admin"

    def test_duplicate_email_ignored(self, wm):
        wm.add_signup("teacher@school.edu")
        wm.add_signup("teacher@school.edu")
        assert wm.count() == 1

    def test_multiple_signups(self, wm):
        wm.add_signup("teacher1@school.edu")
        wm.add_signup("teacher2@school.edu")
        wm.add_signup("teacher3@school.edu")
        assert wm.count() == 3

    def test_invalid_email_raises(self, wm):
        with pytest.raises(ValueError, match="Invalid email"):
            wm.add_signup("not-an-email")

    def test_invalid_email_no_dot(self, wm):
        with pytest.raises(ValueError, match="Invalid email"):
            wm.add_signup("user@localhost")

    def test_list_all(self, wm):
        wm.add_signup("a@b.com", role="teacher")
        wm.add_signup("c@d.com", role="admin")
        result = wm.list_all()
        assert len(result) == 2
        emails = {r["email"] for r in result}
        assert emails == {"a@b.com", "c@d.com"}

    def test_export_csv(self, wm, tmp_path):
        wm.add_signup("teacher@school.edu")
        wm.add_signup("admin@school.edu", role="admin")
        csv_path = tmp_path / "export.csv"
        wm.export_csv(csv_path)
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "teacher@school.edu" in content
        assert "admin@school.edu" in content
        assert "email" in content  # header

    def test_count_empty(self, wm):
        assert wm.count() == 0

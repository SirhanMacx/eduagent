"""Tests for NLAH validation gates."""

from unittest.mock import MagicMock

from clawed.validation import validate_master_content


def _make_mc(
    guided_notes=6,
    exit_tickets=3,
    sources=2,
    instruction=1,
    topic="French Revolution",
):
    """Build a mock MasterContent with configurable counts."""
    mc = MagicMock()
    mc.title = f"The {topic}"
    mc.topic = topic
    mc.objective = f"Students will analyze the {topic}"
    mc.guided_notes = [MagicMock() for _ in range(guided_notes)]
    mc.exit_ticket = []
    for _ in range(exit_tickets):
        q = MagicMock()
        q.stimulus.strip.return_value = "stimulus text"
        q.question = "What happened?"
        mc.exit_ticket.append(q)
    mc.primary_sources = []
    for _ in range(sources):
        s = MagicMock()
        s.content_text.strip.return_value = "Source text here"
        mc.primary_sources.append(s)
    mc.direct_instruction = [MagicMock() for _ in range(instruction)]
    return mc


class TestNLAHGates:
    def test_valid_mc_passes(self):
        """A well-formed MasterContent produces no errors."""
        mc = _make_mc()
        errors = validate_master_content(mc, "French Revolution")
        assert len(errors) == 0

    def test_guided_notes_below_minimum(self):
        """Fewer than 6 guided notes triggers a CRITICAL error."""
        mc = _make_mc(guided_notes=3)
        errors = validate_master_content(mc, "French Revolution")
        assert any("CRITICAL" in e and "Guided notes" in e for e in errors)

    def test_exit_ticket_below_minimum(self):
        """Fewer than 3 exit tickets triggers a CRITICAL error."""
        mc = _make_mc(exit_tickets=1)
        errors = validate_master_content(mc, "French Revolution")
        assert any("CRITICAL" in e and "Exit ticket" in e for e in errors)

    def test_primary_sources_below_minimum(self):
        """Fewer than 2 primary sources triggers a CRITICAL error."""
        mc = _make_mc(sources=1)
        errors = validate_master_content(mc, "French Revolution")
        assert any("CRITICAL" in e and "Primary sources" in e for e in errors)

    def test_topic_drift_detected(self):
        """Topic not present in title, topic, or objective triggers TOPIC_DRIFT."""
        mc = _make_mc(topic="French Revolution")
        mc.title = "Ancient Egypt"
        mc.topic = "Ancient Egypt"
        mc.objective = "Students will learn about pyramids"
        errors = validate_master_content(mc, "French Revolution")
        assert any("TOPIC_DRIFT" in e for e in errors)

    def test_topic_in_objective_no_drift(self):
        """Topic in objective but not title should NOT trigger drift."""
        mc = _make_mc(topic="Test")
        mc.title = "Unit 5 Lesson"
        mc.topic = "Unit 5"
        mc.objective = "Students will analyze the French Revolution"
        errors = validate_master_content(mc, "French Revolution")
        assert not any("TOPIC_DRIFT" in e for e in errors)

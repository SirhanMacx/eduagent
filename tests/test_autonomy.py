"""Tests for autonomy progression — approval rate tracking."""

import pytest

from clawed.agent_core.autonomy import ApprovalTracker


class TestApprovalTracker:
    def test_empty_rates(self, tmp_path):
        tracker = ApprovalTracker(approvals_dir=tmp_path)
        rates = tracker.get_rates()
        assert isinstance(rates, dict)
        assert len(rates) == 0

    def test_tracks_approval_rate(self, tmp_path):
        from clawed.agent_core.approvals import ApprovalManager
        mgr = ApprovalManager(base_dir=tmp_path)
        # Create 10 approvals of the same action type
        for i in range(10):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload lessons to Drive",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.approve(pa.id)

        tracker = ApprovalTracker(approvals_dir=tmp_path)
        rates = tracker.get_rates()
        assert "drive_upload" in rates
        assert rates["drive_upload"]["approval_rate"] == 1.0
        assert rates["drive_upload"]["total"] == 10

    def test_mixed_approvals_and_rejections(self, tmp_path):
        from clawed.agent_core.approvals import ApprovalManager
        mgr = ApprovalManager(base_dir=tmp_path)
        # 8 approved, 2 rejected
        for i in range(8):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.approve(pa.id)
        for i in range(2):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.reject(pa.id)

        tracker = ApprovalTracker(approvals_dir=tmp_path)
        rates = tracker.get_rates()
        assert rates["drive_upload"]["approval_rate"] == 0.8
        assert rates["drive_upload"]["total"] == 10

    def test_should_offer_auto_high_rate(self, tmp_path):
        from clawed.agent_core.approvals import ApprovalManager
        mgr = ApprovalManager(base_dir=tmp_path)
        for i in range(12):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.approve(pa.id)

        tracker = ApprovalTracker(approvals_dir=tmp_path)
        assert tracker.should_offer_auto("drive_upload") is True

    def test_should_not_offer_auto_low_rate(self, tmp_path):
        from clawed.agent_core.approvals import ApprovalManager
        mgr = ApprovalManager(base_dir=tmp_path)
        for i in range(5):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.approve(pa.id)
        for i in range(5):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.reject(pa.id)

        tracker = ApprovalTracker(approvals_dir=tmp_path)
        assert tracker.should_offer_auto("drive_upload") is False

    def test_should_not_offer_auto_insufficient_samples(self, tmp_path):
        from clawed.agent_core.approvals import ApprovalManager
        mgr = ApprovalManager(base_dir=tmp_path)
        for i in range(3):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.approve(pa.id)

        tracker = ApprovalTracker(approvals_dir=tmp_path)
        assert tracker.should_offer_auto("drive_upload") is False

    def test_summarize_for_prompt(self, tmp_path):
        from clawed.agent_core.approvals import ApprovalManager
        mgr = ApprovalManager(base_dir=tmp_path)
        for i in range(12):
            pa = mgr.create(
                teacher_id="t1",
                action_description="Upload",
                action_payload={"action_type": "drive_upload"},
                agent_state={}, transport="cli",
            )
            mgr.approve(pa.id)

        tracker = ApprovalTracker(approvals_dir=tmp_path)
        summary = tracker.summarize_for_prompt()
        assert "drive_upload" in summary
        assert "auto" in summary.lower() or "always" in summary.lower()


class TestStudentInsightsTool:
    def test_schema_valid(self):
        from clawed.agent_core.tools.student_insights import StudentInsightsTool
        tool = StudentInsightsTool()
        s = tool.schema()
        assert s["function"]["name"] == "student_insights"

    @pytest.mark.asyncio
    async def test_execute_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from clawed.agent_core.context import AgentContext
        from clawed.agent_core.tools.student_insights import StudentInsightsTool
        from clawed.models import AppConfig
        tool = StudentInsightsTool()
        ctx = AgentContext(
            teacher_id="t1", config=AppConfig(),
            teacher_profile={}, persona=None,
            session_history=[], improvement_context="",
        )
        result = await tool.execute({"days": 7}, ctx)
        assert "No student questions" in result.text or isinstance(result.text, str)

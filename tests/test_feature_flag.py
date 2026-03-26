"""Tests for feature flag routing between legacy and agent gateway."""
from clawed.models import AppConfig


class TestFeatureFlag:
    def test_flag_defaults_to_false(self):
        cfg = AppConfig()
        assert cfg.agent_gateway is False

    def test_legacy_gateway_when_flag_off(self):
        from clawed.gateway import Gateway
        gw = Gateway(config=AppConfig(agent_gateway=False))
        assert gw.__class__.__module__ == "clawed._legacy_gateway"

    def test_shim_reexports_compat_names(self):
        from clawed.gateway import ActivityEvent, EduAgentGateway, GatewayStats
        assert EduAgentGateway is not None
        assert ActivityEvent is not None
        assert GatewayStats is not None

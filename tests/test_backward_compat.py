"""Tests that the old eduagent imports still work after rename to clawed."""
import pytest


class TestBackwardCompat:
    def test_import_clawed_package(self):
        import clawed
        assert hasattr(clawed, "__version__")

    def test_import_eduagent_package(self):
        import eduagent
        assert hasattr(eduagent, "__version__")

    def test_versions_match(self):
        import clawed
        import eduagent
        assert clawed.__version__ == eduagent.__version__

    def test_import_submodule_via_eduagent(self):
        from eduagent.models import AppConfig
        from clawed.models import AppConfig as ClawedAppConfig
        assert AppConfig is ClawedAppConfig

    def test_import_gateway_via_eduagent(self):
        from eduagent.gateway import Gateway
        from clawed.gateway import Gateway as ClawedGateway
        assert Gateway is ClawedGateway

    def test_import_gateway_response_via_eduagent(self):
        from eduagent.gateway_response import GatewayResponse, Button
        assert GatewayResponse is not None
        assert Button is not None

    def test_import_handler_via_eduagent(self):
        from eduagent.handlers.onboard import OnboardHandler
        from clawed.handlers.onboard import OnboardHandler as ClawedOnboard
        assert OnboardHandler is ClawedOnboard

    def test_import_router_via_eduagent(self):
        from eduagent.router import Intent, parse_intent
        from clawed.router import Intent as ClawedIntent
        assert Intent is ClawedIntent

    def test_import_io_functions_from_eduagent(self):
        from eduagent import output_dir, safe_filename
        assert callable(safe_filename)

    def test_import_deep_submodule(self):
        from eduagent.handlers.generate import GenerateHandler
        from clawed.handlers.generate import GenerateHandler as CG
        assert GenerateHandler is CG

    def test_import_skills_subpackage(self):
        from eduagent.skills.base import SubjectSkill
        from clawed.skills.base import SubjectSkill as CS
        assert SubjectSkill is CS

    @pytest.mark.xfail(
        reason="Pre-existing circular import in clawed.api (server <-> routes.chat); not a shim issue",
        raises=ImportError,
    )
    def test_import_api_routes(self):
        from eduagent.api.routes.chat import router
        from clawed.api.routes.chat import router as cr
        assert router is cr

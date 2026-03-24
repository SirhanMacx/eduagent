"""Import hook that redirects eduagent.* imports to clawed.* modules.

This allows all existing code that does ``from eduagent.X import Y``
to transparently work after the package rename to Claw-ED (clawed).
"""
from __future__ import annotations

import importlib
import sys
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec


class _EduagentRedirectFinder(MetaPathFinder):
    """Intercepts ``import eduagent.X`` and redirects to ``import clawed.X``."""

    _PREFIX = "eduagent."

    def find_module(self, fullname, path=None):
        if fullname == "eduagent" or fullname.startswith(self._PREFIX):
            return self
        return None

    def find_spec(self, fullname, path, target=None):
        if fullname == "eduagent":
            return None  # Let the real eduagent/__init__.py load normally
        if fullname.startswith(self._PREFIX):
            clawed_name = "clawed" + fullname[len("eduagent"):]
            return ModuleSpec(fullname, _EduagentRedirectLoader(clawed_name))
        return None


class _EduagentRedirectLoader(Loader):
    """Loads the clawed.* module and installs it as eduagent.* too."""

    def __init__(self, clawed_name: str):
        self._clawed_name = clawed_name

    def create_module(self, spec):
        return None  # Use default semantics

    def exec_module(self, module):
        real = importlib.import_module(self._clawed_name)
        module.__dict__.update(real.__dict__)
        module.__spec__ = real.__spec__
        module.__loader__ = self
        module.__path__ = getattr(real, "__path__", [])
        module.__file__ = getattr(real, "__file__", None)
        sys.modules[module.__name__] = module


def install():
    """Install the import redirect hook. Idempotent."""
    for finder in sys.meta_path:
        if isinstance(finder, _EduagentRedirectFinder):
            return
    sys.meta_path.insert(0, _EduagentRedirectFinder())

#!/bin/bash
set -euo pipefail

# Build and publish Claw-ED to PyPI
# Usage: ./scripts/publish.sh
#
# Requires: pip install build twine

echo "==> Claw-ED PyPI Publisher"
echo ""

# ── Check dist/ ──────────────────────────────────────────────────────────────

if [[ ! -d dist/ ]] || [[ -z "$(ls -A dist/ 2>/dev/null)" ]]; then
    echo "No dist/ found. Building package first..."
    python3 -m build
fi

# Verify wheel and tarball exist
WHEEL=$(ls dist/*.whl 2>/dev/null | head -1)
TARBALL=$(ls dist/*.tar.gz 2>/dev/null | head -1)

if [[ -z "$WHEEL" || -z "$TARBALL" ]]; then
    echo "✗ Missing wheel or tarball in dist/. Rebuilding..."
    rm -rf dist/ build/ *.egg-info/
    python3 -m build
fi

echo "✓ Found artifacts:"
ls -1 dist/

# ── PyPI credentials ─────────────────────────────────────────────────────────

# Use API token auth (recommended by PyPI)
TWINE_ARGS=("--username" "__token__")

if [[ -z "${TWINE_PASSWORD:-}" ]]; then
    echo ""
    echo "PyPI API token not found in env (TWINE_PASSWORD)."
    echo "Get one at: https://pypi.org/manage/account/token/"
    read -rsp "Enter PyPI API token (starts with pypi-): " TWINE_PASSWORD
    echo ""
    export TWINE_PASSWORD
fi

# ── Upload ────────────────────────────────────────────────────────────────────

echo ""
echo "Uploading to PyPI..."
python3 -m twine upload dist/* "${TWINE_ARGS[@]}"

echo ""
echo "✓ Upload complete! https://pypi.org/project/clawed/"

# ── Bump version for next dev cycle ──────────────────────────────────────────

CURRENT=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
NEXT="${MAJOR}.${MINOR}.$((PATCH + 1))"

echo ""
read -rp "Bump version to ${NEXT} for next release? [Y/n] " bump
if [[ "${bump:-Y}" =~ ^[Yy]$ ]]; then
    sed -i.bak "s/^version = \"${CURRENT}\"/version = \"${NEXT}\"/" pyproject.toml
    sed -i.bak "s/^__version__ = \"${CURRENT}\"/__version__ = \"${NEXT}\"/" clawed/__init__.py
    rm -f pyproject.toml.bak clawed/__init__.py.bak
    echo "✓ Version bumped to ${NEXT}"

    echo "Rebuilding with new version..."
    rm -rf dist/ build/ *.egg-info/
    python3 -m build
    echo "✓ Rebuilt dist/ with v${NEXT}"
fi

echo ""
echo "Done!"

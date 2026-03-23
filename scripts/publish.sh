#!/bin/bash
set -euo pipefail

# Build and publish EDUagent to PyPI
# Usage: ./scripts/publish.sh
#
# Requires: pip install build twine
# Set TWINE_USERNAME and TWINE_PASSWORD (or use ~/.pypirc)

echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

echo "Building package..."
python -m build

echo "Uploading to PyPI..."
twine upload dist/*

echo "Done! Check https://pypi.org/project/eduagent/"

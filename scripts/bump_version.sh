#!/bin/bash
set -euo pipefail

# Bump EDUagent version in pyproject.toml and __init__.py
# Usage: ./scripts/bump_version.sh 0.2.0

if [ $# -ne 1 ]; then
    echo "Usage: $0 <new-version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

NEW_VERSION="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Validate semver format
if ! echo "$NEW_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: Version must be semver (e.g., 0.2.0)"
    exit 1
fi

# Update pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" "$ROOT/pyproject.toml"

# Update __init__.py
sed -i '' "s/^__version__ = \".*\"/__version__ = \"${NEW_VERSION}\"/" "$ROOT/eduagent/__init__.py"

echo "Bumped version to ${NEW_VERSION}"
echo "  - pyproject.toml"
echo "  - eduagent/__init__.py"

#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MOD_DIR="${HOME}/.local/share/FreeCAD/Mod"
LINK_PATH="$MOD_DIR/freecad-agent"
TARGET="$REPO_ROOT/freecad"

mkdir -p "$MOD_DIR"

if [ -e "$LINK_PATH" ] && [ ! -L "$LINK_PATH" ]; then
    echo "[freecad-agent] refusing to replace existing path: $LINK_PATH" >&2
    exit 1
fi

ln -sfn "$TARGET" "$LINK_PATH"

echo "[freecad-agent] FreeCAD startup module installed"
echo "  repo : $TARGET"
echo "  link : $LINK_PATH"
echo
echo "Restart FreeCAD to load the listener automatically."

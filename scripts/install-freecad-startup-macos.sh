#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# FreeCAD 1.x on macOS may use a versioned user-data directory such as
# ~/Library/Application Support/FreeCAD/v1-1/. Do not hard-code it.
# Ask the installed FreeCAD binary for the authoritative path instead.
FREECAD_BIN=""

for candidate in \
    "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD" \
    "$(command -v FreeCAD 2>/dev/null || true)" \
    "$(command -v freecad 2>/dev/null || true)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        FREECAD_BIN="$candidate"
        break
    fi
done

if [ -z "$FREECAD_BIN" ]; then
    echo "[freecad-agent] FreeCAD executable not found" >&2
    echo "Install FreeCAD or set it on PATH, then rerun this script." >&2
    exit 1
fi

USER_APP_DATA="$("$FREECAD_BIN" --get-config UserAppData 2>/dev/null | tail -n 1 | sed 's/[[:space:]]*$//')"

if [ -z "$USER_APP_DATA" ] || [ ! -d "$USER_APP_DATA" ]; then
    echo "[freecad-agent] could not resolve FreeCAD UserAppData" >&2
    echo "  binary: $FREECAD_BIN" >&2
    echo "  value : ${USER_APP_DATA:-<empty>}" >&2
    echo "Run FreeCAD once and verify App.getUserAppDataDir() from its Python console." >&2
    exit 1
fi

MOD_DIR="$USER_APP_DATA/Mod"
LINK_PATH="$MOD_DIR/freecad-agent"
TARGET="$REPO_ROOT/freecad"

mkdir -p "$MOD_DIR"

if [ -e "$LINK_PATH" ] && [ ! -L "$LINK_PATH" ]; then
    echo "[freecad-agent] refusing to replace existing path: $LINK_PATH" >&2
    exit 1
fi

ln -sfn "$TARGET" "$LINK_PATH"

echo "[freecad-agent] macOS startup module installed"
echo "  repo : $TARGET"
echo "  link : $LINK_PATH"
echo "  data : $USER_APP_DATA"
echo
echo "Restart FreeCAD to load the listener automatically."

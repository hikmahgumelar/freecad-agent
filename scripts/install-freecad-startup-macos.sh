#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# FreeCAD 1.x on macOS uses a versioned user-data directory such as:
#   ~/Library/Application Support/FreeCAD/v1-1/
# Use FreeCADCmd when available because the GUI binary may print launcher
# diagnostics instead of returning the requested config value.
FREECAD_CMD=""

for candidate in \
    "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd" \
    "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD" \
    "$(command -v FreeCADCmd 2>/dev/null || true)" \
    "$(command -v freecadcmd 2>/dev/null || true)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        FREECAD_CMD="$candidate"
        break
    fi
done

if [ -z "$FREECAD_CMD" ]; then
    echo "[freecad-agent] FreeCAD command-line executable not found" >&2
    echo "Expected /Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd" >&2
    exit 1
fi

USER_APP_DATA=""

# FreeCADCmd can evaluate Python without opening the GUI. Prefer the API
# itself over guessing the versioned directory name.
if [[ "$(basename "$FREECAD_CMD")" == "FreeCADCmd" ]]; then
    USER_APP_DATA="$("$FREECAD_CMD" -c 'import FreeCAD as App; print(App.getUserAppDataDir())' 2>/dev/null | tail -n 1 | sed 's/[[:space:]]*$//')"
fi

# Fallback for installations where the command-line binary does not support
# the -c invocation as expected. The user-data directory is created by
# FreeCAD on first launch and is normally the only v* directory here.
if [ -z "$USER_APP_DATA" ] || [ ! -d "$USER_APP_DATA" ]; then
    BASE_DIR="$HOME/Library/Application Support/FreeCAD"
    if [ -d "$BASE_DIR" ]; then
        USER_APP_DATA="$(find "$BASE_DIR" -maxdepth 1 -type d -name 'v*' -print | sort | tail -n 1)"
    fi
fi

if [ -z "$USER_APP_DATA" ] || [ ! -d "$USER_APP_DATA" ]; then
    echo "[freecad-agent] could not resolve FreeCAD UserAppData" >&2
    echo "  command: $FREECAD_CMD" >&2
    echo "Run FreeCAD once, then rerun this script." >&2
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

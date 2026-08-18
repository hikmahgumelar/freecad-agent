#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$(uname -s)" in
    Darwin)
        exec "$SCRIPT_DIR/install-freecad-startup-macos.sh" "$@"
        ;;
    Linux)
        exec "$SCRIPT_DIR/install-freecad-startup-linux.sh" "$@"
        ;;
    *)
        echo "[freecad-agent] unsupported OS: $(uname -s)" >&2
        echo "Use the Linux or macOS installer explicitly when applicable." >&2
        exit 1
        ;;
esac

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$ROOT"

install_launcher() {
  local apps="$HOME/.local/share/applications"
  local desk="$HOME/Desktop"
  mkdir -p "$apps" "$HOME/.local/share/icons/hicolor/scalable/apps"
  cp -f "$ROOT/share/icon.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/do-something.svg"
  sed "s|@ROOT@|$ROOT|g" "$ROOT/share/do-something.desktop" > "$apps/do-something.desktop"
  chmod +x "$apps/do-something.desktop"
  if [[ -d "$desk" ]]; then
    sed "s|@ROOT@|$ROOT|g" "$ROOT/share/do-something.desktop" > "$desk/Do Something.desktop"
    chmod +x "$desk/Do Something.desktop"
    gio set "$desk/Do Something.desktop" metadata::trusted true 2>/dev/null || true
  fi
}

install_launcher || true
exec python3 "$ROOT/do_something.py" "$@"

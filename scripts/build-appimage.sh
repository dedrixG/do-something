#!/usr/bin/env bash
# Build a portable x86_64 AppImage.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
cd "$ROOT"

ARCH="$(uname -m)"
if [[ "$ARCH" != "x86_64" ]]; then
  echo "This script currently builds x86_64 AppImages (host is $ARCH)." >&2
  exit 1
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/do-something-build"
DIST="$ROOT/dist"
APPDIR="$DIST/AppDir"
SPEC="$ROOT/packaging/linux/do-something.spec"
DESKTOP="$ROOT/packaging/linux/do-something.desktop"
OUT="$DIST/Do_Something-x86_64.AppImage"
TOOL="$CACHE/appimagetool-x86_64.AppImage"

mkdir -p "$CACHE" "$DIST"

if ! "$PYTHON" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "Installing PyInstaller..." >&2
  "$PYTHON" -m pip install 'pyinstaller>=6'
fi

if [[ ! -f "$ROOT/share/icon-256.png" ]]; then
  magick -background none "$ROOT/share/icon.svg" -resize 256x256 "$ROOT/share/icon-256.png"
fi

echo "==> PyInstaller ($PYTHON)"
rm -rf "$ROOT/build/pyinstaller" "$DIST/do-something"
"$PYTHON" -m PyInstaller \
  --noconfirm \
  --distpath "$DIST" \
  --workpath "$ROOT/build/pyinstaller" \
  "$SPEC"

echo "==> AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" \
  "$APPDIR/usr/share/applications" \
  "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
  "$APPDIR/usr/share/icons/hicolor/scalable/apps"

cp -a "$DIST/do-something" "$APPDIR/usr/lib/do-something"
cat > "$APPDIR/usr/bin/do-something" << 'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/../lib/do-something/do-something" "$@"
EOF
chmod +x "$APPDIR/usr/bin/do-something"

install -m 644 "$DESKTOP" "$APPDIR/do-something.desktop"
install -m 644 "$DESKTOP" "$APPDIR/usr/share/applications/do-something.desktop"
install -m 644 "$ROOT/share/icon-256.png" "$APPDIR/do-something.png"
install -m 644 "$ROOT/share/icon-256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/do-something.png"
install -m 644 "$ROOT/share/icon.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/do-something.svg"

cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:${PATH:-}"
exec "$HERE/usr/lib/do-something/do-something" "$@"
EOF
chmod +x "$APPDIR/AppRun"

if [[ ! -x "$TOOL" ]]; then
  echo "==> downloading appimagetool"
  curl -fsSL -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$TOOL"
fi

echo "==> appimagetool"
if "$TOOL" --appimage-help >/dev/null 2>&1; then
  ARCH=x86_64 "$TOOL" "$APPDIR" "$OUT"
else
  EXTRACT="$CACHE/appimagetool-extracted"
  rm -rf "$EXTRACT"
  (
    cd "$CACHE"
    chmod +x "$TOOL"
    "$TOOL" --appimage-extract >/dev/null
    mv squashfs-root "$EXTRACT"
  )
  ARCH=x86_64 "$EXTRACT/AppRun" "$APPDIR" "$OUT"
fi

chmod +x "$OUT"
echo "Built $OUT"
ls -lh "$OUT"

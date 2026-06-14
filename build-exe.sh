#!/usr/bin/env bash
# Build PPD-Resume for Linux — run from project root
set -euo pipefail
cd "$(dirname "$0")"

echo "Installing build dependencies..."
python3 -m pip install -e . -q
python3 -m pip install pyinstaller -q

echo "Building executable..."
python3 -m PyInstaller ppd.spec --noconfirm --clean

DIST="dist/PPD-Resume"
TOOLS="$DIST/tools"
mkdir -p "$TOOLS" "$DIST/data/source" "$DIST/output"

if command -v typst >/dev/null 2>&1; then
  cp "$(command -v typst)" "$TOOLS/typst"
  chmod +x "$TOOLS/typst"
  echo "Bundled typst from PATH"
else
  echo "Typst not on PATH — downloading portable typst..."
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64) TYPST_ARCH="x86_64-unknown-linux-musl" ;;
    aarch64|arm64) TYPST_ARCH="aarch64-unknown-linux-musl" ;;
    *) echo "Unsupported arch: $ARCH"; exit 1 ;;
  esac
  curl -fsSL "https://github.com/typst/typst/releases/download/v0.14.2/typst-${TYPST_ARCH}.tar.xz" -o /tmp/typst.tar.xz
  rm -rf /tmp/typst-extract
  mkdir -p /tmp/typst-extract
  tar -xJf /tmp/typst.tar.xz -C /tmp/typst-extract
  TYPST_BIN="$(find /tmp/typst-extract -name typst -type f | head -1)"
  if [[ -z "$TYPST_BIN" ]]; then
    echo "Could not find typst binary in archive"; exit 1
  fi
  cp "$TYPST_BIN" "$TOOLS/typst"
  chmod +x "$TOOLS/typst"
  echo "Bundled typst from GitHub release"
fi

chmod +x "$DIST/PPD-Resume"

echo ""
echo "Done! Run:"
echo "  $DIST/PPD-Resume"
echo ""
echo "Copy the entire dist/PPD-Resume folder anywhere and run ./PPD-Resume"

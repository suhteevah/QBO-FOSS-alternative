#!/usr/bin/env bash
#
# build-sidecar.sh
#
# Builds the OpenLedger Python backend into a sidecar executable for Tauri
# on macOS and Linux.
#
#   1. Runs PyInstaller using desktop/pyinstaller.spec.
#   2. Detects the Rust target triple for the current machine.
#   3. Copies the binary into src-tauri/binaries/ with the triple suffix.
#
# Usage:
#   bash desktop/build-sidecar.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SPEC_FILE="$SCRIPT_DIR/pyinstaller.spec"
BIN_DIR="$SCRIPT_DIR/src-tauri/binaries"

# ── 1. Run PyInstaller ──────────────────────────────────────────────────────
echo "==> Building sidecar with PyInstaller ..."

(cd "$PROJECT_ROOT" && python3 -m PyInstaller --clean --noconfirm "$SPEC_FILE")

ARTIFACT="$PROJECT_ROOT/dist/openledger-server"
if [ ! -f "$ARTIFACT" ]; then
    echo "ERROR: PyInstaller did not produce $ARTIFACT" >&2
    exit 1
fi

# ── 2. Detect target triple ─────────────────────────────────────────────────
RUSTC_TARGET="$(rustc -vV | grep '^host:' | sed 's/^host: *//')"
if [ -z "$RUSTC_TARGET" ]; then
    # Fallback: guess from uname
    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64)  ARCH="x86_64" ;;
        aarch64) ARCH="aarch64" ;;
        arm64)   ARCH="aarch64" ;;
        *)       ARCH="$ARCH" ;;
    esac

    OS="$(uname -s)"
    case "$OS" in
        Darwin) RUSTC_TARGET="${ARCH}-apple-darwin" ;;
        Linux)  RUSTC_TARGET="${ARCH}-unknown-linux-gnu" ;;
        *)
            echo "ERROR: Unsupported OS: $OS" >&2
            exit 1
            ;;
    esac
    echo "WARNING: Could not detect Rust target triple, guessed: $RUSTC_TARGET"
fi

echo "==> Detected target triple: $RUSTC_TARGET"

# ── 3. Copy to Tauri binaries ───────────────────────────────────────────────
mkdir -p "$BIN_DIR"

DESTINATION="$BIN_DIR/openledger-server-${RUSTC_TARGET}"
cp -f "$ARTIFACT" "$DESTINATION"
chmod +x "$DESTINATION"

SIZE_MB="$(du -m "$DESTINATION" | cut -f1)"
echo "==> Sidecar ready: $DESTINATION"
echo "    Size: ${SIZE_MB} MB"

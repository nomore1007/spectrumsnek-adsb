#!/usr/bin/env bash
# Build and install SpectrumSnek's project-local readsb with RTL-SDR support.
set -Eeuo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="${SPECTRUMSNEK_ROOT:-$(cd "$PLUGIN_DIR/../.." && pwd)}"
SOURCE_DIR="$APP_ROOT/.local/src/readsb"
BIN_DIR="$APP_ROOT/.local/bin"
READSB_BIN="$BIN_DIR/readsb"
BUILD_MARKER="$BIN_DIR/readsb.rtlsdr-build"
FORCE_BUILD="${FORCE_READSB_BUILD:-0}"

log() { printf '[adsb_radar setup] %s\n' "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

# Avoid a lengthy rebuild on every plugin update. Binaries produced by this
# installer have a marker; unmarked binaries are rebuilt to repair old installs.
if [[ "$FORCE_BUILD" != "1" && -x "$READSB_BIN" && -f "$BUILD_MARKER" ]]; then
    log "RTL-SDR readsb is already installed at $READSB_BIN; skipping rebuild."
    exit 0
fi

run_root() {
    if [[ "$EUID" -eq 0 ]]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        die "Missing system build dependencies and neither root nor sudo is available."
    fi
}

# Core setup normally installs these packages. This also supports installing
# the add-on later through the plugin manager on an existing SpectrumSnek host.
if ! command -v git >/dev/null 2>&1 || \
   ! command -v make >/dev/null 2>&1 || \
   ! command -v pkg-config >/dev/null 2>&1 || \
   ! pkg-config --exists librtlsdr; then
    command -v apt-get >/dev/null 2>&1 || die "Install git, build-essential, pkg-config, librtlsdr-dev, libusb-1.0-0-dev, zlib1g-dev, and libncurses-dev first."
    log "Installing readsb build dependencies..."
    run_root apt-get update
    run_root apt-get install -y git build-essential pkg-config librtlsdr-dev libusb-1.0-0-dev zlib1g-dev libncurses-dev
fi

mkdir -p "$BIN_DIR" "$(dirname "$SOURCE_DIR")"

if [[ ! -d "$SOURCE_DIR/.git" ]]; then
    [[ ! -e "$SOURCE_DIR" ]] || die "$SOURCE_DIR exists but is not a Git checkout; move it aside and rerun setup."
    log "Cloning readsb source from https://github.com/wiedehopf/readsb.git..."
    git clone https://github.com/wiedehopf/readsb.git "$SOURCE_DIR"
else
    log "Updating existing readsb source checkout..."
    git -C "$SOURCE_DIR" pull --ff-only
fi

log "Cleaning readsb build..."
make -C "$SOURCE_DIR" clean

# Keep parallelism conservative for Raspberry Pi Zero 2 W and other low-RAM hosts.
log "Compiling readsb with RTLSDR=yes (up to two jobs)..."
make -C "$SOURCE_DIR" -j2 RTLSDR=yes

[[ -x "$SOURCE_DIR/readsb" ]] || die "Build finished without producing an executable readsb binary."

TEMP_BIN="$BIN_DIR/readsb.tmp.$$"
trap 'rm -f "$TEMP_BIN"' EXIT
install -m 0755 "$SOURCE_DIR/readsb" "$TEMP_BIN"
mv -f "$TEMP_BIN" "$READSB_BIN"
git -C "$SOURCE_DIR" rev-parse HEAD > "$BUILD_MARKER"
trap - EXIT

log "Installed RTL-SDR-enabled readsb at $READSB_BIN"
log "SpectrumSnek's SDR manager will prefer this binary over any system readsb."

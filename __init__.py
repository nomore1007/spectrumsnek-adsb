"""ADS-B radar plugin using readsb as the only ADS-B decoder."""

import argparse
import curses
import os
import subprocess
import sys
import time
import traceback

from sdr_manager import SDRManager, SDRBusyError, SDRUnavailableError
from . import radar


# Supported by both the legacy plugin loader and SpectrumSnek's shared
# backend (spectrum_core.discover_plugins).
MODULE_INFO = {
    "name": "✈️ ADS-B Radar",
    "description": "Live aircraft radar using readsb and the shared RTL-SDR manager",
    "version": "2.2.0",
    "author": "SpectrumSnek",
    "category": "radio",
    "capabilities": [
        "readsb-backed ADS-B",
        "terminal radar",
        "shared SDR ownership",
        "first-run RTL-SDR-enabled readsb build",
    ],
}


def get_module_info():
    """Return plugin metadata for legacy and current SpectrumSnek loaders."""
    return MODULE_INFO.copy()


def _log_error(message, exc_info=False):
    """Append plugin failures to SpectrumSnek's root error.log."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        with open(os.path.join(root, "error.log"), "a", encoding="utf-8") as log_file:
            log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [adsb_radar] {message}\n")
            if exc_info:
                log_file.write(traceback.format_exc())
                log_file.write("\n")
    except OSError as log_exc:
        print(f"ADS-B radar: unable to write error.log: {log_exc}; {message}", file=sys.stderr)


def _ensure_readsb():
    """Build the project-local RTL-SDR-enabled readsb on first use if needed."""
    # An explicit binary override is intentional; leave its configuration alone.
    if os.environ.get("READSB_BIN"):
        return

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    binary = os.path.join(root, ".local", "bin", "readsb")
    marker = os.path.join(root, ".local", "bin", "readsb.rtlsdr-build")
    setup_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup.sh")

    if os.path.isfile(binary) and os.access(binary, os.X_OK) and os.path.isfile(marker):
        return
    if not os.path.isfile(setup_script):
        raise RuntimeError(
            "The RTL-SDR-enabled readsb binary is missing and the plugin setup.sh "
            "is unavailable. Reinstall/update the ADS-B plugin."
        )

    print("ADS-B Radar: preparing an RTL-SDR-enabled readsb build (first run)...", flush=True)
    env = os.environ.copy()
    env["SPECTRUMSNEK_ROOT"] = root
    try:
        subprocess.run(["bash", setup_script], cwd=root, env=env, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"Could not build RTL-SDR-enabled readsb. See setup.log/error output. {exc}"
        ) from exc


def run(stdscr=None, *args, **kwargs):
    """Run the radar from SpectrumSnek's menu, service, or module entry point."""
    # The current menu launches plugins in a child process via plugin_menu.py.
    # Keep this argument compatibility for older callers that supply a curses
    # screen, while allowing the current run() contract (no required arguments).
    if stdscr is not None and not hasattr(stdscr, "getch"):
        stdscr = None

    owns_decoder = os.environ.get("SPECTRUMSNEK_EXTERNAL_READSB") != "1"
    try:
        # Build the native decoder before creating SDRManager, so it selects the
        # freshly installed project-local binary rather than an incompatible
        # system package. External JSON mode does not need a local build.
        if owns_decoder:
            _ensure_readsb()

        manager = SDRManager()
        json_path = os.environ.get(
            "SPECTRUMSNEK_AIRCRAFT_JSON",
            os.path.join(manager.json_dir, "aircraft.json"),
        )
        # An externally managed readsb can be reused by setting
        # SPECTRUMSNEK_EXTERNAL_READSB=1 and optionally SPECTRUMSNEK_AIRCRAFT_JSON.
        # In that mode the plugin never acquires or releases the SDR lock.
        if owns_decoder:
            try:
                json_path = manager.start_readsb()
            except (SDRUnavailableError, SDRBusyError) as exc:
                _log_error(f"SDR startup failed: {type(exc).__name__}: {exc}")
                print(f"ERROR: ADS-B radar unavailable: {exc}", file=sys.stderr)
                raise
            except Exception as exc:
                _log_error(f"readsb startup failed: {type(exc).__name__}: {exc}", exc_info=True)
                print(f"ERROR: ADS-B readsb startup failed: {exc}", file=sys.stderr)
                raise
        radar_args = argparse.Namespace(
            file=json_path,
            interval=max(100, int(os.environ.get("SPECTRUMSNEK_RADAR_INTERVAL", "1000"))),
        )
        if stdscr is None:
            curses.wrapper(radar.main, radar_args)
        else:
            radar.main(stdscr, radar_args)
    except Exception as exc:
        _log_error(f"Radar execution failed: {type(exc).__name__}: {exc}", exc_info=True)
        raise
    finally:
        if owns_decoder:
            # Manager may not have been created if the bootstrap failed.
            if "manager" in locals():
                manager.stop_readsb()


if __name__ == "__main__":
    run()

"""ADS-B radar plugin using readsb as the only ADS-B decoder."""

import argparse
import curses
import os
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
    "version": "2.1.0",
    "author": "SpectrumSnek",
    "category": "radio",
    "capabilities": [
        "readsb-backed ADS-B",
        "terminal radar",
        "shared SDR ownership",
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
            log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [adsb_radar] {message}\\n")
            if exc_info:
                log_file.write(traceback.format_exc())
                log_file.write("\\n")
    except OSError as log_exc:
        print(f"ADS-B radar: unable to write error.log: {log_exc}; {message}", file=sys.stderr)


def run(stdscr=None, *args, **kwargs):
    """Run the radar from SpectrumSnek's menu, service, or module entry point."""
    # The current menu launches plugins in a child process via plugin_menu.py.
    # Keep this argument compatibility for older callers that supply a curses
    # screen, while allowing the current run() contract (no required arguments).
    if stdscr is not None and not hasattr(stdscr, "getch"):
        stdscr = None

    manager = SDRManager()
    json_path = os.environ.get(
        "SPECTRUMSNEK_AIRCRAFT_JSON",
        os.path.join(manager.json_dir, "aircraft.json"),
    )
    owns_decoder = os.environ.get("SPECTRUMSNEK_EXTERNAL_READSB") != "1"
    try:
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
            manager.stop_readsb()


if __name__ == "__main__":
    run()

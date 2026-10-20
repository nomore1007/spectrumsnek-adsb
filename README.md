# SpectrumSnek ADS-B Radar

A modular ADS-B radar plugin for [SpectrumSnek](https://github.com/nomore1007/spectrumsnek). It uses **readsb** as its ADS-B decoder and renders aircraft positions in a terminal radar view.

## Features

- Uses readsb JSON output rather than implementing a separate ADS-B decoder.
- Shares SpectrumSnek's RTL-SDR ownership manager to avoid competing for the same dongle.
- Implements both plugin metadata interfaces: `MODULE_INFO` and `get_module_info()`, for compatibility with SpectrumSnek's current shared discovery backend and legacy loader.
- Runs through SpectrumSnek's plugin launcher, including the Whiptail menu and the experimental Textual menu; the radar itself remains a terminal/curses view.
- Can use an externally managed readsb instance by setting `SPECTRUMSNEK_EXTERNAL_READSB=1`.
- Supports `SPECTRUMSNEK_AIRCRAFT_JSON` to select the aircraft JSON file and `SPECTRUMSNEK_RADAR_INTERVAL` to set refresh milliseconds.
- Logs plugin startup/runtime and aircraft JSON read/parse errors to SpectrumSnek's root `error.log`.

## Install in SpectrumSnek

Use SpectrumSnek's **Utilities → Installed Plugins** menu, or from the SpectrumSnek checkout run:

```bash
bash plugin_manager.sh install adsb_radar
```

For a manual installation from the SpectrumSnek checkout:

```bash
git clone https://github.com/nomore1007/spectrumsnek-adsb.git plugins/adsb_radar
```

The plugin expects SpectrumSnek's shared `sdr_manager.py` at the application root. Keep that shared manager in place; do not copy a second manager into the plugin directory. The manager coordinates SDR ownership and starts/stops readsb when this plugin owns the decoder.

Install/build an RTL-SDR-enabled readsb using SpectrumSnek's setup instructions. If needed, set `READSB_BIN` to the full path of the readsb executable.

## Run

From the SpectrumSnek repository root:

```bash
python3 -m plugins.adsb_radar
```

The terminal radar exits with `q`. If a compatible external readsb process already exists, configure it to write aircraft JSON and set:

```bash
export SPECTRUMSNEK_EXTERNAL_READSB=1
export SPECTRUMSNEK_AIRCRAFT_JSON=/path/to/aircraft.json
python3 -m plugins.adsb_radar
```

In external mode, the plugin does not acquire the SDR lock or manage the decoder process.

## Requirements and notes

- Linux
- Python 3
- SpectrumSnek's shared `sdr_manager.py` when running under SpectrumSnek
- `readsb` built with RTL-SDR support unless using external JSON output
- A supported RTL-SDR receiver for direct decoding

The application can report a missing dongle or an unsupported readsb build, but it cannot make a physically absent or inaccessible device available. Do not run two independent decoders against the same SDR.

## Development

SpectrumSnek discovers plugins from `plugins/<plugin_id>/__init__.py`. The plugin exports `MODULE_INFO`, `get_module_info()`, and a no-argument `run()` entry point. Current menus launch it through SpectrumSnek's `plugin_menu.py --run adsb_radar` wrapper, which supplies the application root on `PYTHONPATH`; this lets the plugin import the shared `sdr_manager.py`. Run from the SpectrumSnek repository root for direct/module execution too.

## License

MIT. See [LICENSE.txt](LICENSE.txt).

# NetworkApp

A Python GUI app for lightweight network utilities and script orchestration.

## What this app does

1. **Landing/Overview tab** with a short introduction to the app.
2. **Network Mapper tab** with a scan button to detect:
   - your default gateway
   - locally discovered devices from ARP cache (`arp -a`)
3. **IP Lookup tab** to search an IP address and return basic origin/company info.
4. **Script Queue tab** to add/run queued scripts (`.py`, `.bat/.cmd`, `.bash/.sh`).

## Project organization

```text
NetworkApp/
├── .gitignore
├── app.py                     # simple launcher
├── src/
│   └── network_utility/
│       ├── __init__.py
│       ├── gui.py             # Tkinter interface + event handlers
│       ├── ip_lookup.py       # external IP info lookup service
│       ├── main.py            # package entrypoint
│       ├── models.py          # shared dataclasses
│       ├── networking.py      # gateway + ARP parsing
│       └── script_runner.py   # script execution utilities
├── scripts/                   # optional place for runnable scripts
└── tests/                     # optional test folder
```

## Run

From repository root:

```bash
python3 NetworkApp/app.py
```

Or from inside `NetworkApp/`:

```bash
python3 app.py
```

## Notes

- On Linux/macOS, make sure `ip` and `arp` commands are available.
- `.bat/.cmd` execution is only supported on Windows.

from __future__ import annotations

import ipaddress
import os
import re
import subprocess

from .models import DeviceRecord

IP_PATTERN = re.compile(r"(\d+\.\d+\.\d+\.\d+)")
MAC_PATTERN = re.compile(r"(([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2})")


def get_default_gateway() -> str:
    if os.name == "nt":
        cmd = ["route", "print", "0.0.0.0"]
    else:
        cmd = ["ip", "route"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = result.stdout + "\n" + result.stderr

    if os.name == "nt":
        for line in output.splitlines():
            if line.strip().startswith("0.0.0.0"):
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]
    else:
        for line in output.splitlines():
            if line.startswith("default"):
                parts = line.split()
                if "via" in parts:
                    return parts[parts.index("via") + 1]
    return ""


def get_arp_devices() -> list[DeviceRecord]:
    result = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
    output = result.stdout + "\n" + result.stderr

    devices: list[DeviceRecord] = []
    for line in output.splitlines():
        ip_match = IP_PATTERN.search(line)
        if not ip_match:
            continue

        ip = ip_match.group(1)
        mac_match = MAC_PATTERN.search(line)
        mac = mac_match.group(1) if mac_match else "(unknown)"

        try:
            ipaddress.ip_address(ip)
        except ValueError:
            continue

        devices.append(DeviceRecord(ip=ip, mac=mac))

    unique: dict[str, DeviceRecord] = {record.ip: record for record in devices}
    return list(unique.values())

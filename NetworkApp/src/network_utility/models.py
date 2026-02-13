from dataclasses import dataclass


@dataclass
class DeviceRecord:
    ip: str
    mac: str
    note: str = ""

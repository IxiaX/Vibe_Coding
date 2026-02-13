from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def lookup_ip_details(ip: str) -> dict[str, str]:
    url = (
        "http://ip-api.com/json/"
        f"{ip}?fields=status,message,query,country,regionName,city,isp,org,as"
    )
    try:
        with urlopen(url, timeout=10) as response:  # nosec: B310 - controlled endpoint
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {"status": "fail", "message": str(exc)}

    return payload

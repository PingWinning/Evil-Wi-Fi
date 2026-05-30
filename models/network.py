import re
import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class Network:
    ssid: str
    bssid: str
    channel: int
    signal: int
    encryption: str


class NetworkScanner:
    def __init__(self, interface: str):
        self.interface = interface

    def scan(self) -> List[Network]:
        try:
            result = subprocess.run(
                ['iwlist', self.interface, 'scanning'],
                capture_output=True, text=True, timeout=30
            )
            return self._parse(result.stdout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Scan timed out on {self.interface}")
        except FileNotFoundError:
            raise RuntimeError("iwlist not found — install wireless-tools")

    def _parse(self, output: str) -> List[Network]:
        networks = []
        seen_bssids = set()

        for cell in re.split(r'Cell \d+ -', output)[1:]:
            ssid_m = re.search(r'ESSID:"([^"]*)"', cell)
            bssid_m = re.search(r'Address: ([0-9A-Fa-f:]{17})', cell)
            chan_m = re.search(r'Channel:(\d+)', cell)
            sig_m = re.search(r'Signal level=(-?\d+)', cell)
            enc_m = re.search(r'Encryption key:(on|off)', cell)

            if not ssid_m or not bssid_m:
                continue
            ssid = ssid_m.group(1).strip()
            bssid = bssid_m.group(1)
            if not ssid or bssid in seen_bssids:
                continue

            seen_bssids.add(bssid)
            networks.append(Network(
                ssid=ssid,
                bssid=bssid,
                channel=int(chan_m.group(1)) if chan_m else 6,
                signal=int(sig_m.group(1)) if sig_m else -100,
                encryption='WPA' if enc_m and enc_m.group(1) == 'on' else 'Open',
            ))

        return sorted(networks, key=lambda n: n.signal, reverse=True)

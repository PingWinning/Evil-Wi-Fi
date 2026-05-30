import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rogue AP network
PORTAL_IP = '192.168.87.1'
PORTAL_SUBNET = '192.168.87.0/24'
DHCP_RANGE_START = '192.168.87.10'
DHCP_RANGE_END = '192.168.87.100'
DHCP_LEASE_FILE = '/tmp/evil_wifi_dnsmasq.leases'

# Portal
PORTAL_PORT = 80
PORTAL_TEMPLATE_DIR = os.path.join(BASE_DIR, 'views', 'portal')

# Logging
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CRED_LOG_FILE = os.path.join(LOG_DIR, 'credentials.log')

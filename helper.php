<?php
/**
 * Get the MAC address of a client by their IP address.
 * 
 * @param string $clientIP The client's IP address.
 * @return string The MAC address as a string.
 */
function getClientMac($clientIP)
{
    return trim(exec("grep " . escapeshellarg($clientIP) . " /tmp/dhcp.leases | awk '{print $2}'"));
}

/**
 * Get the SSID a client is associated with by their IP address.
 * 
 * @param string $clientIP The client's IP address.
 * @return string The SSID as a string.
 */
function getClientSSID($clientIP)
{
    $mac = getClientMac($clientIP);
    $pineAPLogPath = trim(file_get_contents('/etc/pineapple/pineap_log_location'));
    return trim(exec("grep " . escapeshellarg($mac) . " " . $pineAPLogPath . "pineap.log | grep 'Association' | awk -F ',' '{print $4}'"));
}

/**
 * Get the host name of the connected client by their IP address.
 * 
 * @param string $clientIP The client's IP address.
 * @return string The host name as a string.
 */
function getClientHostName($clientIP)
{
    return trim(exec("grep " . escapeshellarg($clientIP) . " /tmp/dhcp.leases | awk '{print $4}'"));
}
?>

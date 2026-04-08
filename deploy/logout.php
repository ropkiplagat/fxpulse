<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';
session_init();
logout();
header('Location: login.php?out=1');
exit;

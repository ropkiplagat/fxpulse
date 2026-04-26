<?php
/**
 * get_accounts.php — Returns active MT5 accounts for copy trading
 * Called by the VPS bot on every copy event to get fresh user accounts.
 * Protected by API_KEY header.
 */
require_once __DIR__ . '/../includes/config.php';

// Auth
$key = $_SERVER['HTTP_X_API_KEY'] ?? '';
if ($key !== API_KEY) {
    http_response_code(401);
    die(json_encode(['error' => 'Unauthorized']));
}

header('Content-Type: application/json');

if (!file_exists(MT5_ACCOUNTS_FILE)) {
    echo json_encode(['accounts' => []]);
    exit;
}

$data     = json_decode(file_get_contents(MT5_ACCOUNTS_FILE), true);
$accounts = $data['accounts'] ?? $data ?? [];

// Only return active accounts
$active = [];
foreach ($accounts as $username => $acc) {
    if (($acc['status'] ?? '') === 'active' || isset($acc['mt5_login'])) {
        $active[$username] = $acc;
    }
}

echo json_encode(['accounts' => $active]);

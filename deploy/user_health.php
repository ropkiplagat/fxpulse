<?php
/**
 * user_health.php — Internal health check for user data integrity.
 * Called by VPS agent CHECK 7 every 10 minutes.
 * Auth: ?token= must match API_KEY in config.php
 */
require_once __DIR__ . '/includes/config.php';

$token = $_GET['token'] ?? '';
if (!hash_equals(API_KEY, $token)) {
    http_response_code(403);
    echo json_encode(['error' => 'Forbidden']);
    exit;
}

$users_raw = file_exists(USERS_FILE)
    ? (json_decode(file_get_contents(USERS_FILE), true) ?? [])
    : [];

$result = [];
foreach ($users_raw as $username => $user) {
    $state_file = USER_STATES_DIR . $username . '.json';
    $result[] = [
        'username'       => $username,
        'role'           => $user['role']   ?? 'viewer',
        'status'         => $user['status'] ?? 'pending',
        'has_state_file' => file_exists($state_file),
    ];
}

header('Content-Type: application/json');
echo json_encode(['users' => $result, 'checked_at' => date('c')]);

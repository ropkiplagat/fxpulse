<?php
// One-time script: approve 'robi' and confirm auto-approve is on for all future users.
// DELETE THIS FILE from server after running once.
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/users.php';

$target = 'robi';
$users  = load_users();

if (!isset($users[$target])) {
    echo "User '$target' not found. Registered users: " . implode(', ', array_keys($users));
    exit;
}

$before = $users[$target]['status'] ?? 'unknown';
$users[$target]['status']      = STATUS_APPROVED;
$users[$target]['approved_at'] = date('c');
save_users($users);
activity_log("APPROVED: $target (one-time fix script)");

echo "Done. '$target' status: $before → approved. Delete this file now.";

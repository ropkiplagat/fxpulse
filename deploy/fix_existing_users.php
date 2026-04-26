<?php
// One-time script: marks all existing users as email_confirmed = true
// so they are not locked out by the new email confirmation requirement.
// DELETE THIS FILE from server after running once.
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/users.php';

$users   = load_users();
$updated = 0;

foreach ($users as $username => $u) {
    if (!isset($u['email_confirmed']) || $u['email_confirmed'] === false) {
        $users[$username]['email_confirmed'] = true;
        $updated++;
    }
}

save_users($users);
activity_log("SYSTEM: fix_existing_users.php — confirmed $updated existing accounts");

echo "<pre>Done. $updated accounts marked as email_confirmed = true.\n";
foreach ($users as $u) {
    echo "  {$u['username']} ({$u['email']}) — confirmed: " . ($u['email_confirmed'] ? 'YES' : 'NO') . "\n";
}
echo "\nDelete this file from the server now.</pre>";

<?php
require_once __DIR__ . '/config.php';

function load_users(): array {
    if (!file_exists(USERS_FILE)) return [];
    $data = json_decode(file_get_contents(USERS_FILE), true);
    return is_array($data) ? $data : [];
}

function save_users(array $users): void {
    file_put_contents(USERS_FILE, json_encode($users, JSON_PRETTY_PRINT));
}

function get_user(string $username): ?array {
    $users = load_users();
    return $users[$username] ?? null;
}

function user_exists(string $username): bool {
    return get_user($username) !== null;
}

function email_taken(string $email): bool {
    foreach (load_users() as $u) {
        if (strtolower($u['email']) === strtolower($email)) return true;
    }
    return false;
}

function user_count(): int {
    return count(load_users());
}

function at_capacity(): bool {
    // Admin account doesn't count toward the 100-user limit
    $users = load_users();
    $non_admin = array_filter($users, fn($u) => ($u['role'] ?? '') !== ROLE_ADMIN);
    return count($non_admin) >= MAX_USERS;
}

function create_user(string $username, string $password, string $email, string $full_name): array {
    $users = load_users();
    // First 100 non-admin users are auto-approved — no admin action needed
    $status      = STATUS_APPROVED;
    $approved_at = date('c');
    $users[$username] = [
        'username'        => $username,
        'hash'            => password_hash($password, PASSWORD_DEFAULT),
        'email'           => $email,
        'full_name'       => $full_name,
        'role'            => ROLE_VIEWER,
        'status'          => $status,
        'email_confirmed' => false,
        'created_at'      => date('c'),
        'approved_at'     => $approved_at,
        'last_login'      => null,
    ];
    save_users($users);
    activity_log("REGISTER: $username ($email) — auto-approved, email pending confirmation");
    return $users[$username];
}

function approve_user(string $username): bool {
    $users = load_users();
    if (!isset($users[$username])) return false;
    $users[$username]['status']      = STATUS_APPROVED;
    $users[$username]['approved_at'] = date('c');
    save_users($users);
    activity_log("APPROVED: $username by admin");
    return true;
}

function reject_user(string $username): bool {
    $users = load_users();
    if (!isset($users[$username])) return false;
    $users[$username]['status'] = STATUS_REJECTED;
    save_users($users);
    activity_log("REJECTED: $username by admin");
    return true;
}

function delete_user(string $username): bool {
    $users = load_users();
    if (!isset($users[$username])) return false;
    unset($users[$username]);
    save_users($users);
    activity_log("DELETED: $username by admin");
    return true;
}

function confirm_email(string $username): void {
    $users = load_users();
    if (isset($users[$username])) {
        $users[$username]['email_confirmed'] = true;
        save_users($users);
        activity_log("EMAIL CONFIRMED: $username");
    }
}

function update_password(string $username, string $new_password): void {
    $users = load_users();
    if (isset($users[$username])) {
        $users[$username]['hash'] = password_hash($new_password, PASSWORD_DEFAULT);
        save_users($users);
        activity_log("PASSWORD RESET: $username");
    }
}

function get_user_by_email(string $email): ?array {
    foreach (load_users() as $u) {
        if (strtolower($u['email']) === strtolower($email)) return $u;
    }
    return null;
}

function update_last_login(string $username): void {
    $users = load_users();
    if (isset($users[$username])) {
        $users[$username]['last_login'] = date('c');
        save_users($users);
    }
}

function get_users_by_status(string $status): array {
    return array_filter(load_users(), fn($u) => $u['status'] === $status);
}

function seed_admin(): void {
    // Create default admin if no users exist
    if (!empty(load_users())) return;
    $users = [];
    $users['admin'] = [
        'username'   => 'admin',
        'hash'       => password_hash('Admin@FXPulse2026', PASSWORD_DEFAULT),
        'email'      => 'admin@fxpulse.com',
        'full_name'  => 'FXPulse Admin',
        'role'       => ROLE_ADMIN,
        'status'     => STATUS_APPROVED,
        'created_at' => date('c'),
        'approved_at'=> date('c'),
        'last_login' => null,
    ];
    save_users($users);
    activity_log("SYSTEM: Default admin account created");
}

function activity_log(string $message): void {
    $line = '[' . date('Y-m-d H:i:s') . '] ' . $message . PHP_EOL;
    file_put_contents(LOGS_FILE, $line, FILE_APPEND | LOCK_EX);
}

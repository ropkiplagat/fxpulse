<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/users.php';

function session_init(): void {
    if (session_status() === PHP_SESSION_NONE) {
        session_set_cookie_params([
            'lifetime' => 0,
            'path'     => '/',
            'secure'   => true,
            'httponly' => true,
            'samesite' => 'Strict',
        ]);
        session_start();
    }
}

function is_logged_in(): bool {
    session_init();
    if (!isset($_SESSION['user'], $_SESSION['logged_in'])) return false;
    if (time() - $_SESSION['logged_in'] > SESSION_TIMEOUT) {
        logout();
        return false;
    }
    $_SESSION['logged_in'] = time(); // Rolling
    return true;
}

function is_admin(): bool {
    return is_logged_in() && ($_SESSION['role'] ?? '') === ROLE_ADMIN;
}

function require_login(string $redirect = 'login.php'): void {
    if (!is_logged_in()) {
        header("Location: $redirect");
        exit;
    }
}

function require_admin(string $redirect = '../login.php'): void {
    if (!is_admin()) {
        header("Location: $redirect");
        exit;
    }
}

function login(string $username, string $password): string {
    $user = get_user($username);
    if (!$user) return 'invalid';
    if (!password_verify($password, $user['hash'])) return 'invalid';
    if ($user['status'] === STATUS_PENDING)  return 'pending';
    if ($user['status'] === STATUS_REJECTED) return 'rejected';
    if (!($user['email_confirmed'] ?? false)) return 'unconfirmed';

    session_init();
    session_regenerate_id(true);
    $_SESSION['user']      = $username;
    $_SESSION['role']      = $user['role'];
    $_SESSION['name']      = $user['full_name'];
    $_SESSION['logged_in'] = time();

    update_last_login($username);
    activity_log("LOGIN: $username");
    return 'ok';
}

function logout(): void {
    session_init();
    if (isset($_SESSION['user'])) {
        activity_log("LOGOUT: " . $_SESSION['user']);
    }
    $_SESSION = [];
    session_destroy();
}

function current_user(): array {
    return [
        'username' => $_SESSION['user']  ?? '',
        'role'     => $_SESSION['role']  ?? '',
        'name'     => $_SESSION['name']  ?? '',
    ];
}

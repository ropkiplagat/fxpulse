<?php
require_once __DIR__ . '/config.php';

// ─────────────────────────────────────────────────────────────
// Storage helpers
// ─────────────────────────────────────────────────────────────

function load_mt5_accounts(): array {
    if (!file_exists(MT5_ACCOUNTS_FILE)) return [];
    $data = json_decode(file_get_contents(MT5_ACCOUNTS_FILE), true);
    return is_array($data) ? $data : [];
}

function save_mt5_accounts(array $accounts): void {
    file_put_contents(MT5_ACCOUNTS_FILE, json_encode($accounts, JSON_PRETTY_PRINT), LOCK_EX);
}

// ─────────────────────────────────────────────────────────────
// Account CRUD
// ─────────────────────────────────────────────────────────────

function get_mt5_account(string $username): ?array {
    $all = load_mt5_accounts();
    return $all[$username] ?? null;
}

function has_active_mt5_account(string $username): bool {
    $acc = get_mt5_account($username);
    return $acc !== null && ($acc['is_active'] ?? false) === true;
}

function create_mt5_account(
    string $username,
    string $mt5_login,
    string $mt5_password,
    string $broker_server,
    string $lot_size,
    string $account_type
): void {
    $all = load_mt5_accounts();
    $all[$username] = [
        'username'         => $username,
        'mt5_login'        => $mt5_login,
        'mt5_password_enc' => encrypt_mt5_password($mt5_password),
        'broker_server'    => $broker_server,
        'lot_size'         => $lot_size,
        'account_type'     => $account_type,
        'is_active'        => true,
        'connected_at'     => date('c'),
        'disconnected_at'  => null,
    ];
    save_mt5_accounts($all);
    activity_log("MT5 CONNECTED: $username → $broker_server #****" . substr($mt5_login, -4));
}

function disconnect_mt5_account(string $username): void {
    $all = load_mt5_accounts();
    if (isset($all[$username])) {
        $all[$username]['is_active']       = false;
        $all[$username]['disconnected_at'] = date('c');
        save_mt5_accounts($all);
        activity_log("MT5 DISCONNECTED: $username");
    }
}

// ─────────────────────────────────────────────────────────────
// AES-256-CBC encryption
// ─────────────────────────────────────────────────────────────

function encrypt_mt5_password(string $password): string {
    $key = substr(hash('sha256', ENCRYPT_SECRET, true), 0, 32);
    $iv  = random_bytes(16);
    $enc = openssl_encrypt($password, 'AES-256-CBC', $key, OPENSSL_RAW_DATA, $iv);
    return base64_encode($iv . $enc);
}

function decrypt_mt5_password(string $encrypted): string {
    $key  = substr(hash('sha256', ENCRYPT_SECRET, true), 0, 32);
    $raw  = base64_decode($encrypted);
    $iv   = substr($raw, 0, 16);
    $enc  = substr($raw, 16);
    return openssl_decrypt($enc, 'AES-256-CBC', $key, OPENSSL_RAW_DATA, $iv) ?: '';
}

// ─────────────────────────────────────────────────────────────
// CSRF helpers (used by connect-mt5.php)
// ─────────────────────────────────────────────────────────────

function generate_csrf(): string {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function verify_csrf(string $token): bool {
    return !empty($_SESSION['csrf_token'])
        && hash_equals($_SESSION['csrf_token'], $token);
}

// ─────────────────────────────────────────────────────────────
// Allowed values (validation whitelist)
// ─────────────────────────────────────────────────────────────

function allowed_brokers(): array {
    return [
        'Pepperstone-Demo', 'Pepperstone-Live',
        'ICMarkets-Demo',   'ICMarkets-Live',
        'FPMarkets-Demo',   'FPMarkets-Live',
        'FusionMarkets-Demo',
        'Vantage-Demo',     'Eightcap-Demo',
        'GOMarkets-Demo',   'XMGlobal-Demo',
        'AvaTrade-Demo',    'HFM-Demo',
        'HFCK-Demo',        'HFCK-Live',
        'Other-MT5',
    ];
}

function allowed_lot_sizes(): array {
    return ['0.10', '0.20', '0.30'];
}

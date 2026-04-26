<?php
require_once __DIR__ . '/config.php';

function _load_tokens(): array {
    if (!file_exists(TOKENS_FILE)) return [];
    $d = json_decode(file_get_contents(TOKENS_FILE), true);
    return is_array($d) ? $d : [];
}

function _save_tokens(array $tokens): void {
    file_put_contents(TOKENS_FILE, json_encode($tokens, JSON_PRETTY_PRINT), LOCK_EX);
}

function generate_token(string $type, string $username, int $ttl_hours = 24): string {
    $tokens = _load_tokens();
    // Purge expired
    $now = time();
    foreach ($tokens as $t => $data) {
        if ($data['expires'] < $now) unset($tokens[$t]);
    }
    $token = bin2hex(random_bytes(32));
    $tokens[$token] = [
        'type'     => $type,
        'username' => $username,
        'expires'  => $now + ($ttl_hours * 3600),
    ];
    _save_tokens($tokens);
    return $token;
}

function verify_token(string $token, string $type): ?string {
    $tokens = _load_tokens();
    if (!isset($tokens[$token])) return null;
    $d = $tokens[$token];
    if ($d['type'] !== $type) return null;
    if ($d['expires'] < time()) return null;
    return $d['username'];
}

function consume_token(string $token): void {
    $tokens = _load_tokens();
    unset($tokens[$token]);
    _save_tokens($tokens);
}

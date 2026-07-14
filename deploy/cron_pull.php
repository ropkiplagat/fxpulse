<?php
/**
 * cron_pull.php — runs on SiteGround server via cron (internal, no CAPTCHA)
 * Fetches bot_state.json + all user_states/ files from GitHub every minute.
 *
 * Cron command:
 *   php /home/u73-cgnrzebgdlwg/www/myforexpulse.com/public_html/cron_pull.php
 * Interval: every minute (* * * * *)
 */

require_once __DIR__ . '/includes/config.php';
define('CRON_LOG', DATA_DIR . 'cron.log');
define('RAW_BASE',        'https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/');
define('GH_API_BASE',     'https://api.github.com/repos/ropkiplagat/fxpulse/contents/');

if (!is_dir(DATA_DIR))        mkdir(DATA_DIR,        0750, true);
if (!is_dir(USER_STATES_DIR)) mkdir(USER_STATES_DIR, 0750, true);

$ctx = stream_context_create(['http' => [
    'timeout'       => 10,
    'user_agent'    => 'FXPulse-Cron/1.0',
    'ignore_errors' => true,
]]);

// ── 1. Pull master bot state ──────────────────────────────────────────────────
$json = @file_get_contents(RAW_BASE . 'bot_state.json', false, $ctx);
if ($json) {
    json_decode($json);
    if (json_last_error() === JSON_ERROR_NONE) {
        file_put_contents(BOT_FILE, $json);
        _log("Master bot_state OK");
    } else {
        _log("Master bot_state invalid JSON");
    }
} else {
    _log("Failed to fetch master bot_state");
}

// ── 2. Pull per-user state files ──────────────────────────────────────────────
$api_ctx = stream_context_create(['http' => [
    'timeout'       => 10,
    'user_agent'    => 'FXPulse-Cron/1.0',
    'ignore_errors' => true,
]]);

$listing = @file_get_contents(GH_API_BASE . 'user_states', false, $api_ctx);
if ($listing) {
    $files = json_decode($listing, true);
    if (is_array($files)) {
        foreach ($files as $file) {
            $name = $file['name'] ?? '';
            if (!str_ends_with($name, '.json')) continue;
            $raw = @file_get_contents(RAW_BASE . 'user_states/' . $name, false, $ctx);
            if ($raw) {
                json_decode($raw);
                if (json_last_error() === JSON_ERROR_NONE) {
                    file_put_contents(USER_STATES_DIR . $name, $raw);
                    _log("User state OK: $name");
                }
            }
        }
    }
} else {
    _log("No user_states/ folder on GitHub yet — skipping");
}

echo "OK\n";

function _log(string $msg): void {
    file_put_contents(CRON_LOG, date('Y-m-d H:i:s') . " [CRON] $msg\n", FILE_APPEND);
}

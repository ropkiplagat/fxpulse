<?php
/**
 * Bot Data Push Endpoint
 * The Python bot on Windows POSTs JSON body here every 60 seconds.
 * URL: https://yourdomain.com/fxpulse/api/bot_push.php
 */
require_once __DIR__ . '/../includes/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405); die('Method Not Allowed');
}

// Accept JSON body (Content-Type: application/json)
$body = json_decode(file_get_contents('php://input'), true);
if (!$body) {
    http_response_code(400); die('Invalid JSON body');
}
if (($body['api_key'] ?? '') !== API_KEY) {
    http_response_code(401); die('Unauthorized');
}
$data = $body['data'] ?? '{}';
json_decode($data);
if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(400); die('Invalid data JSON');
}
file_put_contents(BOT_FILE, $data);
echo 'OK';

<?php
define('APP_NAME',    'FXPulse');
define('APP_TAGLINE', 'AI-Powered Forex Trading Intelligence');
define('APP_VERSION', '1.0.0');

// Data directory (writable by PHP, outside public reach via .htaccess)
define('DATA_DIR',    __DIR__ . '/../data/');
define('USERS_FILE',  DATA_DIR . 'users.json');
define('BOT_FILE',    DATA_DIR . 'bot_state.json');
define('LOGS_FILE',   DATA_DIR . 'activity.log');

// Bot push API key — must match config.py SITEGROUND_API_KEY
define('API_KEY', 'CHANGE_THIS_TO_A_SECRET_KEY_123');

// Session timeout (30 min)
define('SESSION_TIMEOUT', 1800);

// Roles
define('ROLE_ADMIN',   'admin');
define('ROLE_VIEWER',  'viewer');
define('STATUS_PENDING',  'pending');
define('STATUS_APPROVED', 'approved');
define('STATUS_REJECTED', 'rejected');

// Ensure data dir exists
if (!is_dir(DATA_DIR)) {
    mkdir(DATA_DIR, 0750, true);
}

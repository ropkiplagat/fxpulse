<?php
define('APP_NAME',    'FXPulse');
define('APP_TAGLINE', 'AI-Powered Forex Trading Intelligence');
define('APP_VERSION', '1.0.0');

// Data directory (writable by PHP, outside public reach via .htaccess)
define('DATA_DIR',         __DIR__ . '/../data/');
define('USERS_FILE',       DATA_DIR . 'users.json');
define('BOT_FILE',         DATA_DIR . 'bot_state.json');
define('LOGS_FILE',        DATA_DIR . 'activity.log');
define('MT5_ACCOUNTS_FILE',  DATA_DIR . 'mt5_accounts.json');
define('USER_STATES_DIR',   DATA_DIR . 'user_states/');
define('MAX_USERS',         100);

// AES-256-CBC encryption key for MT5 passwords at rest
// CHANGE this to a unique secret on your server — never commit the real value
define('ENCRYPT_SECRET',   'fxpulse-mt5-enc-v1-changeme-on-server');

// Bot push API key — must match config.py SITEGROUND_API_KEY
define('API_KEY', '0d070602123b2dbf102ab30f01d95f34cab48bf4e08cabd8dd5b53561d6cdac7');

// Session timeout (30 min)
define('SESSION_TIMEOUT', 1800);

// Roles
define('ROLE_ADMIN',   'admin');
define('ROLE_VIEWER',  'viewer');
define('STATUS_PENDING',  'pending');
define('STATUS_APPROVED', 'approved');
define('STATUS_REJECTED', 'rejected');

// Ensure data dirs exist
if (!is_dir(DATA_DIR))        mkdir(DATA_DIR,        0750, true);
if (!is_dir(USER_STATES_DIR)) mkdir(USER_STATES_DIR, 0750, true);

<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/users.php';
require_once __DIR__ . '/includes/tokens.php';

$token    = trim($_GET['token'] ?? '');
$username = $token ? verify_token($token, 'email_confirm') : null;
$status   = 'invalid';

if ($username) {
    $user = get_user($username);
    if ($user && ($user['email_confirmed'] ?? false)) {
        $status = 'already';
    } else {
        confirm_email($username);
        consume_token($token);
        $status = 'ok';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Confirm Email — FXPulse</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#06080f;color:#c8d8ed;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.box{background:#0b0f1c;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:44px 40px;max-width:440px;width:100%;text-align:center}
.icon{font-size:48px;margin-bottom:20px}
h1{font-size:1.4em;font-weight:700;color:#e6edf3;margin-bottom:10px}
p{font-size:.92em;color:#8b949e;line-height:1.7;margin-bottom:24px}
a.btn{display:inline-block;background:#1a6fff;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:.92em}
a.btn:hover{background:#3a7fff}
</style>
</head>
<body>
<div class="box">
<?php if ($status === 'ok'): ?>
  <div class="icon">✅</div>
  <h1>Email confirmed!</h1>
  <p>Your FXPulse account is now active. Sign in to access your dashboard.</p>
  <a class="btn" href="login.php">Sign In &rarr;</a>

<?php elseif ($status === 'already'): ?>
  <div class="icon">ℹ️</div>
  <h1>Already confirmed</h1>
  <p>Your email is already confirmed. Go ahead and sign in.</p>
  <a class="btn" href="login.php">Sign In &rarr;</a>

<?php else: ?>
  <div class="icon">❌</div>
  <h1>Link expired or invalid</h1>
  <p>This confirmation link is invalid or has expired (links last 24 hours). Register again or contact support.</p>
  <a class="btn" href="register.php">Register again</a>
<?php endif; ?>
</div>
</body>
</html>

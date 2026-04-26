<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/users.php';
require_once __DIR__ . '/includes/mailer.php';

$sent = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');
    $user  = filter_var($email, FILTER_VALIDATE_EMAIL) ? get_user_by_email($email) : null;
    if ($user) {
        mail_forgot_username($user['email'], $user['full_name'], $user['username']);
    }
    $sent = true; // Always show success
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Forgot Username — FXPulse</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#06080f;color:#c8d8ed;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.box{background:#0b0f1c;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:44px 40px;max-width:420px;width:100%}
h1{font-size:1.3em;font-weight:700;color:#e6edf3;margin-bottom:8px}
.sub{font-size:.88em;color:#8b949e;margin-bottom:28px;line-height:1.6}
label{display:block;font-size:.8em;color:#8b949e;margin-bottom:6px;letter-spacing:.5px;text-transform:uppercase}
input[type=email]{width:100%;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:11px 14px;color:#e6edf3;font-size:.95em;outline:none;transition:border-color .2s}
input[type=email]:focus{border-color:#1a6fff}
.btn{width:100%;background:#1a6fff;color:#fff;border:none;padding:13px;border-radius:8px;font-size:.95em;font-weight:600;cursor:pointer;margin-top:18px}
.btn:hover{background:#3a7fff}
.success{background:#0d1f0d;border:1px solid #238636;border-radius:8px;padding:14px 16px;font-size:.88em;color:#3fb950;margin-bottom:20px;line-height:1.6}
.back{display:block;text-align:center;margin-top:20px;font-size:.85em;color:#8b949e}
.back a{color:#1a6fff}.back a:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="box">
  <h1>Forgot your username?</h1>
  <p class="sub">Enter the email address on your account and we'll send your username.</p>

  <?php if ($sent): ?>
    <div class="success">&#10003; If that email is registered, your username is on its way. Check your inbox.</div>
    <p class="back"><a href="login.php">&larr; Back to sign in</a></p>
  <?php else: ?>
    <form method="POST" action="">
      <label>Email address</label>
      <input type="email" name="email" placeholder="you@example.com" autofocus required>
      <button type="submit" class="btn">Send My Username</button>
    </form>
    <p class="back"><a href="login.php">&larr; Back to sign in</a> &nbsp;·&nbsp; <a href="forgot_password.php">Forgot password?</a></p>
  <?php endif; ?>
</div>
</body>
</html>

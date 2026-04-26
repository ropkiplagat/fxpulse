<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/users.php';
require_once __DIR__ . '/includes/tokens.php';

$token    = trim($_GET['token'] ?? '');
$username = $token ? verify_token($token, 'password_reset') : null;
$done     = false;
$errors   = [];

if (!$username) {
    $invalid = true;
} else {
    $invalid = false;
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $pw  = $_POST['password']  ?? '';
        $pw2 = $_POST['confirm']   ?? '';
        if (strlen($pw) < 8)   $errors[] = 'Password must be at least 8 characters.';
        if ($pw !== $pw2)       $errors[] = 'Passwords do not match.';
        if (empty($errors)) {
            update_password($username, $pw);
            consume_token($token);
            $done = true;
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reset Password — FXPulse</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#06080f;color:#c8d8ed;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.box{background:#0b0f1c;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:44px 40px;max-width:420px;width:100%}
h1{font-size:1.3em;font-weight:700;color:#e6edf3;margin-bottom:8px}
.sub{font-size:.88em;color:#8b949e;margin-bottom:28px;line-height:1.6}
.field{margin-bottom:16px}
label{display:block;font-size:.8em;color:#8b949e;margin-bottom:6px;letter-spacing:.5px;text-transform:uppercase}
.pw-wrap{position:relative}
.pw-wrap input{width:100%;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:11px 44px 11px 14px;color:#e6edf3;font-size:.95em;outline:none;transition:border-color .2s}
.pw-wrap input:focus{border-color:#1a6fff}
.pw-eye{position:absolute;right:12px;top:50%;transform:translateY(-50%);background:none;border:none;color:#8b949e;cursor:pointer;padding:2px;line-height:1}
.pw-eye:hover{color:#e6edf3}
.btn{width:100%;background:#1a6fff;color:#fff;border:none;padding:13px;border-radius:8px;font-size:.95em;font-weight:600;cursor:pointer;margin-top:6px}
.btn:hover{background:#3a7fff}
.error{background:#2d0f10;border:1px solid #6e2124;border-radius:8px;padding:12px 16px;font-size:.85em;color:#f85149;margin-bottom:16px}
.success{background:#0d1f0d;border:1px solid #238636;border-radius:8px;padding:14px 16px;font-size:.88em;color:#3fb950;margin-bottom:20px;line-height:1.6}
.back{display:block;text-align:center;margin-top:20px;font-size:.85em}
.back a{color:#1a6fff}.back a:hover{text-decoration:underline}
.hint{font-size:.75em;color:#8b949e;margin-top:5px}
</style>
</head>
<body>
<div class="box">
<?php if ($invalid): ?>
  <h1>Link expired</h1>
  <p class="sub">This password reset link is invalid or has expired (links last 1 hour). Request a new one.</p>
  <a href="forgot_password.php" style="display:block;background:#1a6fff;color:#fff;padding:12px;border-radius:8px;text-decoration:none;text-align:center;font-weight:600">Request new link</a>

<?php elseif ($done): ?>
  <h1>Password updated</h1>
  <p class="sub">Your password has been changed successfully.</p>
  <a href="login.php" style="display:block;background:#1a6fff;color:#fff;padding:12px;border-radius:8px;text-decoration:none;text-align:center;font-weight:600">Sign In &rarr;</a>

<?php else: ?>
  <h1>Choose a new password</h1>
  <p class="sub">Resetting password for <strong style="color:#e6edf3"><?= htmlspecialchars($username) ?></strong></p>

  <?php if ($errors): ?>
    <div class="error"><?= implode('<br>', array_map('htmlspecialchars', $errors)) ?></div>
  <?php endif; ?>

  <form method="POST" action="?token=<?= urlencode($token) ?>">
    <div class="field">
      <label>New Password</label>
      <div class="pw-wrap">
        <input type="password" name="password" id="pw1" placeholder="Min 8 characters" autocomplete="new-password" required>
        <button type="button" class="pw-eye" onclick="t('pw1')" aria-label="Show">
          <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
      <p class="hint">At least 8 characters</p>
    </div>
    <div class="field">
      <label>Confirm Password</label>
      <div class="pw-wrap">
        <input type="password" name="confirm" id="pw2" placeholder="Repeat password" autocomplete="new-password" required>
        <button type="button" class="pw-eye" onclick="t('pw2')" aria-label="Show">
          <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
    </div>
    <button type="submit" class="btn">Set New Password</button>
  </form>
<?php endif; ?>
</div>
<script>function t(id){const el=document.getElementById(id);el.type=el.type==='password'?'text':'password'}</script>
</body>
</html>

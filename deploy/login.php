<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';

session_init();
if (is_logged_in()) { header('Location: dashboard.php'); exit; }

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $result = login(trim($_POST['username'] ?? ''), $_POST['password'] ?? '');
    if ($result === 'ok')       { header('Location: dashboard.php'); exit; }
    if ($result === 'pending')  $error = 'Your account is pending admin approval. Check back soon.';
    if ($result === 'rejected') $error = 'Your account request was not approved. Contact support.';
    if ($result === 'invalid')  $error = 'Invalid username or password.';
}

$timeout  = isset($_GET['timeout']);
$loggedout= isset($_GET['out']);
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign In — FXPulse</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="auth-wrap">
  <div class="auth-box">
    <a href="index.php" class="auth-brand">&#9650; FXPulse</a>
    <h1 class="auth-title">Welcome back</h1>
    <p class="auth-sub">Sign in to your FXPulse dashboard.</p>

    <?php if ($timeout):  ?><div class="alert alert-warning">&#9201; Session expired. Please sign in again.</div><?php endif; ?>
    <?php if ($loggedout): ?><div class="alert alert-info">&#10003; You have been signed out.</div><?php endif; ?>
    <?php if ($error):    ?><div class="alert alert-error"><?= htmlspecialchars($error) ?></div><?php endif; ?>

    <form method="POST" action="">
      <div class="form-group">
        <label>Username</label>
        <input type="text" name="username" placeholder="Your username"
               value="<?= htmlspecialchars($_POST['username'] ?? '') ?>"
               autocomplete="username" autofocus required>
      </div>
      <div class="form-group">
        <label>Password</label>
        <input type="password" name="password" placeholder="Your password"
               autocomplete="current-password" required>
      </div>
      <button type="submit" class="btn-full">Sign In &rarr;</button>
    </form>

    <p class="auth-footer">Don't have an account? <a href="register.php">Request access</a></p>
  </div>
</div>
</body>
</html>

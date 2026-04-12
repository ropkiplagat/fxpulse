<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/users.php';

session_init();
if (is_logged_in()) { header('Location: dashboard.php'); exit; }

$errors  = [];
$success = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username  = trim($_POST['username']  ?? '');
    $email     = trim($_POST['email']     ?? '');
    $full_name = trim($_POST['full_name'] ?? '');
    $password  = $_POST['password']  ?? '';
    $confirm   = $_POST['confirm']   ?? '';

    // Validation
    if (!preg_match('/^[a-zA-Z0-9_]{3,20}$/', $username))
        $errors[] = 'Username must be 3–20 characters (letters, numbers, underscore).';
    elseif (user_exists($username))
        $errors[] = 'That username is already taken.';

    if (!filter_var($email, FILTER_VALIDATE_EMAIL))
        $errors[] = 'Please enter a valid email address.';
    elseif (email_taken($email))
        $errors[] = 'That email address is already registered.';

    if (strlen($full_name) < 2)
        $errors[] = 'Please enter your full name.';

    if (strlen($password) < 8)
        $errors[] = 'Password must be at least 8 characters.';
    elseif ($password !== $confirm)
        $errors[] = 'Passwords do not match.';

    if (empty($errors)) {
        create_user($username, $password, $email, $full_name);
        $success = true;

        // Telegram notification to admin
        $bot_token = '7618210192:AAH6GVQO4w6a9uHN9kTPr1xGpjF6KaLopWY';
        $chat_id   = ''; // set after first /start message to bot
        if ($bot_token && $chat_id) {
            $msg = urlencode("🔔 FXPulse: New registration!\nName: $full_name\nUsername: @$username\nEmail: $email\nApprove at: https://myforexpulse.com/admin/");
            @file_get_contents("https://api.telegram.org/bot{$bot_token}/sendMessage?chat_id={$chat_id}&text={$msg}");
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Register — FXPulse</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="auth-wrap">
  <div class="auth-box">
    <a href="index.php" class="auth-brand">&#9650; FXPulse</a>
    <h1 class="auth-title">Request Access</h1>
    <p class="auth-sub">Create your account. An admin will review and approve your request.</p>

    <?php if ($success): ?>
      <div class="alert alert-success">
        &#10003; <strong>Registration submitted!</strong><br><br>
        Your account is currently <strong>pending approval</strong>.<br>
        You will be approved within <strong>5 minutes</strong>.<br><br>
        Once approved, you can sign in using your username and password.
      </div>
      <a href="login.php" class="btn-full" style="margin-top:16px; display:block; text-align:center;">
        Back to Sign In
      </a>
    <?php else: ?>
      <?php if ($errors): ?>
        <div class="alert alert-error">
          <?php foreach ($errors as $e): ?>
            <div>&#8226; <?= htmlspecialchars($e) ?></div>
          <?php endforeach; ?>
        </div>
      <?php endif; ?>

      <form method="POST" action="" novalidate>
        <div class="form-group">
          <label>Full Name</label>
          <input type="text" name="full_name" placeholder="John Smith"
                 value="<?= htmlspecialchars($_POST['full_name'] ?? '') ?>" required>
        </div>
        <div class="form-group">
          <label>Username</label>
          <input type="text" name="username" placeholder="johnsmith"
                 value="<?= htmlspecialchars($_POST['username'] ?? '') ?>"
                 autocomplete="username" required>
          <span class="hint">Letters, numbers, underscore. 3–20 characters.</span>
        </div>
        <div class="form-group">
          <label>Email Address</label>
          <input type="email" name="email" placeholder="john@example.com"
                 value="<?= htmlspecialchars($_POST['email'] ?? '') ?>" required>
        </div>
        <div class="form-group">
          <label>Password</label>
          <input type="password" name="password" placeholder="Minimum 8 characters"
                 autocomplete="new-password" required>
        </div>
        <div class="form-group">
          <label>Confirm Password</label>
          <input type="password" name="confirm" placeholder="Repeat your password"
                 autocomplete="new-password" required>
        </div>
        <button type="submit" class="btn-full">Submit Request &rarr;</button>
      </form>
    <?php endif; ?>

    <p class="auth-footer">Already approved? <a href="login.php">Sign in</a></p>
  </div>
</div>
</body>
</html>

<?php
require_once __DIR__ . '/config.php';

function send_mail(string $to, string $to_name, string $subject, string $body_html): bool {
    $from    = FROM_EMAIL;
    $name    = FROM_NAME;
    $headers = implode("\r\n", [
        "MIME-Version: 1.0",
        "Content-Type: text/html; charset=UTF-8",
        "From: {$name} <{$from}>",
        "Reply-To: {$from}",
        "X-Mailer: FXPulse/1.0",
    ]);
    $result = @mail($to, $subject, $body_html, $headers);
    if (!$result) {
        error_log("[MAIL] Failed to send '$subject' to $to");
    }
    return (bool)$result;
}

function mail_confirm_email(string $to, string $to_name, string $username, string $token): bool {
    $link    = SITE_URL . '/confirm_email.php?token=' . urlencode($token);
    $subject = 'Confirm your FXPulse email address';
    $body    = email_template($to_name, 'Confirm your email', "
        <p>Thanks for joining FXPulse, <strong>{$username}</strong>.</p>
        <p>Click the button below to confirm your email address and activate your account.</p>
        <p style='margin:28px 0;text-align:center'>
          <a href='{$link}' style='background:#1a6fff;color:#fff;padding:13px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;display:inline-block'>
            Confirm Email Address
          </a>
        </p>
        <p style='font-size:12px;color:#8b949e'>Link expires in 24 hours. If you didn't create an account, ignore this email.</p>
        <p style='font-size:11px;color:#8b949e;margin-top:8px'>Or copy: {$link}</p>
    ");
    return send_mail($to, $to_name, $subject, $body);
}

function mail_reset_password(string $to, string $to_name, string $token): bool {
    $link    = SITE_URL . '/reset_password.php?token=' . urlencode($token);
    $subject = 'Reset your FXPulse password';
    $body    = email_template($to_name, 'Reset your password', "
        <p>We received a request to reset your FXPulse password.</p>
        <p style='margin:28px 0;text-align:center'>
          <a href='{$link}' style='background:#1a6fff;color:#fff;padding:13px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;display:inline-block'>
            Reset Password
          </a>
        </p>
        <p style='font-size:12px;color:#8b949e'>Link expires in 1 hour. If you didn't request this, your account is safe — ignore this email.</p>
        <p style='font-size:11px;color:#8b949e;margin-top:8px'>Or copy: {$link}</p>
    ");
    return send_mail($to, $to_name, $subject, $body);
}

function mail_forgot_username(string $to, string $to_name, string $username): bool {
    $subject = 'Your FXPulse username';
    $body    = email_template($to_name, 'Your username', "
        <p>You requested your FXPulse username.</p>
        <p style='margin:20px 0;font-size:22px;font-weight:700;color:#e6edf3;text-align:center;letter-spacing:1px'>{$username}</p>
        <p style='text-align:center'>
          <a href='" . SITE_URL . "/login.php' style='background:#1a6fff;color:#fff;padding:11px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;display:inline-block'>Sign In</a>
        </p>
        <p style='font-size:12px;color:#8b949e;margin-top:20px'>If you didn't request this, ignore this email.</p>
    ");
    return send_mail($to, $to_name, $subject, $body);
}

function email_template(string $name, string $heading, string $content): string {
    return <<<HTML
<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#06080f;font-family:'Segoe UI',Arial,sans-serif;color:#c8d8ed">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:40px 16px">
<table width="100%" style="max-width:520px;background:#0b0f1c;border-radius:12px;border:1px solid rgba(255,255,255,0.07);overflow:hidden">
  <tr><td style="background:linear-gradient(135deg,#1a6fff,#0047cc);padding:28px 36px">
    <div style="color:#fff;font-size:20px;font-weight:700;letter-spacing:-0.3px">FX<span style="color:#7eb8ff">Pulse</span></div>
    <div style="color:rgba(255,255,255,0.6);font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-top:4px">AI Trading Intelligence</div>
  </td></tr>
  <tr><td style="padding:36px">
    <h2 style="margin:0 0 20px;color:#e6edf3;font-size:18px;font-weight:600">{$heading}</h2>
    <div style="font-size:14px;line-height:1.7;color:#c8d8ed">{$content}</div>
  </td></tr>
  <tr><td style="padding:20px 36px;border-top:1px solid rgba(255,255,255,0.07);font-size:11px;color:#8b949e">
    &copy; 2026 FXPulse. This is an automated message &mdash; do not reply.
  </td></tr>
</table>
</td></tr></table>
</body></html>
HTML;
}

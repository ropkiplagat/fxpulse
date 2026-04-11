<?php
// Shared HTML head, nav, and footer helpers
function html_head(string $title, bool $refresh = false, int $refresh_secs = 30): void {
    $app = APP_NAME;
    $ref = $refresh ? "<meta http-equiv=\"refresh\" content=\"$refresh_secs\">" : '';
    echo <<<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{$ref}
<title>{$title} — {$app}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
HTML;
}

function nav(array $user = []): void {
    $app    = APP_NAME;
    $name   = htmlspecialchars($user['name']   ?? '');
    $role   = $user['role']   ?? '';
    $admin  = $role === ROLE_ADMIN
        ? '<a href="/fxpulse/admin/" class="nav-link admin-link">Admin Panel</a>' : '';
    echo <<<HTML
<nav class="navbar">
  <a href="/fxpulse/" class="nav-brand">&#9650; {$app}</a>
  <div class="nav-links">
    <a href="/fxpulse/dashboard.php" class="nav-link">Dashboard</a>
    {$admin}
    <span class="nav-user">&#128100; {$name}</span>
    <a href="/fxpulse/logout.php" class="nav-link nav-logout">Sign Out</a>
  </div>
</nav>
HTML;
}

function html_foot(): void {
    $app = APP_NAME;
    echo <<<HTML
<footer class="footer">
  <p>&copy; 2026 {$app} &bull; AI-Powered Forex Trading Intelligence &bull; Authorized Access Only</p>
</footer>
</body>
</html>
HTML;
}

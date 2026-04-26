<?php
/**
 * receiver.php — Forex AI Bot Web Dashboard with Login
 * Upload to SiteGround public_html/trading/receiver.php
 *
 * Features:
 *  - Secure login with hashed passwords
 *  - Multiple user accounts (client, admin)
 *  - Session-based authentication
 *  - Bot data push from Windows bot
 *  - Auto-refresh live dashboard
 */

session_start();

// =========================================================
// CONFIGURATION — Edit these before uploading
// =========================================================

$API_KEY   = "CHANGE_THIS_TO_A_SECRET_KEY_123"; // Must match config.py SITEGROUND_API_KEY
$DATA_FILE = __DIR__ . "/bot_state.json";

/**
 * USER ACCOUNTS
 * Add as many users as you need.
 *
 * To generate a password hash, run this PHP once:
 *   echo password_hash("yourpassword", PASSWORD_DEFAULT);
 *
 * Or use: https://bcrypt-generator.com  (cost factor 12)
 *
 * Default accounts below (CHANGE PASSWORDS before deploying):
 *   admin   / Admin@Forex2026
 *   client  / Client@Forex2026
 */
$USERS = [
    "admin" => [
        "hash"  => password_hash("Admin@Forex2026",  PASSWORD_DEFAULT),
        "role"  => "admin",   // admin sees config controls
        "name"  => "Admin",
    ],
    "client" => [
        "hash"  => password_hash("Client@Forex2026", PASSWORD_DEFAULT),
        "role"  => "viewer",  // viewer sees dashboard only
        "name"  => "Bethwel's Client",
    ],
];

// Session timeout in seconds (30 minutes)
$SESSION_TIMEOUT = 1800;

// =========================================================
// Handle POST from bot (data push) — no login needed
// =========================================================
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["api_key"])) {
    if ($_POST["api_key"] !== $API_KEY) {
        http_response_code(401);
        die("Unauthorized");
    }
    $data = $_POST["data"] ?? "{}";
    json_decode($data);
    if (json_last_error() !== JSON_ERROR_NONE) {
        http_response_code(400);
        die("Invalid JSON");
    }
    file_put_contents($DATA_FILE, $data);
    echo "OK";
    exit;
}

// =========================================================
// Handle login form submission
// =========================================================
$login_error = "";

if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["username"])) {
    $username = trim($_POST["username"] ?? "");
    $password = $_POST["password"] ?? "";

    if (isset($USERS[$username]) && password_verify($password, $USERS[$username]["hash"])) {
        $_SESSION["user"]       = $username;
        $_SESSION["role"]       = $USERS[$username]["role"];
        $_SESSION["name"]       = $USERS[$username]["name"];
        $_SESSION["logged_in"]  = time();
        header("Location: " . $_SERVER["PHP_SELF"]);
        exit;
    } else {
        $login_error = "Invalid username or password.";
    }
}

// =========================================================
// Handle logout
// =========================================================
if (isset($_GET["logout"])) {
    session_destroy();
    header("Location: " . $_SERVER["PHP_SELF"]);
    exit;
}

// =========================================================
// Session timeout check
// =========================================================
if (isset($_SESSION["logged_in"])) {
    if (time() - $_SESSION["logged_in"] > $SESSION_TIMEOUT) {
        session_destroy();
        header("Location: " . $_SERVER["PHP_SELF"] . "?timeout=1");
        exit;
    }
    $_SESSION["logged_in"] = time(); // Rolling timeout
}

// =========================================================
// Not logged in — show login page
// =========================================================
if (!isset($_SESSION["user"])):
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Forex AI Bot — Login</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif;
         min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .login-box { background: #161b22; border: 1px solid #30363d; border-radius: 12px;
               padding: 40px 36px; width: 100%; max-width: 380px; }
  .logo { text-align: center; margin-bottom: 28px; }
  .logo h1 { color: #58a6ff; font-size: 1.4em; margin-bottom: 4px; }
  .logo p  { color: #8b949e; font-size: 0.85em; }
  label { display: block; color: #8b949e; font-size: 0.8em; text-transform: uppercase;
          letter-spacing: 1px; margin-bottom: 6px; margin-top: 16px; }
  input[type=text], input[type=password] {
    width: 100%; background: #0d1117; border: 1px solid #30363d;
    border-radius: 6px; padding: 10px 14px; color: #c9d1d9; font-size: 0.95em;
    outline: none; transition: border-color 0.2s;
  }
  input:focus { border-color: #58a6ff; }
  .btn { width: 100%; margin-top: 24px; padding: 11px;
         background: #238636; border: none; border-radius: 6px;
         color: #fff; font-size: 1em; font-weight: 600; cursor: pointer;
         transition: background 0.2s; }
  .btn:hover { background: #2ea043; }
  .error { background: #3d1214; border: 1px solid #f85149; border-radius: 6px;
           color: #f85149; padding: 10px 14px; margin-top: 16px; font-size: 0.88em; }
  .timeout { background: #3d2b0e; border: 1px solid #d29922; border-radius: 6px;
             color: #d29922; padding: 10px 14px; margin-top: 16px; font-size: 0.88em; }
  .footer { color: #8b949e; font-size: 0.75em; text-align: center; margin-top: 24px; }
</style>
</head>
<body>
<div class="login-box">
  <div class="logo">
    <h1>🤖 Forex AI Bot</h1>
    <p>Live Trading Dashboard</p>
  </div>

  <?php if (isset($_GET["timeout"])): ?>
    <div class="timeout">Session expired. Please log in again.</div>
  <?php endif; ?>

  <?php if ($login_error): ?>
    <div class="error"><?= htmlspecialchars($login_error) ?></div>
  <?php endif; ?>

  <form method="POST" action="">
    <label for="username">Username</label>
    <input type="text" id="username" name="username" placeholder="Enter username"
           autocomplete="username" required>

    <label for="password">Password</label>
    <input type="password" id="password" name="password" placeholder="Enter password"
           autocomplete="current-password" required>

    <button type="submit" class="btn">Sign In</button>
  </form>

  <p class="footer">Authorized access only &bull; Pepperstone MT5</p>
</div>
</body>
</html>
<?php
// Stop here — user not logged in
die();
endif;

// =========================================================
// LOGGED IN — Load dashboard data
// =========================================================
$current_user = $_SESSION["user"];
$current_role = $_SESSION["role"];
$current_name = $_SESSION["name"];

$raw     = file_exists($DATA_FILE) ? file_get_contents($DATA_FILE) : "{}";
$state   = json_decode($raw, true) ?? [];
$updated = $state["updated"] ?? "Never";
$account = $state["account"] ?? [];
$balance = number_format($account["balance"] ?? 0, 2);
$equity  = number_format($account["equity"]  ?? 0, 2);
$dd_pct  = ($account["balance"] ?? 0) > 0
    ? round((($account["balance"] - $account["equity"]) / $account["balance"]) * 100, 1) : 0;
$regime     = strtoupper($state["regime"] ?? "UNKNOWN");
$session    = strtoupper($state["session"] ?? "NONE");
$perf       = $state["performance"] ?? [];
$wr_raw     = $perf["win_rate"]  ?? 0;
$wr         = round($wr_raw * 100, 1) . "%";
$pnl_raw    = $perf["total_pnl"] ?? 0;
$pnl        = ($pnl_raw >= 0 ? "+" : "") . number_format($pnl_raw, 2);
$trades     = $perf["total"]   ?? 0;
$wins       = $perf["wins"]    ?? 0;
$losses     = $perf["losses"]  ?? 0;
$strength   = $state["strength"]  ?? [];
$pairs      = $state["top_pairs"] ?? [];
$probs      = $state["win_probs"] ?? [];
$news       = $state["news"]      ?? [];
$in_session = $state["in_session"]       ?? false;
$regime_ok  = $state["regime_tradeable"] ?? false;

uasort($strength, fn($a, $b) => ($a["rank"] ?? 9) - ($b["rank"] ?? 9));

// Is data fresh? (older than 3 minutes = bot may be offline)
$data_age_sec = 9999;
if ($updated !== "Never") {
    try {
        $data_age_sec = time() - (new DateTime($updated))->getTimestamp();
    } catch (Exception $e) {}
}
$bot_online = $data_age_sec < 180;
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="30">
<title>Forex AI Bot — Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif;
         padding: 16px; min-height: 100vh; }
  .topbar { display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 6px; flex-wrap: wrap; gap: 8px; }
  h1 { color: #58a6ff; font-size: 1.35em; }
  .user-pill { background: #161b22; border: 1px solid #30363d; border-radius: 20px;
               padding: 5px 14px; font-size: 0.82em; display: flex; align-items: center; gap: 10px; }
  .user-pill span { color: #8b949e; }
  .user-pill a { color: #f85149; text-decoration: none; font-size: 0.9em; }
  .user-pill a:hover { text-decoration: underline; }
  .meta { color: #8b949e; font-size: 0.78em; margin-bottom: 18px; display: flex;
          align-items: center; gap: 10px; flex-wrap: wrap; }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .dot-green { background: #3fb950; } .dot-red { background: #f85149; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; }
  .card h3 { color: #58a6ff; font-size: 0.78em; text-transform: uppercase;
             letter-spacing: 1.5px; margin-bottom: 12px; border-bottom: 1px solid #21262d;
             padding-bottom: 8px; }
  .stat-row { display: flex; justify-content: space-between; align-items: center;
              padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 0.88em; }
  .stat-row:last-child { border-bottom: none; }
  .green { color: #3fb950; } .red { color: #f85149; } .yellow { color: #d29922; }
  .badge { padding: 2px 10px; border-radius: 20px; font-size: 0.75em; font-weight: 700; }
  .bg-green { background: #196c2e; color: #3fb950; }
  .bg-red   { background: #3d1214; color: #f85149; }
  .bg-yellow { background: #3d2b0e; color: #d29922; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
  th { color: #8b949e; font-weight: 500; text-align: left; padding: 4px 4px;
       border-bottom: 1px solid #30363d; font-size: 0.78em; text-transform: uppercase; }
  td { padding: 6px 4px; border-bottom: 1px solid #21262d; }
  .bar-bg { background: #21262d; height: 8px; border-radius: 4px; width: 80px; }
  .bar-fill { height: 8px; border-radius: 4px; }
  .bar-pos { background: #3fb950; } .bar-neg { background: #f85149; }
  .no-data { color: #8b949e; font-size: 0.85em; padding: 8px 0; }
  .offline-banner { background: #3d1214; border: 1px solid #f85149; border-radius: 8px;
                    color: #f85149; padding: 10px 16px; margin-bottom: 16px; font-size: 0.88em; }
  .footer { color: #8b949e; font-size: 0.72em; text-align: center; margin-top: 24px;
            padding-top: 16px; border-top: 1px solid #21262d; }
  @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } h1 { font-size: 1.1em; } }
</style>
</head>
<body>

<div class="topbar">
  <h1>&#129302; Forex AI Bot &mdash; Live Dashboard</h1>
  <div class="user-pill">
    <span>&#128100; <?= htmlspecialchars($current_name) ?>
      <?php if ($current_role === "admin"): ?><em>(Admin)</em><?php endif; ?>
    </span>
    <a href="?logout=1">Sign out</a>
  </div>
</div>

<div class="meta">
  <span class="dot <?= $bot_online ? 'dot-green' : 'dot-red' ?>"></span>
  <span>Bot: <strong><?= $bot_online ? 'ONLINE' : 'OFFLINE' ?></strong></span>
  &bull;
  <span>Last update: <strong><?= htmlspecialchars($updated) ?></strong></span>
  &bull;
  <span>Auto-refresh: 30s</span>
</div>

<?php if (!$bot_online): ?>
<div class="offline-banner">
  &#9888; Bot appears offline — last data was <?= round($data_age_sec / 60) ?> minutes ago.
  Check that main.py is running on your Windows machine.
</div>
<?php endif; ?>

<div class="grid">

  <!-- Account -->
  <div class="card">
    <h3>Account Overview</h3>
    <div class="stat-row"><span>Balance</span>
      <span class="green"><strong>$<?= $balance ?></strong></span></div>
    <div class="stat-row"><span>Equity</span><span>$<?= $equity ?></span></div>
    <div class="stat-row"><span>Drawdown</span>
      <span class="<?= $dd_pct >= 5 ? 'red' : ($dd_pct >= 3 ? 'yellow' : 'green') ?>">
        <?= $dd_pct ?>%
      </span></div>
    <div class="stat-row"><span>Session</span>
      <span class="badge <?= $in_session ? 'bg-green' : 'bg-red' ?>"><?= $session ?></span></div>
    <div class="stat-row"><span>Regime</span>
      <span class="badge <?= $regime_ok ? 'bg-green' : 'bg-yellow' ?>"><?= $regime ?></span></div>
  </div>

  <!-- Performance -->
  <div class="card">
    <h3>Performance</h3>
    <div class="stat-row"><span>Total Trades</span><span><strong><?= $trades ?></strong></span></div>
    <div class="stat-row"><span>Wins / Losses</span>
      <span><span class="green"><?= $wins ?></span> / <span class="red"><?= $losses ?></span></span></div>
    <div class="stat-row"><span>Win Rate</span>
      <span class="<?= $wr_raw >= 0.65 ? 'green' : ($wr_raw >= 0.5 ? 'yellow' : 'red') ?>">
        <strong><?= $wr ?></strong><?= $wr_raw >= 0.65 ? ' &#10003;' : '' ?>
      </span></div>
    <div class="stat-row"><span>Total P&amp;L</span>
      <span class="<?= $pnl_raw >= 0 ? 'green' : 'red' ?>"><strong>$<?= $pnl ?></strong></span></div>
  </div>

  <!-- Currency Strength -->
  <div class="card">
    <h3>Currency Strength</h3>
    <?php if (empty($strength)): ?>
      <p class="no-data">Waiting for bot data&hellip;</p>
    <?php else: ?>
    <table>
      <tr><th>#</th><th>CCY</th><th>Score</th><th>Dir</th><th>Strength</th></tr>
      <?php foreach ($strength as $cur => $s):
        $score  = (float)($s["score"] ?? 0);
        $rank   = (int)($s["rank"]  ?? 9);
        $slope  = $s["slope"] ?? "flat";
        $arrow  = $slope === "up" ? "&#9650;" : ($slope === "down" ? "&#9660;" : "&mdash;");
        $barW   = min((int)(abs($score) * 40), 72);
        $cls    = $score >= 0 ? "green" : "red";
        $barcls = $score >= 0 ? "bar-pos" : "bar-neg";
      ?>
      <tr>
        <td><strong>#<?= $rank ?></strong></td>
        <td><strong><?= htmlspecialchars($cur) ?></strong></td>
        <td class="<?= $cls ?>"><?= $score >= 0 ? "+" : "" ?><?= number_format($score, 3) ?></td>
        <td><?= $arrow ?></td>
        <td><div class="bar-bg"><div class="bar-fill <?= $barcls ?>" style="width:<?= $barW ?>px"></div></div></td>
      </tr>
      <?php endforeach; ?>
    </table>
    <?php endif; ?>
  </div>

  <!-- Top Opportunities -->
  <div class="card">
    <h3>Top Trade Opportunities</h3>
    <?php if (empty($pairs)): ?>
      <p class="no-data">No pairs above strength threshold.</p>
    <?php else: ?>
    <table>
      <tr><th>#</th><th>Pair</th><th>Dir</th><th>AI Win%</th><th>Gap</th></tr>
      <?php foreach ($pairs as $i => $p):
        $sym    = $p["symbol"] ?? "";
        $dir    = strtoupper($p["direction"] ?? "");
        $gap    = (float)($p["gap"] ?? 0);
        $prob   = (float)($probs[$sym] ?? 0);
        $probPc = round($prob * 100);
        $pcls   = $prob >= 0.65 ? "green" : ($prob >= 0.5 ? "yellow" : "red");
        $dircls = $dir === "BUY" ? "green" : "red";
      ?>
      <tr>
        <td>#<?= $i + 1 ?></td>
        <td><strong><?= htmlspecialchars($sym) ?></strong></td>
        <td class="<?= $dircls ?>"><strong><?= $dir ?></strong></td>
        <td class="<?= $pcls ?>"><strong><?= $probPc ?>%</strong><?= $prob >= 0.65 ? ' &#10003;' : '' ?></td>
        <td><?= $gap >= 0 ? "+" : "" ?><?= number_format($gap, 3) ?></td>
      </tr>
      <?php endforeach; ?>
    </table>
    <?php endif; ?>
  </div>

  <!-- News -->
  <?php if (!empty($news)): ?>
  <div class="card">
    <h3>Economic Calendar</h3>
    <table>
      <tr><th>CCY</th><th>Event</th><th>Time</th><th>Impact</th></tr>
      <?php foreach ($news as $n):
        $cls = ($n["impact"] ?? "") === "HIGH" ? "red" : "yellow";
        $min = (int)($n["in_min"] ?? 0);
        $t   = $min >= 0 ? "in {$min}m" : abs($min)."m ago";
      ?>
      <tr>
        <td><?= htmlspecialchars($n["currency"] ?? "") ?></td>
        <td><?= htmlspecialchars(substr($n["name"] ?? "", 0, 22)) ?></td>
        <td><?= $t ?></td>
        <td class="<?= $cls ?>"><strong><?= htmlspecialchars($n["impact"] ?? "") ?></strong></td>
      </tr>
      <?php endforeach; ?>
    </table>
  </div>
  <?php endif; ?>

</div><!-- end grid -->

<p class="footer">
  Forex AI Bot &bull; XGBoost + LSTM + Currency Strength &bull;
  Pepperstone MT5 &bull; Authorized access only.
</p>

</body>
</html>

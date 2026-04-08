"""
SiteGround API Bridge — bot POSTs live data to your SiteGround web dashboard.
The bot runs on Windows (local PC or VPS), the web UI lives on SiteGround.

Setup:
1. Upload receiver.php to your SiteGround public_html folder
2. Set SITEGROUND_API_URL in config.py to: https://yourdomain.com/receiver.php
3. Set SITEGROUND_API_KEY to any random string (same in receiver.php)
4. Bot will POST state data every 60 seconds
"""
import requests
import json
from datetime import datetime, timezone
import config

PUSH_INTERVAL = 60  # seconds between pushes
_last_push = None


def push_state(state: dict) -> bool:
    """
    Push bot state to SiteGround PHP endpoint.
    Returns True on success.
    """
    global _last_push

    url     = getattr(config, "SITEGROUND_API_URL", "")
    api_key = getattr(config, "SITEGROUND_API_KEY", "")

    if not url:
        return False  # Not configured

    try:
        payload = {
            "api_key": api_key,
            "data":    json.dumps(state, default=str),
            "ts":      datetime.now(timezone.utc).isoformat(),
        }
        resp = requests.post(url, data=payload, timeout=10)
        _last_push = datetime.now(timezone.utc)
        return resp.status_code == 200
    except Exception as e:
        print(f"[SG] Push failed: {e}")
        return False


def get_receiver_php() -> str:
    """
    Returns the PHP code to upload to SiteGround.
    Save as receiver.php in your public_html folder.
    """
    api_key = getattr(config, "SITEGROUND_API_KEY", "CHANGE_THIS_KEY")
    return f"""<?php
// receiver.php — upload to your SiteGround public_html folder
// Bot POSTs state data here every 60 seconds

$API_KEY = "{api_key}";
$DATA_FILE = __DIR__ . "/bot_state.json";

// --- Handle POST from bot ---
if ($_SERVER["REQUEST_METHOD"] === "POST") {{
    if (!isset($_POST["api_key"]) || $_POST["api_key"] !== $API_KEY) {{
        http_response_code(401);
        die("Unauthorized");
    }}
    $data = $_POST["data"] ?? "{{}}";
    file_put_contents($DATA_FILE, $data);
    echo "OK";
    exit;
}}

// --- Serve dashboard HTML on GET ---
$state = json_decode(file_exists($DATA_FILE) ? file_get_contents($DATA_FILE) : "{{}}", true) ?? [];
$updated = $state["updated"] ?? "Never";
$account = $state["account"] ?? [];
$balance = number_format($account["balance"] ?? 0, 2);
$equity  = number_format($account["equity"]  ?? 0, 2);
$regime  = strtoupper($state["regime"] ?? "UNKNOWN");
$session = strtoupper($state["session"] ?? "NONE");
$perf    = $state["performance"] ?? [];
$wr      = isset($perf["win_rate"]) ? round($perf["win_rate"] * 100, 1) . "%" : "0%";
$pnl     = isset($perf["total_pnl"]) ? ($perf["total_pnl"] >= 0 ? "+" : "") . number_format($perf["total_pnl"], 2) : "0.00";
$strength= $state["strength"] ?? [];
$pairs   = $state["top_pairs"] ?? [];
$probs   = $state["win_probs"] ?? [];
$news    = $state["news"] ?? [];

// Sort strength by rank
uasort($strength, fn($a, $b) => ($a["rank"] ?? 9) - ($b["rank"] ?? 9));
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="30">
<title>Forex AI Bot — Live Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', monospace; padding: 16px; }}
  h1 {{ color: #58a6ff; font-size: 1.4em; margin-bottom: 4px; }}
  .meta {{ color: #8b949e; font-size: 0.8em; margin-bottom: 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px; }}
  .card h3 {{ color: #58a6ff; font-size: 0.85em; text-transform: uppercase;
               letter-spacing: 1px; margin-bottom: 10px; }}
  .stat-row {{ display: flex; justify-content: space-between; padding: 4px 0;
               border-bottom: 1px solid #21262d; font-size: 0.9em; }}
  .green {{ color: #3fb950; }} .red {{ color: #f85149; }} .yellow {{ color: #d29922; }}
  .badge {{ padding: 1px 8px; border-radius: 10px; font-size: 0.75em; font-weight: bold; }}
  .bg-green {{ background: #196c2e; color: #3fb950; }}
  .bg-red   {{ background: #3d1214; color: #f85149; }}
  .bg-yellow {{ background: #3d2b0e; color: #d29922; }}
  .bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .bar {{ height: 10px; border-radius: 3px; min-width: 2px; }}
  .bar-pos {{ background: #3fb950; }} .bar-neg {{ background: #f85149; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88em; }}
  th {{ color: #8b949e; font-weight: normal; text-align: left; padding: 4px 0; border-bottom: 1px solid #30363d; }}
  td {{ padding: 5px 0; border-bottom: 1px solid #21262d; }}
  .footer {{ color: #8b949e; font-size: 0.75em; text-align: center; margin-top: 20px; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>🤖 Forex AI Bot — Live Dashboard</h1>
<p class="meta">Last updated: <?= htmlspecialchars($updated) ?> &nbsp;|&nbsp; Auto-refreshes every 30s</p>

<div class="grid">

  <!-- Account Card -->
  <div class="card">
    <h3>Account</h3>
    <div class="stat-row"><span>Balance</span><span class="green">$<?= $balance ?></span></div>
    <div class="stat-row"><span>Equity</span><span>$<?= $equity ?></span></div>
    <div class="stat-row"><span>Session</span>
      <span class="badge <?= $state["in_session"] ? "bg-green" : "bg-red" ?>"><?= $session ?></span></div>
    <div class="stat-row"><span>Regime</span>
      <span class="badge <?= strpos($regime,"TREND")!==false ? "bg-green" : "bg-yellow" ?>"><?= $regime ?></span></div>
    <div class="stat-row"><span>Win Rate</span><span class="<?= (float)$wr >= 65 ? "green" : "yellow" ?>"><?= $wr ?></span></div>
    <div class="stat-row"><span>Total P&amp;L</span>
      <span class="<?= ($perf["total_pnl"] ?? 0) >= 0 ? "green" : "red" ?>">$<?= $pnl ?></span></div>
    <div class="stat-row"><span>Trades</span><span><?= $perf["total"] ?? 0 ?></span></div>
  </div>

  <!-- Currency Strength -->
  <div class="card">
    <h3>Currency Strength</h3>
    <table>
      <tr><th>#</th><th>Currency</th><th>Score</th><th>Bar</th></tr>
      <?php foreach ($strength as $cur => $s):
        $score = $s["score"] ?? 0;
        $rank  = $s["rank"]  ?? 9;
        $slope = $s["slope"] ?? "flat";
        $arrow = $slope === "up" ? "▲" : ($slope === "down" ? "▼" : "─");
        $barW  = min(abs($score) * 35, 80);
        $cls   = $score >= 0 ? "green" : "red";
        $barcls= $score >= 0 ? "bar-pos" : "bar-neg";
      ?>
      <tr>
        <td>#<?= $rank ?></td>
        <td><b><?= htmlspecialchars($cur) ?></b> <?= $arrow ?></td>
        <td class="<?= $cls ?>"><?= $score >= 0 ? "+" : "" ?><?= number_format($score, 4) ?></td>
        <td><div class="bar-wrap"><div class="bar <?= $barcls ?>" style="width:<?= $barW ?>px"></div></div></td>
      </tr>
      <?php endforeach; ?>
    </table>
  </div>

  <!-- Top Pairs -->
  <div class="card">
    <h3>Top Pair Opportunities</h3>
    <?php if (empty($pairs)): ?>
      <p class="yellow" style="font-size:0.85em">No valid pairs above threshold.</p>
    <?php else: ?>
    <table>
      <tr><th>#</th><th>Pair</th><th>Dir</th><th>AI%</th><th>Gap</th></tr>
      <?php foreach ($pairs as $i => $p):
        $sym  = $p["symbol"] ?? "";
        $dir  = strtoupper($p["direction"] ?? "");
        $gap  = $p["gap"] ?? 0;
        $prob = ($probs[$sym] ?? 0) * 100;
        $cls  = $prob >= 65 ? "green" : ($prob >= 50 ? "yellow" : "red");
        $dircls = $dir === "BUY" ? "green" : "red";
      ?>
      <tr>
        <td>#<?= $i+1 ?></td>
        <td><b><?= htmlspecialchars($sym) ?></b></td>
        <td class="<?= $dircls ?>"><?= $dir ?></td>
        <td class="<?= $cls ?>"><?= round($prob) ?>%</td>
        <td><?= $gap >= 0 ? "+" : "" ?><?= number_format($gap, 3) ?></td>
      </tr>
      <?php endforeach; ?>
    </table>
    <?php endif; ?>
  </div>

  <!-- News Filter -->
  <?php if (!empty($news)): ?>
  <div class="card">
    <h3>Upcoming News Events</h3>
    <table>
      <tr><th>CCY</th><th>Event</th><th>In</th><th>Impact</th></tr>
      <?php foreach ($news as $n):
        $cls = ($n["impact"] ?? "") === "HIGH" ? "red" : "yellow";
        $min = $n["in_min"] ?? 0;
        $timeStr = $min >= 0 ? "in {$min}m" : abs($min)."m ago";
      ?>
      <tr>
        <td><?= htmlspecialchars($n["currency"] ?? "") ?></td>
        <td><?= htmlspecialchars($n["name"] ?? "") ?></td>
        <td><?= $timeStr ?></td>
        <td class="<?= $cls ?>"><?= htmlspecialchars($n["impact"] ?? "") ?></td>
      </tr>
      <?php endforeach; ?>
    </table>
  </div>
  <?php endif; ?>

</div>

<p class="footer">Forex AI Bot &nbsp;|&nbsp; Powered by XGBoost + LSTM + Currency Strength &nbsp;|&nbsp; For authorized use only.</p>
</body>
</html>
"""

<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';

session_init();
require_login();

$user  = current_user();

// Admin sees master bot state; each subscriber sees their own copied account state
if ($user['role'] === ROLE_ADMIN) {
    $state_file = BOT_FILE;
} else {
    $user_state_file = USER_STATES_DIR . $user['username'] . '.json';
    $state_file      = file_exists($user_state_file) ? $user_state_file : null;
}
$state = ($state_file && file_exists($state_file))
    ? (json_decode(file_get_contents($state_file), true) ?? [])
    : [];

$updated    = $state['updated']      ?? null;
$account    = $state['account']      ?? [];
$balance    = $account['balance']    ?? 0;
$equity     = $account['equity']     ?? 0;
$perf       = $state['performance']  ?? [];
$wr         = isset($perf['win_rate']) ? round($perf['win_rate'] * 100, 1) : 0;
$pnl_raw    = $perf['total_pnl']     ?? 0;
$wins       = $perf['wins']          ?? 0;
$losses     = $perf['losses']        ?? 0;
$total      = $perf['total']         ?? 0;
$dd         = $perf['max_drawdown_pct'] ?? 0;
$strength   = $state['strength']     ?? [];
$pairs      = $state['top_pairs']    ?? [];
$probs      = $state['win_probs']    ?? [];
$news       = $state['news']         ?? [];
$trades     = $state['open_trades']  ?? [];
$equity_hist= $state['equity_history'] ?? [];
$regime     = strtoupper($state['regime']      ?? 'UNKNOWN');
$session    = strtoupper($state['session']     ?? 'NONE');
$in_session = $state['in_session']   ?? false;

$_bot_online = false;
if ($updated) {
    try {
        $last_dt  = new DateTime($updated, new DateTimeZone('UTC'));
        $now_dt   = new DateTime('now',    new DateTimeZone('UTC'));
        $diff_sec = $now_dt->getTimestamp() - $last_dt->getTimestamp();
        $_bot_online = ($diff_sec <= 300);
    } catch (Exception $e) {}
}
$bot_running = $_bot_online;
$paper_mode  = $state['paper_trading'] ?? true;

if ($strength) uasort($strength, fn($a,$b) => ($a['rank']??9) - ($b['rank']??9));

$age_sec   = $updated ? (time() - strtotime($updated)) : null;
$stale     = ($age_sec === null || $age_sec > 120);

// State helpers
$is_new_user = ($updated === null && $balance === 0 && empty($strength));
$off_session = ($bot_running && !$in_session);

// JS data
$js_strength_labels = json_encode(array_keys($strength));
$js_strength_scores = json_encode(array_map(fn($s) => round($s['score'] ?? 0, 4), $strength));
$js_strength_colors = json_encode(array_map(fn($s) => ($s['score'] ?? 0) >= 0 ? '#3fb950' : '#f85149', $strength));
$js_equity          = json_encode(array_map(fn($e) => $e['equity'] ?? 0, $equity_hist));
$js_equity_labels   = json_encode(array_map(fn($e) => $e['time'] ?? '', $equity_hist));
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="30">
<title>FXPulse &mdash; Live Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1" crossorigin="anonymous"></script>
<style>
:root {
  --bg:       #0d1117;
  --bg-card:  #161b22;
  --bg-card2: #1c2128;
  --border:   #30363d;
  --border2:  #21262d;
  --text:     #e6edf3;
  --muted:    #8b949e;
  --blue:     #58a6ff;
  --green:    #3fb950;
  --red:      #f85149;
  --yellow:   #d29922;
  --gap: 16px;
  --radius: 10px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.5;}

/* HEADER */
.hdr{display:flex;justify-content:space-between;align-items:center;
  padding:12px 24px;background:var(--bg-card);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;}
.hdr-brand{color:var(--blue);font-weight:700;font-size:1.1em;text-decoration:none;display:flex;align-items:center;gap:8px;}
.hdr-brand span{width:8px;height:8px;border-radius:50%;background:<?= $bot_running ? 'var(--green)' : 'var(--red)' ?>;
  display:inline-block;<?= $bot_running ? 'animation:pulse 2s infinite;' : '' ?>}
.hdr-right{display:flex;align-items:center;gap:16px;}
.hdr-user{color:var(--muted);font-size:.85em;}
.hdr-admin{color:var(--blue);font-size:.82em;text-decoration:none;padding:4px 10px;
  border:1px solid var(--border);border-radius:6px;}
.hdr-admin:hover{border-color:var(--blue);}
.hdr-signout{color:var(--muted);font-size:.82em;text-decoration:none;padding:4px 10px;
  border:1px solid var(--border);border-radius:6px;}
.hdr-signout:hover{color:var(--red);border-color:var(--red);}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* BODY */
.body{padding:20px 24px;max-width:1400px;margin:0 auto;}

/* STALE */
.stale{background:#2d1f0a;border:1px solid #6e3c0e;color:var(--yellow);
  border-radius:8px;padding:10px 16px;margin-bottom:16px;font-size:.85em;display:flex;align-items:center;gap:8px;}

/* ONBOARDING */
.onboard{background:#0d1f0d;border:1px solid #238636;border-radius:10px;padding:20px 24px;margin-bottom:20px;}
.onboard h3{color:#3fb950;font-size:1em;margin-bottom:10px;}
.onboard p{color:#8b949e;font-size:.85em;line-height:1.65;}
.onboard p+p{margin-top:8px;}
.onboard .steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:14px;}
.onboard .step{background:#0f2d15;border:1px solid #238636;border-radius:8px;padding:14px 16px;}
.onboard .step-num{color:#3fb950;font-size:.7em;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;}
.onboard .step-title{color:#e6edf3;font-size:.9em;font-weight:600;margin-bottom:4px;}
.onboard .step-desc{color:#8b949e;font-size:.78em;line-height:1.5;}

/* OFF-SESSION */
.off-session{background:#1a1600;border:1px solid #6e3c0e;border-radius:10px;padding:16px 20px;margin-bottom:20px;
  display:flex;align-items:center;gap:14px;}
.off-session-icon{font-size:1.4em;flex-shrink:0;}
.off-session-text{color:#d29922;font-size:.85em;line-height:1.6;}
.off-session-text strong{color:#f0b429;}

/* EXPLAIN CHIPS */
.explain-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;}
.explain-chip{background:var(--bg-card);border:1px solid var(--border);border-radius:20px;padding:5px 14px;
  display:flex;align-items:center;gap:7px;font-size:.75em;color:var(--muted);}
.chip-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
.dot-green{background:var(--green);}
.dot-blue{background:var(--blue);}
.dot-yellow{background:var(--yellow);}

/* STATUS BAR */
.status-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;}
.pill{padding:4px 14px;border-radius:20px;font-size:.75em;font-weight:700;letter-spacing:.5px;border:1px solid;}
.pill-green{background:#0f2d15;color:var(--green);border-color:#238636;}
.pill-red{background:#2d0f10;color:var(--red);border-color:#6e2124;}
.pill-yellow{background:#2d1f0a;color:var(--yellow);border-color:#6e3c0e;}
.pill-blue{background:#091f3d;color:var(--blue);border-color:#1f6feb;}

/* KPI ROW */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:var(--gap);margin-bottom:var(--gap);}
.kpi{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:18px 20px;}
.kpi-label{font-size:.72em;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;}
.kpi-value{font-size:1.9em;font-weight:800;line-height:1;margin-bottom:4px;}
.kpi-sub{font-size:.78em;color:var(--muted);}
.kpi-green .kpi-value{color:var(--green);}
.kpi-red   .kpi-value{color:var(--red);}
.kpi-blue  .kpi-value{color:var(--blue);}
.kpi-yellow .kpi-value{color:var(--yellow);}
.kpi-white .kpi-value{color:var(--text);}

/* GRID */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:var(--gap);margin-bottom:var(--gap);}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:var(--gap);margin-bottom:var(--gap);}
.grid-full{margin-bottom:var(--gap);}
@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr;}}

/* CARD */
.card{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:18px 20px;}
.card-title{font-size:.72em;color:var(--blue);text-transform:uppercase;letter-spacing:1.5px;
  margin-bottom:16px;font-weight:700;display:flex;justify-content:space-between;align-items:center;}
.card-title .badge{font-size:1em;letter-spacing:0;text-transform:none;padding:2px 8px;
  border-radius:10px;font-weight:600;}

/* CHART */
.chart-wrap{position:relative;height:220px;}

/* TABLE */
table{width:100%;border-collapse:collapse;font-size:.87em;}
th{color:var(--muted);font-weight:500;text-align:left;padding:6px 0;
  border-bottom:1px solid var(--border);font-size:.8em;text-transform:uppercase;letter-spacing:.5px;}
td{padding:7px 0;border-bottom:1px solid var(--border2);}
td:last-child,th:last-child{text-align:right;}
tr:last-child td{border-bottom:none;}
.green{color:var(--green);} .red{color:var(--red);} .yellow{color:var(--yellow);}
.muted{color:var(--muted);} .blue{color:var(--blue);}
.bold{font-weight:700;}

/* STRENGTH BARS */
.bar-row{display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border2);}
.bar-row:last-child{border-bottom:none;}
.bar-left{display:flex;align-items:center;gap:8px;width:80px;}
.bar-rank{color:var(--muted);font-size:.78em;width:18px;}
.bar-ccy{font-weight:700;font-size:.92em;}
.bar-track{flex:1;background:var(--border2);border-radius:3px;height:8px;overflow:hidden;margin:0 12px;}
.bar-fill{height:100%;border-radius:3px;transition:width .3s;}
.bar-green{background:var(--green);}
.bar-red{background:var(--red);}
.bar-score{width:70px;text-align:right;font-size:.85em;font-variant-numeric:tabular-nums;}

/* PAIRS */
.pair-row{display:flex;align-items:center;justify-content:space-between;
  padding:8px 12px;border-radius:6px;margin-bottom:6px;background:var(--bg-card2);border:1px solid var(--border2);}
.pair-sym{font-weight:700;font-size:1em;}
.pair-dir{font-size:.78em;font-weight:700;padding:2px 8px;border-radius:4px;}
.dir-buy{background:#0f2d15;color:var(--green);}
.dir-sell{background:#2d0f10;color:var(--red);}
.pair-ai{font-size:.85em;font-weight:700;}
.pair-gap{font-size:.8em;color:var(--muted);}

/* NEWS */
.news-row{display:flex;align-items:center;justify-content:space-between;
  padding:6px 0;border-bottom:1px solid var(--border2);font-size:.85em;}
.news-row:last-child{border-bottom:none;}
.impact-high{color:var(--red);font-weight:700;}
.impact-med{color:var(--yellow);}

/* OPEN TRADES */
.trade-row{display:flex;align-items:center;justify-content:space-between;
  padding:8px 12px;border-radius:6px;margin-bottom:6px;background:var(--bg-card2);border:1px solid var(--border2);}

/* NO DATA */
.no-data{color:var(--muted);text-align:center;padding:30px 0;font-size:.88em;line-height:1.7;}

/* FOOTER */
.foot{color:var(--muted);font-size:.72em;text-align:center;margin-top:8px;padding-bottom:24px;}

@media(max-width:600px){.body{padding:12px;}.kpi-row{grid-template-columns:1fr 1fr;}
  .hdr{padding:10px 14px;}.hdr-user{display:none;}}
</style>
</head>
<body>

<header class="hdr">
  <a href="index.php" class="hdr-brand">
    <span></span> FXPulse
  </a>
  <div class="hdr-right">
    <span class="hdr-user"><?= htmlspecialchars($user['name']) ?></span>
    <?php if ($user['role'] === 'admin'): ?>
      <a href="admin/" class="hdr-admin">Admin Panel</a>
    <?php endif; ?>
    <a href="logout.php" class="hdr-signout">Sign out</a>
  </div>
</header>

<div class="body">

  <?php if ($is_new_user): ?>
  <div class="onboard">
    <h3>Welcome to FXPulse, <?= htmlspecialchars($user['name']) ?>! Your account is live.</h3>
    <p>The AI is scanning 28 currency pairs right now. <strong style="color:#e6edf3">Analysis appears below within 60 seconds</strong> &mdash; no action needed from you.</p>
    <div class="steps">
      <div class="step">
        <div class="step-num">Step 1 &mdash; Done</div>
        <div class="step-title">&#10003; Account approved</div>
        <div class="step-desc">You are signed in and verified.</div>
      </div>
      <div class="step">
        <div class="step-num">Step 2 &mdash; Done</div>
        <div class="step-title">&#10003; MT5 connected</div>
        <div class="step-desc">Your Pepperstone account is linked. <a href="guide.html" style="color:#58a6ff;">Review &rarr;</a></div>
      </div>
      <div class="step">
        <div class="step-num">Step 3 &mdash; Live now</div>
        <div class="step-title">Watch the signals</div>
        <div class="step-desc">Currency strength, regime, and top pair setups update every 60 seconds automatically.</div>
      </div>
      <div class="step">
        <div class="step-num">Step 4 &mdash; Your action</div>
        <div class="step-title">Trade on your MT5</div>
        <div class="step-desc">When AI confidence &ge;65% shows in Top Pairs, open that trade on your Pepperstone 50k demo terminal.</div>
      </div>
    </div>
    <p style="margin-top:14px;font-size:.78em;border-top:1px solid #238636;padding-top:12px;">
      <strong style="color:#e6edf3">How it works:</strong> The AI engine runs on the master trading account and analyses all 28 pairs every minute.
      You see those signals here in real time. Execute them on your own Pepperstone MT5 to grow your 50,000 demo balance using the same AI edge.
    </p>
  </div>
  <?php endif; ?>

  <?php if ($off_session): ?>
  <div class="off-session">
    <span class="off-session-icon">&#128307;</span>
    <div class="off-session-text">
      <strong>Markets are off-session right now</strong> &mdash; no new trade setups until the next active session.
      Currency strength and regime analysis below are still live and updating. The bot resumes signal generation automatically at session open.
    </div>
  </div>
  <?php endif; ?>

  <?php if ($stale && !$is_new_user): ?>
  <div class="stale">
    &#9888;
    <?= $updated ? 'Data is '.round($age_sec/60).' min old &mdash; bot may be offline or MT5 disconnected.' : 'Waiting for first data push from bot&hellip;' ?>
  </div>
  <?php endif; ?>

  <?php if (!$is_new_user && $bot_running): ?>
  <div class="explain-row">
    <div class="explain-chip"><span class="chip-dot dot-green"></span>AI scanning 28 pairs &mdash; updates every 60s</div>
    <div class="explain-chip"><span class="chip-dot dot-blue"></span>Session: <?= htmlspecialchars($session ?: 'detecting') ?></div>
    <div class="explain-chip"><span class="chip-dot dot-<?= strpos($regime,'TREND')!==false ? 'green' : 'yellow' ?>"></span>Regime: <?= htmlspecialchars($regime) ?></div>
    <div class="explain-chip"><span class="chip-dot dot-<?= $paper_mode ? 'yellow' : 'green' ?>"></span><?= $paper_mode ? 'Paper mode &mdash; no real money' : 'Live trading active' ?></div>
  </div>
  <?php endif; ?>

  <!-- Status Pills -->
  <div class="status-bar">
    <span class="pill <?= $bot_running ? 'pill-green' : 'pill-red' ?>">
      <?= $bot_running ? '&#9679; BOT RUNNING' : '&#9679; BOT OFFLINE' ?>
    </span>
    <span class="pill <?= $paper_mode ? 'pill-yellow' : 'pill-green' ?>">
      <?= $paper_mode ? 'PAPER MODE' : '&#9679; LIVE MODE' ?>
    </span>
    <span class="pill <?= $in_session ? 'pill-green' : 'pill-red' ?>">
      <?= $in_session ? 'IN SESSION' : 'OFF SESSION' ?>
    </span>
    <span class="pill pill-<?= strpos($regime,'TREND')!==false ? 'green' : 'yellow' ?>">
      <?= htmlspecialchars($regime) ?>
    </span>
    <?php if ($updated): ?>
    <span class="pill pill-blue">&#8635; <?= date('H:i:s', strtotime($updated)) ?> UTC</span>
    <?php endif; ?>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-row">
    <div class="kpi <?= $balance > 0 ? 'kpi-green' : 'kpi-white' ?>">
      <div class="kpi-label">Balance</div>
      <div class="kpi-value">$<?= number_format($balance,2) ?></div>
      <div class="kpi-sub">Master AI account</div>
    </div>
    <div class="kpi <?= $equity >= $balance ? 'kpi-green' : 'kpi-red' ?>">
      <div class="kpi-label">Equity</div>
      <div class="kpi-value">$<?= number_format($equity,2) ?></div>
      <div class="kpi-sub">Including open P&amp;L</div>
    </div>
    <div class="kpi <?= $pnl_raw >= 0 ? 'kpi-green' : 'kpi-red' ?>">
      <div class="kpi-label">Total P&amp;L</div>
      <div class="kpi-value"><?= $pnl_raw >= 0 ? '+' : '' ?>$<?= number_format($pnl_raw,2) ?></div>
      <div class="kpi-sub"><?= $total ?> trades total</div>
    </div>
    <div class="kpi <?= $wr >= 65 ? 'kpi-green' : ($wr >= 50 ? 'kpi-yellow' : 'kpi-red') ?>">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-value"><?= $wr ?>%</div>
      <div class="kpi-sub"><span class="green"><?= $wins ?>W</span> / <span class="red"><?= $losses ?>L</span></div>
    </div>
    <div class="kpi kpi-red">
      <div class="kpi-label">Max Drawdown</div>
      <div class="kpi-value"><?= $dd > 0 ? round($dd,2).'%' : '&mdash;' ?></div>
      <div class="kpi-sub">Peak-to-trough</div>
    </div>
    <div class="kpi kpi-blue">
      <div class="kpi-label">Open Trades</div>
      <div class="kpi-value"><?= count($trades) ?></div>
      <div class="kpi-sub">Active positions</div>
    </div>
  </div>

  <!-- Charts Row -->
  <div class="grid2">

    <div class="card">
      <div class="card-title">Currency Strength Rankings</div>
      <?php if (empty($strength)): ?>
        <div class="no-data">
          <?= $bot_running ? '&#128307; Strength analysis loading &mdash; arrives with next bot cycle (~60s)' : '&#9888; Bot offline &mdash; strength unavailable' ?>
        </div>
      <?php else: ?>
        <div class="chart-wrap"><canvas id="strengthChart"></canvas></div>
      <?php endif; ?>
    </div>

    <div class="card">
      <div class="card-title">Equity Curve</div>
      <?php if (empty($equity_hist)): ?>
        <div class="no-data">Equity curve builds once the bot begins trading &mdash; check back after the first London session</div>
      <?php else: ?>
        <div class="chart-wrap"><canvas id="equityChart"></canvas></div>
      <?php endif; ?>
    </div>

  </div>

  <!-- Pairs + Trades -->
  <div class="grid2">

    <div class="card">
      <div class="card-title">
        Top Pair Opportunities
        <span class="badge pill-blue"><?= count($pairs) ?> pairs</span>
      </div>
      <?php if (empty($pairs)): ?>
        <div class="no-data">
          <?php if (!$bot_running): ?>
            &#9888; Bot offline &mdash; no signals available
          <?php elseif (!$in_session): ?>
            &#128307; Off-session &mdash; signals resume when London or NY opens
          <?php elseif ($regime === 'RANGING'): ?>
            &#8987; Market is ranging &mdash; AI holding for trending conditions.<br>
            <span style="font-size:.82em;">This is normal. No edge in a ranging market. Bot waits.</span>
          <?php else: ?>
            Scanning &mdash; pairs appear when AI confidence exceeds threshold
          <?php endif; ?>
        </div>
      <?php else: ?>
        <?php foreach ($pairs as $i => $p):
          $sym  = $p['symbol']    ?? '';
          $dir  = strtoupper($p['direction'] ?? '');
          $gap  = $p['gap']       ?? 0;
          $prob = ($probs[$sym]   ?? 0) * 100;
          $pcls = $prob >= 65 ? 'green' : ($prob >= 50 ? 'yellow' : 'red');
        ?>
        <div class="pair-row">
          <div style="display:flex;align-items:center;gap:10px;">
            <span class="muted" style="font-size:.78em;">#<?= $i+1 ?></span>
            <span class="pair-sym"><?= htmlspecialchars($sym) ?></span>
            <span class="pair-dir <?= $dir==='BUY' ? 'dir-buy' : 'dir-sell' ?>"><?= $dir ?></span>
          </div>
          <div style="display:flex;align-items:center;gap:14px;">
            <span class="pair-ai <?= $pcls ?>"><?= round($prob) ?>% AI</span>
            <span class="pair-gap">Gap <?= number_format(abs($gap),3) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      <?php endif; ?>
    </div>

    <div class="card">
      <div class="card-title">
        Open Trades
        <?php if (!empty($trades)): ?>
          <span class="badge pill-<?= array_sum(array_column($trades,'profit')) >= 0 ? 'green' : 'red' ?>">
            <?= array_sum(array_column($trades,'profit')) >= 0 ? '+' : '' ?>$<?= number_format(array_sum(array_column($trades,'profit')),2) ?>
          </span>
        <?php endif; ?>
      </div>
      <?php if (empty($trades)): ?>
        <div class="no-data">
          <?php if (!$bot_running): ?>
            &#9888; Bot offline
          <?php elseif (!$in_session): ?>
            No positions &mdash; bot holds during off-session hours
          <?php elseif ($regime === 'RANGING'): ?>
            No positions &mdash; bot skips entries in ranging markets
          <?php else: ?>
            No open positions &mdash; waiting for a qualifying setup
          <?php endif; ?>
        </div>
      <?php else: ?>
        <?php foreach ($trades as $t):
          $ttype = strtoupper($t['type'] ?? '');
          $tpnl  = $t['profit'] ?? 0;
        ?>
        <div class="trade-row">
          <div style="display:flex;align-items:center;gap:10px;">
            <span class="bold"><?= htmlspecialchars($t['symbol'] ?? '') ?></span>
            <span class="pair-dir <?= $ttype==='BUY' ? 'dir-buy' : 'dir-sell' ?>"><?= $ttype ?></span>
            <span class="muted"><?= $t['volume'] ?? '' ?> lots</span>
          </div>
          <span class="<?= $tpnl >= 0 ? 'green' : 'red' ?> bold">
            <?= $tpnl >= 0 ? '+' : '' ?>$<?= number_format($tpnl,2) ?>
          </span>
        </div>
        <?php endforeach; ?>
      <?php endif; ?>
    </div>

  </div>

  <!-- Strength Detail + News -->
  <div class="grid2">

    <div class="card">
      <div class="card-title">Strength Detail</div>
      <?php if (empty($strength)): ?>
        <div class="no-data"><?= $bot_running ? '&#128307; Loading&hellip;' : '&#9888; Bot offline' ?></div>
      <?php else: ?>
        <?php foreach ($strength as $cur => $s):
          $score = $s['score'] ?? 0;
          $rank  = $s['rank']  ?? 9;
          $slope = $s['slope'] ?? 'flat';
          $arrow = $slope === 'up' ? '&#9650;' : ($slope === 'down' ? '&#9660;' : '&mdash;');
          $barPct= min(abs($score) * 35, 100);
          $cls   = $score >= 0 ? 'green' : 'red';
        ?>
        <div class="bar-row">
          <div class="bar-left">
            <span class="bar-rank">#<?= $rank ?></span>
            <span class="bar-ccy"><?= htmlspecialchars($cur) ?></span>
          </div>
          <div class="bar-track">
            <div class="bar-fill <?= $score >= 0 ? 'bar-green' : 'bar-red' ?>" style="width:<?= $barPct ?>%"></div>
          </div>
          <div class="bar-score <?= $cls ?>">
            <?= $arrow ?> <?= $score >= 0 ? '+' : '' ?><?= number_format($score,4) ?>
          </div>
        </div>
        <?php endforeach; ?>
      <?php endif; ?>
    </div>

    <div class="card">
      <div class="card-title">News Events</div>
      <?php if (empty($news)): ?>
        <div class="no-data">No high-impact events in the next 24h &mdash; clean trading window</div>
      <?php else: ?>
        <?php foreach ($news as $n):
          $impact = $n['impact'] ?? '';
          $min    = $n['in_min'] ?? 0;
          $ts     = $min >= 0 ? "in {$min}m" : abs($min)."m ago";
          $icls   = $impact === 'HIGH' ? 'impact-high' : 'impact-med';
        ?>
        <div class="news-row">
          <span class="bold"><?= htmlspecialchars($n['currency'] ?? '') ?></span>
          <span style="flex:1;padding:0 12px;color:var(--text);"><?= htmlspecialchars($n['name'] ?? '') ?></span>
          <span class="muted" style="margin-right:10px;"><?= $ts ?></span>
          <span class="<?= $icls ?>"><?= htmlspecialchars($impact) ?></span>
        </div>
        <?php endforeach; ?>
      <?php endif; ?>
    </div>

  </div>

</div>

<p class="foot">
  FXPulse &nbsp;&middot;&nbsp; Auto-refreshes every 30s
  <?php if($updated): ?>&nbsp;&middot;&nbsp; Last data: <?= date('Y-m-d H:i:s', strtotime($updated)) ?> UTC<?php endif; ?>
</p>

<script>
<?php if (!empty($strength)): ?>
(function(){
  const labels = <?= $js_strength_labels ?>;
  const scores = <?= $js_strength_scores ?>;
  const colors = <?= $js_strength_colors ?>;
  const ctx = document.getElementById('strengthChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets:[{
        label: 'Strength Score',
        data: scores,
        backgroundColor: colors.map(c => c + 'aa'),
        borderColor: colors,
        borderWidth: 2,
        borderRadius: 4,
      }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:false,
      plugins:{ legend:{display:false},
        tooltip:{ callbacks:{ label: ctx => (ctx.parsed.y >= 0 ? '+' : '') + ctx.parsed.y.toFixed(4) }}},
      scales:{
        x:{ grid:{color:'#21262d'}, ticks:{color:'#8b949e'}},
        y:{ grid:{color:'#21262d'}, ticks:{color:'#8b949e',
          callback: v => (v >= 0 ? '+' : '') + v.toFixed(3)}}
      }
    }
  });
})();
<?php endif; ?>

<?php if (!empty($equity_hist)): ?>
(function(){
  const labels = <?= $js_equity_labels ?>;
  const data   = <?= $js_equity ?>;
  const ctx = document.getElementById('equityChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets:[{
        label: 'Equity',
        data,
        borderColor: '#3fb950',
        backgroundColor: 'rgba(63,185,80,.08)',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:false,
      plugins:{ legend:{display:false},
        tooltip:{ callbacks:{ label: ctx => '$' + ctx.parsed.y.toFixed(2) }}},
      scales:{
        x:{ display:false },
        y:{ grid:{color:'#21262d'}, ticks:{color:'#8b949e',
          callback: v => '$' + v.toLocaleString()}}
      }
    }
  });
})();
<?php endif; ?>
</script>
</body>
</html>

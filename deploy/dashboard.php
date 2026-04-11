<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';

session_init();
require_login();

$user  = current_user();
$state = json_decode(file_exists(BOT_FILE) ? file_get_contents(BOT_FILE) : '{}', true) ?? [];

$bot_online   = !empty($state) && isset($state['timestamp']) && (time() - strtotime($state['timestamp'])) < 120;
$balance      = $state['balance']      ?? 0;
$equity       = $state['equity']       ?? 0;
$pnl          = $state['total_pnl']    ?? 0;
$win_rate     = $state['win_rate']      ?? 0;
$total_trades = $state['total_trades'] ?? 0;
$wins         = $state['wins']          ?? 0;
$losses       = $state['losses']        ?? 0;
$drawdown     = $state['max_drawdown']  ?? 0;
$open_trades  = $state['open_trades']  ?? [];
$strengths    = $state['strengths']    ?? [];
$top_pairs    = $state['top_pairs']    ?? [];
$news_events  = $state['news_events']  ?? [];
$regime       = $state['regime']       ?? 'UNKNOWN';
$paper_mode   = $state['paper_trading'] ?? true;
$adx          = $state['adx']          ?? 0;
$session      = $state['session']      ?? 'OFF SESSION';
$equity_curve = $state['equity_curve'] ?? [];
$last_updated = isset($state['timestamp']) ? date('H:i:s', strtotime($state['timestamp'])) : '--:--:--';

$pnl_color = $pnl >= 0 ? '#00ff88' : '#ff4757';
$pnl_sign  = $pnl >= 0 ? '+' : '';

// Regime color
$regime_colors = [
  'TRENDING_UP'   => '#00ff88',
  'TRENDING_DOWN' => '#ff4757',
  'RANGING'       => '#ffc107',
  'HIGH_VOL'      => '#ff6b35',
  'UNKNOWN'       => '#6b7fa3',
];
$regime_color = $regime_colors[$regime] ?? '#6b7fa3';
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FXPulse — Live Trading Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #04080f;
  --surface: #080f1a;
  --card: #0a1220;
  --card2: #0d1628;
  --border: #132035;
  --border2: #1a2d4a;
  --accent: #00c8ff;
  --accent2: #00ff88;
  --accent3: #ff6b35;
  --gold: #ffc107;
  --danger: #ff3a5c;
  --text: #dce8f5;
  --muted: #4a6080;
  --muted2: #2a3f5a;
  --font-display: 'Syne', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-display);
  min-height: 100vh;
  overflow-x: hidden;
}

/* Animated background grid */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0,200,255,.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,200,255,.025) 1px, transparent 1px);
  background-size: 48px 48px;
  animation: gridMove 20s linear infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes gridMove {
  0% { background-position: 0 0; }
  100% { background-position: 48px 48px; }
}

/* Ambient glow */
body::after {
  content: '';
  position: fixed;
  top: -40%;
  left: 50%;
  transform: translateX(-50%);
  width: 800px;
  height: 800px;
  background: radial-gradient(ellipse, rgba(0,200,255,.06) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

.wrap { max-width: 1400px; margin: 0 auto; padding: 0 20px; position: relative; z-index: 1; }

/* ── HEADER ── */
header {
  position: sticky;
  top: 0;
  z-index: 200;
  background: rgba(4,8,15,.92);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
}

.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 20px;
  color: var(--text);
  letter-spacing: -0.5px;
}

.logo-mark {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
  color: #000;
}

.logo-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: <?= $bot_online ? 'var(--accent2)' : 'var(--danger)' ?>;
  animation: <?= $bot_online ? 'pulse 2s infinite' : 'none' ?>;
  box-shadow: <?= $bot_online ? '0 0 8px var(--accent2)' : 'none' ?>;
}

@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.7)} }

.hdr-center {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 20px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.pill-online { background: rgba(0,255,136,.1); border: 1px solid rgba(0,255,136,.25); color: var(--accent2); }
.pill-offline { background: rgba(255,58,92,.1); border: 1px solid rgba(255,58,92,.25); color: var(--danger); }
.pill-paper { background: rgba(255,193,7,.1); border: 1px solid rgba(255,193,7,.25); color: var(--gold); }
.pill-live { background: rgba(0,200,255,.1); border: 1px solid rgba(0,200,255,.25); color: var(--accent); }
.pill-regime {
  background: rgba(0,0,0,.3);
  border: 1px solid var(--border2);
  color: <?= $regime_color ?>;
}

.hdr-right {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent), #0052cc);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
}

.btn-sm {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-family: var(--font-display);
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border2);
  background: transparent;
  color: var(--muted);
  transition: .2s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.btn-sm:hover { border-color: var(--accent); color: var(--accent); }

/* ── ALERT BANNER ── */
.alert-banner {
  background: linear-gradient(90deg, rgba(255,193,7,.08), rgba(255,107,53,.06));
  border-bottom: 1px solid rgba(255,193,7,.15);
  padding: 10px 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--gold);
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── MAIN LAYOUT ── */
.dashboard {
  padding: 24px 20px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ── METRIC CARDS ── */
.metrics {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

@media(max-width:1100px){ .metrics{grid-template-columns:repeat(3,1fr)} }
@media(max-width:600px){ .metrics{grid-template-columns:repeat(2,1fr)} }

.metric {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
  position: relative;
  overflow: hidden;
  transition: border-color .25s, transform .25s;
  animation: fadeUp .5s ease both;
}

.metric:hover { border-color: var(--border2); transform: translateY(-2px); }

.metric::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--metric-accent, linear-gradient(90deg, var(--accent), var(--accent2)));
  opacity: 0;
  transition: opacity .25s;
}
.metric:hover::before { opacity: 1; }

.metric-label {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--muted);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
  margin-bottom: 6px;
}

.metric-sub {
  font-size: 11px;
  color: var(--muted);
}

.metric:nth-child(1) { animation-delay: .05s; }
.metric:nth-child(2) { animation-delay: .1s; }
.metric:nth-child(3) { animation-delay: .15s; }
.metric:nth-child(4) { animation-delay: .2s; }
.metric:nth-child(5) { animation-delay: .25s; }
.metric:nth-child(6) { animation-delay: .3s; }

/* ── MAIN GRID ── */
.grid-main {
  display: grid;
  grid-template-columns: 1fr 1fr 380px;
  gap: 16px;
  margin-bottom: 16px;
}

@media(max-width:1100px){ .grid-main{grid-template-columns:1fr 1fr} }
@media(max-width:700px){ .grid-main{grid-template-columns:1fr} }

.grid-bottom {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media(max-width:700px){ .grid-bottom{grid-template-columns:1fr} }

/* ── PANELS ── */
.panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  animation: fadeUp .5s ease both;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.panel-title {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  letter-spacing: 2.5px;
  text-transform: uppercase;
  font-weight: 500;
}

.panel-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 3px 9px;
  border-radius: 10px;
  background: rgba(0,200,255,.1);
  border: 1px solid rgba(0,200,255,.2);
  color: var(--accent);
}

.panel-body { padding: 18px 20px; }

.empty-state {
  text-align: center;
  padding: 32px 20px;
  color: var(--muted);
  font-size: 13px;
  font-family: var(--font-mono);
}

.empty-state .empty-icon { font-size: 28px; margin-bottom: 10px; opacity: .5; }

/* ── STRENGTH BARS ── */
.strength-list { display: flex; flex-direction: column; gap: 10px; }

.strength-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.str-rank {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted);
  width: 18px;
  text-align: right;
  flex-shrink: 0;
}

.str-ccy {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
  width: 36px;
  flex-shrink: 0;
}

.str-bar-wrap {
  flex: 1;
  height: 6px;
  background: var(--muted2);
  border-radius: 3px;
  overflow: hidden;
}

.str-bar {
  height: 100%;
  border-radius: 3px;
  transition: width .8s ease;
}

.str-val {
  font-family: var(--font-mono);
  font-size: 11px;
  width: 60px;
  text-align: right;
  flex-shrink: 0;
}

.str-dir { font-size: 11px; width: 14px; flex-shrink: 0; }

/* ── PAIR OPPORTUNITIES ── */
.pair-list { display: flex; flex-direction: column; gap: 8px; }

.pair-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--card2);
  border: 1px solid var(--border);
  border-radius: 8px;
  transition: border-color .2s;
}
.pair-row:hover { border-color: var(--border2); }

.pair-name {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.pair-dir {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-weight: 700;
}

.dir-buy { background: rgba(0,255,136,.15); color: var(--accent2); }
.dir-sell { background: rgba(255,58,92,.15); color: var(--danger); }

.pair-conf {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--gold);
}

.conf-bar-wrap {
  width: 60px;
  height: 4px;
  background: var(--muted2);
  border-radius: 2px;
  overflow: hidden;
}

.conf-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  border-radius: 2px;
}

/* ── OPEN TRADES ── */
.trade-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.trade-row:last-child { border-bottom: none; }

.trade-pair { font-family: var(--font-mono); font-size: 14px; font-weight: 700; }
.trade-type { font-size: 11px; padding: 2px 7px; border-radius: 5px; font-family: var(--font-mono); }
.trade-info { font-family: var(--font-mono); font-size: 11px; color: var(--muted); }
.trade-pnl { font-family: var(--font-mono); font-size: 14px; font-weight: 700; }

/* ── EQUITY CURVE ── */
.equity-chart {
  width: 100%;
  height: 120px;
  position: relative;
  overflow: hidden;
}

.equity-chart svg {
  width: 100%;
  height: 100%;
}

/* ── NEWS EVENTS ── */
.news-list { display: flex; flex-direction: column; gap: 8px; }

.news-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--card2);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.news-impact {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.impact-high { background: var(--danger); box-shadow: 0 0 6px var(--danger); }
.impact-med { background: var(--gold); }
.impact-low { background: var(--muted); }

.news-ccy { font-family: var(--font-mono); font-size: 11px; color: var(--accent); font-weight: 700; width: 32px; flex-shrink: 0; }
.news-name { font-size: 13px; color: var(--text); flex: 1; }
.news-time { font-family: var(--font-mono); font-size: 11px; color: var(--muted); flex-shrink: 0; }

/* ── TICKER ── */
.ticker-wrap {
  border-top: 1px solid var(--border);
  overflow: hidden;
  background: rgba(0,0,0,.3);
}

.ticker {
  display: flex;
  gap: 0;
  animation: ticker 30s linear infinite;
  white-space: nowrap;
}

@keyframes ticker { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }

.tick-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 24px;
  border-right: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 11px;
}

.tick-pair { color: var(--muted); }
.tick-val { color: var(--text); font-weight: 500; }
.tick-chg { font-size: 10px; }
.tick-up { color: var(--accent2); }
.tick-dn { color: var(--danger); }

/* ── FOOTER ── */
.dash-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
  max-width: 1400px;
  margin: 0 auto;
}

/* ── ANIMATIONS ── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.number-green { color: var(--accent2) !important; }
.number-red { color: var(--danger) !important; }
.number-gold { color: var(--gold) !important; }

/* Live clock */
#live-clock { font-family: var(--font-mono); font-size: 12px; color: var(--muted); }

/* Auto-refresh progress */
.refresh-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  animation: refreshBar 30s linear infinite;
  z-index: 999;
}

@keyframes refreshBar { 0%{width:0} 100%{width:100%} }

/* Admin link */
.admin-link { color: var(--accent); text-decoration: none; font-size: 12px; }
.admin-link:hover { text-decoration: underline; }
</style>
</head>
<body>

<div class="refresh-bar"></div>

<!-- HEADER -->
<header>
  <div class="hdr">
    <div class="logo">
      <div class="logo-mark">FX</div>
      FXPulse
      <div class="logo-pulse"></div>
    </div>

    <div class="hdr-center">
      <span class="status-pill <?= $bot_online ? 'pill-online' : 'pill-offline' ?>">
        <?= $bot_online ? '● LIVE' : '● OFFLINE' ?>
      </span>
      <span class="status-pill <?= $paper_mode ? 'pill-paper' : 'pill-live' ?>">
        <?= $paper_mode ? 'PAPER' : 'LIVE' ?>
      </span>
      <span class="status-pill pill-regime">
        <?= str_replace('_', ' ', $regime) ?>
      </span>
    </div>

    <div class="hdr-right">
      <span id="live-clock"></span>
      <div class="user-info">
        <div class="user-avatar"><?= strtoupper(substr($user['full_name'] ?? 'U', 0, 1)) ?></div>
        <?= htmlspecialchars($user['full_name'] ?? '') ?>
      </div>
      <?php if (($user['role'] ?? '') === 'admin'): ?>
        <a href="/admin/" class="btn-sm admin-link">⚙ Admin</a>
      <?php endif; ?>
      <a href="/logout.php" class="btn-sm">Sign out</a>
    </div>
  </div>

  <?php if (!$bot_online): ?>
  <div class="alert-banner">
    <span>⚠</span>
    No data received — bot is offline or MT5 is not connected. Dashboard will auto-refresh every 30 seconds.
    Last updated: <?= $last_updated ?>
  </div>
  <?php endif; ?>
</header>

<div class="dashboard">

  <!-- METRIC CARDS -->
  <div class="metrics">

    <div class="metric">
      <div class="metric-label">Balance</div>
      <div class="metric-value">$<?= number_format($balance, 2) ?></div>
      <div class="metric-sub">Account funds</div>
    </div>

    <div class="metric">
      <div class="metric-label">Equity</div>
      <div class="metric-value" style="color:var(--accent)">$<?= number_format($equity, 2) ?></div>
      <div class="metric-sub">Incl. open P&L</div>
    </div>

    <div class="metric">
      <div class="metric-label">Total P&L</div>
      <div class="metric-value" style="color:<?= $pnl_color ?>"><?= $pnl_sign ?>$<?= number_format(abs($pnl), 2) ?></div>
      <div class="metric-sub"><?= $total_trades ?> trades total</div>
    </div>

    <div class="metric">
      <div class="metric-label">Win Rate</div>
      <div class="metric-value <?= $win_rate >= 55 ? 'number-green' : ($win_rate >= 45 ? 'number-gold' : 'number-red') ?>">
        <?= number_format($win_rate, 1) ?>%
      </div>
      <div class="metric-sub"><?= $wins ?>W / <?= $losses ?>L</div>
    </div>

    <div class="metric">
      <div class="metric-label">Max Drawdown</div>
      <div class="metric-value <?= $drawdown < 10 ? 'number-green' : ($drawdown < 15 ? 'number-gold' : 'number-red') ?>">
        <?= number_format($drawdown, 1) ?>%
      </div>
      <div class="metric-sub">Peak-to-trough</div>
    </div>

    <div class="metric">
      <div class="metric-label">Open Trades</div>
      <div class="metric-value" style="color:var(--gold)"><?= count($open_trades) ?></div>
      <div class="metric-sub">Active positions</div>
    </div>

  </div>

  <!-- MAIN GRID -->
  <div class="grid-main">

    <!-- CURRENCY STRENGTH -->
    <div class="panel">
      <div class="panel-head">
        <span class="panel-title">Currency Strength</span>
        <span class="panel-badge">8 currencies</span>
      </div>
      <div class="panel-body">
        <?php if (empty($strengths)): ?>
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            Waiting for bot data
          </div>
        <?php else: ?>
          <div class="strength-list">
            <?php
            arsort($strengths);
            $i = 1;
            $max_val = max(array_map('abs', array_values($strengths))) ?: 1;
            foreach ($strengths as $ccy => $val):
              $pct = min(100, (abs($val) / $max_val) * 100);
              $is_pos = $val >= 0;
              $bar_color = $is_pos
                ? 'linear-gradient(90deg,#00c8ff,#00ff88)'
                : 'linear-gradient(90deg,#ff3a5c,#ff6b35)';
              $val_color = $is_pos ? 'var(--accent2)' : 'var(--danger)';
              $dir = $is_pos ? '▲' : '▼';
            ?>
            <div class="strength-row">
              <span class="str-rank"><?= $i++ ?></span>
              <span class="str-ccy" style="color:<?= $is_pos ? 'var(--accent2)' : 'var(--danger)' ?>"><?= htmlspecialchars($ccy) ?></span>
              <div class="str-bar-wrap">
                <div class="str-bar" style="width:<?= $pct ?>%;background:<?= $bar_color ?>"></div>
              </div>
              <span class="str-dir" style="color:<?= $val_color ?>"><?= $dir ?></span>
              <span class="str-val" style="color:<?= $val_color ?>"><?= sprintf('%+.4f', $val) ?></span>
            </div>
            <?php endforeach; ?>
          </div>
        <?php endif; ?>
      </div>
    </div>

    <!-- TOP PAIR OPPORTUNITIES -->
    <div class="panel">
      <div class="panel-head">
        <span class="panel-title">Top Pair Opportunities</span>
        <span class="panel-badge"><?= count($top_pairs) ?> pairs</span>
      </div>
      <div class="panel-body">
        <?php if (empty($top_pairs)): ?>
          <div class="empty-state">
            <div class="empty-icon">🎯</div>
            No valid pairs above threshold
          </div>
        <?php else: ?>
          <div class="pair-list">
            <?php foreach (array_slice($top_pairs, 0, 8) as $pair):
              $conf = $pair['confidence'] ?? 0;
              $dir = strtoupper($pair['direction'] ?? 'BUY');
            ?>
            <div class="pair-row">
              <span class="pair-name"><?= htmlspecialchars($pair['pair'] ?? '') ?></span>
              <span class="pair-dir <?= $dir === 'BUY' ? 'dir-buy' : 'dir-sell' ?>"><?= $dir ?></span>
              <div>
                <div class="pair-conf"><?= number_format($conf * 100, 1) ?>%</div>
                <div class="conf-bar-wrap" style="margin-top:3px">
                  <div class="conf-bar" style="width:<?= ($conf * 100) ?>%"></div>
                </div>
              </div>
            </div>
            <?php endforeach; ?>
          </div>
        <?php endif; ?>
      </div>
    </div>

    <!-- OPEN TRADES -->
    <div class="panel">
      <div class="panel-head">
        <span class="panel-title">Open Trades</span>
        <span class="panel-badge"><?= count($open_trades) ?> active</span>
      </div>
      <div class="panel-body">
        <?php if (empty($open_trades)): ?>
          <div class="empty-state">
            <div class="empty-icon">📈</div>
            No open positions
          </div>
        <?php else: ?>
          <?php foreach ($open_trades as $t):
            $tpnl = $t['pnl'] ?? 0;
            $tcolor = $tpnl >= 0 ? 'var(--accent2)' : 'var(--danger)';
            $ttype = strtoupper($t['type'] ?? 'BUY');
          ?>
          <div class="trade-row">
            <div>
              <div class="trade-pair"><?= htmlspecialchars($t['symbol'] ?? '') ?></div>
              <div class="trade-info"><?= htmlspecialchars($t['entry'] ?? '') ?></div>
            </div>
            <span class="trade-type <?= $ttype === 'BUY' ? 'dir-buy' : 'dir-sell' ?>"><?= $ttype ?></span>
            <div class="trade-pnl" style="color:<?= $tcolor ?>">
              <?= $tpnl >= 0 ? '+' : '' ?>$<?= number_format(abs($tpnl), 2) ?>
            </div>
          </div>
          <?php endforeach; ?>
        <?php endif; ?>
      </div>
    </div>

  </div>

  <!-- BOTTOM GRID -->
  <div class="grid-bottom">

    <!-- NEWS EVENTS -->
    <div class="panel">
      <div class="panel-head">
        <span class="panel-title">News Events</span>
        <span class="panel-badge"><?= count($news_events) ?> upcoming</span>
      </div>
      <div class="panel-body">
        <?php if (empty($news_events)): ?>
          <div class="empty-state">
            <div class="empty-icon">📅</div>
            No upcoming high-impact events
          </div>
        <?php else: ?>
          <div class="news-list">
            <?php foreach (array_slice($news_events, 0, 6) as $n):
              $impact = strtolower($n['impact'] ?? 'low');
              $dot_class = $impact === 'high' ? 'impact-high' : ($impact === 'medium' ? 'impact-med' : 'impact-low');
            ?>
            <div class="news-row">
              <div class="news-impact <?= $dot_class ?>"></div>
              <span class="news-ccy"><?= htmlspecialchars($n['currency'] ?? '') ?></span>
              <span class="news-name"><?= htmlspecialchars($n['name'] ?? '') ?></span>
              <span class="news-time"><?= htmlspecialchars($n['time'] ?? '') ?></span>
            </div>
            <?php endforeach; ?>
          </div>
        <?php endif; ?>
      </div>
    </div>

    <!-- BOT STATS -->
    <div class="panel">
      <div class="panel-head">
        <span class="panel-title">Bot Performance</span>
        <span class="panel-badge">Session stats</span>
      </div>
      <div class="panel-body">
        <div style="display:flex;flex-direction:column;gap:14px">
          <?php
          $stats = [
            ['ADX Strength', number_format($adx, 1), $adx > 25 ? 'var(--accent2)' : 'var(--gold)'],
            ['Market Session', $session, 'var(--accent)'],
            ['Market Regime', str_replace('_',' ',$regime), $regime_color],
            ['Paper / Live', $paper_mode ? 'PAPER MODE' : 'LIVE MODE', $paper_mode ? 'var(--gold)' : 'var(--accent2)'],
            ['Total Trades', $total_trades, 'var(--text)'],
            ['Last Updated', $last_updated, 'var(--muted)'],
          ];
          foreach ($stats as $s): ?>
          <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:10px">
            <span style="font-family:var(--font-mono);font-size:11px;color:var(--muted);letter-spacing:1px;text-transform:uppercase"><?= $s[0] ?></span>
            <span style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:<?= $s[2] ?>"><?= htmlspecialchars($s[1]) ?></span>
          </div>
          <?php endforeach; ?>
        </div>
      </div>
    </div>

  </div>

</div>

<!-- FOOTER -->
<div class="dash-footer">
  <span>FXPulse v<?= APP_VERSION ?> · <?= APP_TAGLINE ?></span>
  <span>Auto-refreshes every 30s · <span id="next-refresh">30</span>s</span>
</div>

<script>
// Live clock
function updateClock() {
  const now = new Date();
  document.getElementById('live-clock').textContent =
    now.toLocaleTimeString('en-AU', {hour:'2-digit',minute:'2-digit',second:'2-digit'}) + ' AEST';
}
setInterval(updateClock, 1000);
updateClock();

// Countdown + auto-refresh
let secs = 30;
setInterval(() => {
  secs--;
  const el = document.getElementById('next-refresh');
  if (el) el.textContent = secs;
  if (secs <= 0) location.reload();
}, 1000);
</script>
</body>
</html>

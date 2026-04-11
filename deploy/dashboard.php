<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';

session_init();
require_login();

$user  = current_user();
$state = json_decode(file_exists(BOT_FILE) ? file_get_contents(BOT_FILE) : '{}', true) ?? [];

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
$bot_running= $state['bot_running']  ?? false;
$paper_mode = $state['paper_trading'] ?? true;

if ($strength) uasort($strength, fn($a,$b) => ($a['rank']??9) - ($b['rank']??9));

$age_sec = $updated ? (time() - strtotime($updated)) : null;
$stale   = ($age_sec === null || $age_sec > 120);

// Prepare JS data
$js_strength_labels = json_encode(array_keys($strength));
$js_strength_scores = json_encode(array_map(fn($s) => round($s['score'] ?? 0, 4), $strength));
$js_strength_colors = json_encode(array_map(fn($s) => ($s['score'] ?? 0) >= 0 ? '#3fb950' : '#f85149', $strength));
$js_equity = json_encode(array_map(fn($e) => $e['equity'] ?? 0, $equity_hist));
$js_equity_labels = json_encode(array_map(fn($e) => $e['time'] ?? '', $equity_hist));
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="30">
<title>FXPulse — Live Dashboard</title>
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
.no-data{color:var(--muted);text-align:center;padding:30px 0;font-size:.88em;}

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

  <?php if ($stale): ?>
  <div class="stale">
    &#9888;
    <?= $updated ? 'Data is '.round($age_sec/60).' min old — bot may be offline or MT5 disconnected.' : 'No data received yet — waiting for bot to connect.' ?>
  </div>
  <?php endif; ?>

  <!-- Status Pills -->
  <div class="status-bar">
    <span class="pill <?= $bot_running ? 'pill-green' : 'pill-red' ?>">
      <?= $bot_running ? '● RUNNING' : '● OFFLINE' ?>
    </span>
    <span class="pill <?= $paper_mode ? 'pill-yellow' : 'pill-green' ?>">
      <?= $paper_mode ? 'PAPER MODE' : '● LIVE MODE' ?>
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
      <div class="kpi-sub">Account funds</div>
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
      <div class="kpi-value"><?= $dd > 0 ? round($dd,2).'%' : '—' ?></div>
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

    <!-- Currency Strength Chart -->
    <div class="card">
      <div class="card-title">Currency Strength Rankings</div>
      <?php if (empty($strength)): ?>
        <div class="no-data">No data — waiting for bot</div>
      <?php else: ?>
        <div class="chart-wrap"><canvas id="strengthChart"></canvas></div>
      <?php endif; ?>
    </div>

    <!-- Equity Curve -->
    <div class="card">
      <div class="card-title">Equity Curve</div>
      <?php if (empty($equity_hist)): ?>
        <div class="no-data">No history yet — builds as bot trades</div>
      <?php else: ?>
        <div class="chart-wrap"><canvas id="equityChart"></canvas></div>
      <?php endif; ?>
    </div>

  </div>

  <!-- Pairs + Trades -->
  <div class="grid2">

    <!-- Top Pair Opportunities -->
    <div class="card">
      <div class="card-title">
        Top Pair Opportunities
        <span class="badge pill-blue"><?= count($pairs) ?> pairs</span>
      </div>
      <?php if (empty($pairs)): ?>
        <div class="no-data">No valid pairs above threshold</div>
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

    <!-- Open Trades -->
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
        <div class="no-data">No open positions</div>
      <?php else: ?>
        <?php foreach ($trades as $t):
          $tpnl = $t['profit'] ?? 0;
          $ttype = strtoupper($t['type'] ?? '');
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

  <!-- Currency Strength Detail + News -->
  <div class="grid2">

    <!-- Strength Detail Table -->
    <div class="card">
      <div class="card-title">Strength Detail</div>
      <?php if (empty($strength)): ?>
        <div class="no-data">No data</div>
      <?php else: ?>
        <?php foreach ($strength as $cur => $s):
          $score = $s['score'] ?? 0;
          $rank  = $s['rank']  ?? 9;
          $slope = $s['slope'] ?? 'flat';
          $arrow = $slope === 'up' ? '▲' : ($slope === 'down' ? '▼' : '─');
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

    <!-- News Filter -->
    <div class="card">
      <div class="card-title">News Events</div>
      <?php if (empty($news)): ?>
        <div class="no-data">No upcoming high-impact events</div>
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

</div><!-- /body -->

<p class="foot">
  FXPulse &nbsp;·&nbsp; Auto-refreshes every 30s
  <?php if($updated): ?>&nbsp;·&nbsp; Last data: <?= date('Y-m-d H:i:s', strtotime($updated)) ?> UTC<?php endif; ?>
</p>

<script>
// Currency Strength Chart
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

// Equity Curve
<?php if (!empty($equity_hist)): ?>
(function(){
  const labels = <?= $js_equity_labels ?>;
  const data   = <?= $js_equity ?>;
  const ctx = document.getElementById('equityChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data:{
      labels,
      datasets:[{
        label:'Equity',
        data,
        borderColor:'#58a6ff',
        backgroundColor:'rgba(88,166,255,0.08)',
        borderWidth:2,
        fill:true,
        tension:0.3,
        pointRadius:0,
        pointHoverRadius:4,
      }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:false,
      interaction:{mode:'index',intersect:false},
      plugins:{ legend:{display:false},
        tooltip:{ callbacks:{ label: ctx => '$'+ctx.parsed.y.toFixed(2) }}},
      scales:{
        x:{ display:false },
        y:{ grid:{color:'#21262d'}, ticks:{color:'#8b949e',
          callback: v => '$'+v.toFixed(0)}}
      }
    }
  });
})();
<?php endif; ?>
</script>

</body>
</html>

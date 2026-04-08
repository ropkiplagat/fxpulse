<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';

session_init();
// Redirect logged-in users straight to dashboard
if (is_logged_in()) {
    header('Location: dashboard.php');
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FXPulse — AI-Powered Forex Trading Intelligence</title>
<link rel="stylesheet" href="assets/style.css">
<style>
  /* Landing-specific overrides */
  .hero          { min-height: 100vh; display: flex; flex-direction: column;
                   align-items: center; justify-content: center; text-align: center;
                   padding: 80px 24px 60px; position: relative; overflow: hidden; }
  .hero::before  { content: ''; position: absolute; inset: 0;
                   background: radial-gradient(ellipse 80% 60% at 50% 0%,
                     rgba(88,166,255,.12) 0%, transparent 70%); pointer-events: none; }
  .hero-badge    { display: inline-flex; align-items: center; gap: 8px;
                   background: rgba(88,166,255,.1); border: 1px solid rgba(88,166,255,.3);
                   border-radius: 20px; padding: 5px 14px; font-size: .78em;
                   color: #58a6ff; margin-bottom: 24px; letter-spacing: .5px; }
  .hero-badge span { width: 7px; height: 7px; border-radius: 50%;
                     background: #3fb950; display: inline-block;
                     animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  .hero h1       { font-size: clamp(2.4em, 6vw, 4.2em); font-weight: 800; line-height: 1.1;
                   color: #e6edf3; max-width: 800px; margin: 0 auto 20px; letter-spacing: -.02em; }
  .hero h1 em    { font-style: normal; color: #58a6ff; }
  .hero p        { font-size: clamp(1em, 2.5vw, 1.2em); color: #8b949e; max-width: 560px;
                   margin: 0 auto 40px; line-height: 1.7; }
  .hero-btns     { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
  .btn-primary   { background: #238636; color: #fff; padding: 13px 28px; border-radius: 8px;
                   font-size: 1em; font-weight: 600; text-decoration: none;
                   transition: background .2s, transform .15s; border: none; cursor: pointer; }
  .btn-primary:hover { background: #2ea043; transform: translateY(-1px); }
  .btn-ghost     { background: transparent; color: #c9d1d9; padding: 13px 28px; border-radius: 8px;
                   font-size: 1em; font-weight: 500; text-decoration: none; border: 1px solid #30363d;
                   transition: border-color .2s, transform .15s; }
  .btn-ghost:hover { border-color: #8b949e; transform: translateY(-1px); }

  /* Stats strip */
  .stats         { display: flex; justify-content: center; gap: 48px; flex-wrap: wrap;
                   padding: 40px 24px; border-top: 1px solid #21262d;
                   border-bottom: 1px solid #21262d; background: rgba(22,27,34,.6); }
  .stat          { text-align: center; }
  .stat-num      { font-size: 2em; font-weight: 800; color: #e6edf3; display: block; }
  .stat-label    { font-size: .8em; color: #8b949e; text-transform: uppercase;
                   letter-spacing: 1px; margin-top: 4px; }

  /* Features */
  .section       { padding: 80px 24px; max-width: 1100px; margin: 0 auto; }
  .section-label { text-align: center; font-size: .78em; color: #58a6ff; text-transform: uppercase;
                   letter-spacing: 2px; margin-bottom: 12px; }
  .section h2    { text-align: center; font-size: clamp(1.6em, 4vw, 2.4em); font-weight: 700;
                   color: #e6edf3; margin-bottom: 48px; }
  .features      { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                   gap: 20px; }
  .feat-card     { background: #161b22; border: 1px solid #30363d; border-radius: 12px;
                   padding: 24px; transition: border-color .2s, transform .2s; }
  .feat-card:hover { border-color: #58a6ff; transform: translateY(-3px); }
  .feat-icon     { font-size: 1.8em; margin-bottom: 14px; }
  .feat-card h3  { color: #e6edf3; font-size: 1.05em; margin-bottom: 8px; }
  .feat-card p   { color: #8b949e; font-size: .88em; line-height: 1.6; }

  /* How it works */
  .steps         { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                   gap: 20px; counter-reset: steps; }
  .step          { background: #161b22; border: 1px solid #21262d; border-radius: 12px;
                   padding: 28px 24px; position: relative; }
  .step::before  { counter-increment: steps; content: "0" counter(steps);
                   display: block; font-size: 2.5em; font-weight: 800;
                   color: rgba(88,166,255,.2); margin-bottom: 12px; line-height: 1; }
  .step h3       { color: #e6edf3; font-size: 1em; margin-bottom: 8px; }
  .step p        { color: #8b949e; font-size: .85em; line-height: 1.6; }

  /* CTA band */
  .cta-band      { background: linear-gradient(135deg, #0d2137 0%, #0d1117 100%);
                   border-top: 1px solid #30363d; border-bottom: 1px solid #30363d;
                   padding: 80px 24px; text-align: center; }
  .cta-band h2   { font-size: clamp(1.6em, 4vw, 2.2em); color: #e6edf3; margin-bottom: 14px; }
  .cta-band p    { color: #8b949e; margin-bottom: 32px; font-size: 1em; }

  /* Nav (landing version) */
  .landing-nav   { position: fixed; top: 0; left: 0; right: 0; z-index: 100;
                   display: flex; justify-content: space-between; align-items: center;
                   padding: 16px 32px; background: rgba(13,17,23,.85);
                   backdrop-filter: blur(12px); border-bottom: 1px solid rgba(48,54,61,.5); }
  .landing-nav .brand { color: #58a6ff; font-weight: 700; font-size: 1.1em;
                        text-decoration: none; }
  .landing-nav .nav-actions { display: flex; gap: 10px; }

  footer.land-foot { background: #0d1117; border-top: 1px solid #21262d;
                     padding: 32px 24px; text-align: center;
                     color: #8b949e; font-size: .8em; }
  footer.land-foot a { color: #58a6ff; text-decoration: none; }
</style>
</head>
<body style="background:#0d1117; color:#c9d1d9; font-family:'Segoe UI',sans-serif; margin:0;">

<!-- Navigation -->
<nav class="landing-nav">
  <a href="index.php" class="brand">&#9650; FXPulse</a>
  <div class="nav-actions">
    <a href="login.php" class="btn-ghost" style="padding:8px 18px; font-size:.9em;">Sign In</a>
    <a href="register.php" class="btn-primary" style="padding:8px 18px; font-size:.9em;">Get Access</a>
  </div>
</nav>

<!-- Hero -->
<section class="hero">
  <div class="hero-badge">
    <span></span> Live Trading &bull; AI-Powered &bull; Pepperstone MT5
  </div>
  <h1>Trade Smarter with <em>AI Currency Intelligence</em></h1>
  <p>FXPulse combines currency strength analysis, Renko timing, and XGBoost + LSTM machine learning to identify high-probability forex setups — before you risk a cent.</p>
  <div class="hero-btns">
    <a href="register.php" class="btn-primary">Request Access &rarr;</a>
    <a href="#features"   class="btn-ghost">See How It Works</a>
  </div>
</section>

<!-- Stats -->
<div class="stats">
  <div class="stat"><span class="stat-num">65%+</span><span class="stat-label">Target Win Rate</span></div>
  <div class="stat"><span class="stat-num">28</span><span class="stat-label">Pairs Monitored</span></div>
  <div class="stat"><span class="stat-num">8</span><span class="stat-label">Currencies Ranked</span></div>
  <div class="stat"><span class="stat-num">24/7</span><span class="stat-label">Autonomous Operation</span></div>
</div>

<!-- Features -->
<div id="features" class="section">
  <p class="section-label">Core Intelligence</p>
  <h2>Everything your trades need to win</h2>
  <div class="features">
    <div class="feat-card">
      <div class="feat-icon">&#128200;</div>
      <h3>Currency Strength Engine</h3>
      <p>Scores USD, EUR, GBP, JPY, AUD, NZD, CAD, CHF across M15 + H1 timeframes every 60 seconds. Always trading the strongest vs the weakest.</p>
    </div>
    <div class="feat-card">
      <div class="feat-icon">&#129302;</div>
      <h3>XGBoost + LSTM AI</h3>
      <p>Ensemble machine learning model trained on thousands of historical setups. Only fires when win probability exceeds 65% — no gambling.</p>
    </div>
    <div class="feat-card">
      <div class="feat-icon">&#127919;</div>
      <h3>Renko Pullback Timing</h3>
      <p>Detects 2–4 brick pullbacks and continuation triggers on Renko charts simulated from M1 data. Precise entry, every time.</p>
    </div>
    <div class="feat-card">
      <div class="feat-icon">&#128737;</div>
      <h3>Smart Risk Management</h3>
      <p>Half Kelly position sizing, Renko trailing stops, 50% partial close at 1R, break-even management, and 8% drawdown circuit breaker.</p>
    </div>
    <div class="feat-card">
      <div class="feat-icon">&#128240;</div>
      <h3>News & Regime Filter</h3>
      <p>Blocks trading 30 min before high-impact events. Market regime detector (ADX + ATR) automatically sits out ranging and volatile markets.</p>
    </div>
    <div class="feat-card">
      <div class="feat-icon">&#128241;</div>
      <h3>Live Dashboard + Alerts</h3>
      <p>Real-time web dashboard showing currency rankings, top pairs, AI win probabilities, and P&amp;L. Telegram alerts for every trade.</p>
    </div>
  </div>
</div>

<!-- How it works -->
<div class="section" style="padding-top:0">
  <p class="section-label">Process</p>
  <h2>How FXPulse works</h2>
  <div class="steps">
    <div class="step">
      <h3>Rank Currencies</h3>
      <p>Calculates live strength scores for all 8 major currencies every 60 seconds using M15 + H1 data.</p>
    </div>
    <div class="step">
      <h3>Find the Gap</h3>
      <p>Identifies the top 3 pairs where the strongest and weakest currencies are most diverged.</p>
    </div>
    <div class="step">
      <h3>Wait for Setup</h3>
      <p>Monitors Renko charts for pullback + continuation trigger. No trigger = no trade.</p>
    </div>
    <div class="step">
      <h3>AI Scores It</h3>
      <p>XGBoost + LSTM ensemble scores the setup. Below 65% confidence = skipped automatically.</p>
    </div>
    <div class="step">
      <h3>Execute &amp; Manage</h3>
      <p>Places trade with risk-calculated lot size. Manages SL, partial close, break-even, and trailing stop autonomously.</p>
    </div>
  </div>
</div>

<!-- CTA -->
<div class="cta-band">
  <h2>Ready to trade with an edge?</h2>
  <p>Request access today. Start in paper trading mode — zero risk until you're confident.</p>
  <a href="register.php" class="btn-primary" style="font-size:1.05em; padding:14px 32px;">
    Request Access &rarr;
  </a>
</div>

<!-- Footer -->
<footer class="land-foot">
  <p>&copy; 2026 FXPulse &bull; AI-Powered Forex Trading Intelligence &bull;
  <a href="login.php">Sign In</a> &bull; <a href="register.php">Register</a></p>
  <p style="margin-top:8px; color:#6e7681; font-size:.9em;">
    Trading involves risk. Past performance does not guarantee future results.
    Always trade responsibly.
  </p>
</footer>

</body>
</html>

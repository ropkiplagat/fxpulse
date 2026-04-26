<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';
session_init();
if (is_logged_in()) { header('Location: dashboard.php'); exit; }
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FXPulse — AI-Powered Forex Intelligence</title>
<meta name="description" content="FXPulse combines currency strength analysis, Renko timing, and XGBoost + LSTM AI to identify high-probability forex setups 24/7 on Pepperstone MT5.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1" crossorigin="anonymous"></script>
<style>
/* ═══════════════════════════════════════════════
   TOKENS
═══════════════════════════════════════════════ */
:root {
  --bg:         #080c10;
  --bg-1:       #0d1117;
  --bg-2:       #111820;
  --bg-card:    #131a23;
  --border:     #1e2d3d;
  --border-hi:  #2a4060;
  --text:       #e2eaf3;
  --muted:      #6b8299;
  --accent:     #00d4ff;
  --accent2:    #00ff88;
  --accent3:    #ff6b35;
  --gold:       #f0c040;
  --green:      #00c853;
  --red:        #ff3d57;
  --font:       'Space Grotesk', sans-serif;
  --mono:       'DM Mono', monospace;
}
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  font-size: 16px;
  line-height: 1.6;
  overflow-x: hidden;
}

/* ═══════════════════════════════════════════════
   NAV
═══════════════════════════════════════════════ */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 200;
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 40px; height: 64px;
  background: rgba(8,12,16,.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
}
.nav-brand {
  display: flex; align-items: center; gap: 10px;
  color: var(--text); text-decoration: none; font-weight: 700; font-size: 1.1em;
}
.nav-brand .dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--accent2);
  animation: blink 2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.2} }
.nav-links { display: flex; align-items: center; gap: 32px; }
.nav-links a { color: var(--muted); text-decoration: none; font-size: .9em; transition: color .2s; }
.nav-links a:hover { color: var(--text); }
.nav-cta { display: flex; gap: 10px; align-items: center; }
.btn-ghost-sm {
  padding: 8px 20px; border: 1px solid var(--border-hi); border-radius: 6px;
  color: var(--text); text-decoration: none; font-size: .88em; font-weight: 500;
  transition: border-color .2s, color .2s;
}
.btn-ghost-sm:hover { border-color: var(--accent); color: var(--accent); }
.btn-accent-sm {
  padding: 8px 20px; background: var(--accent); border-radius: 6px;
  color: #000; text-decoration: none; font-size: .88em; font-weight: 700;
  transition: opacity .2s;
}
.btn-accent-sm:hover { opacity: .85; }

/* ═══════════════════════════════════════════════
   HERO
═══════════════════════════════════════════════ */
.hero {
  min-height: 100vh;
  display: grid; grid-template-columns: 1fr 1fr; align-items: center;
  gap: 60px; padding: 120px 80px 80px;
  position: relative; overflow: hidden;
  background:
    radial-gradient(ellipse 70% 60% at 60% 50%, rgba(0,212,255,.06) 0%, transparent 70%),
    radial-gradient(ellipse 50% 40% at 10% 80%, rgba(0,255,136,.04) 0%, transparent 60%);
}
.hero::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    linear-gradient(var(--border) 1px, transparent 1px),
    linear-gradient(90deg, var(--border) 1px, transparent 1px);
  background-size: 60px 60px;
  opacity: .25;
  pointer-events: none;
}
.hero-label {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--mono); font-size: .75em; color: var(--accent);
  border: 1px solid rgba(0,212,255,.3); border-radius: 4px;
  padding: 5px 14px; margin-bottom: 24px; letter-spacing: 1px;
  text-transform: uppercase;
}
.hero-label::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
.hero h1 {
  font-size: clamp(2.8em, 5vw, 4.4em); font-weight: 700; line-height: 1.05;
  letter-spacing: -.03em; margin-bottom: 24px;
}
.hero h1 em { font-style: normal; color: var(--accent); }
.hero h1 .gold { color: var(--gold); }
.hero-sub {
  font-size: 1.1em; color: var(--muted); max-width: 480px; margin-bottom: 40px; line-height: 1.7;
}
.hero-btns { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 48px; }
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 14px 32px; background: var(--accent); border-radius: 8px;
  color: #000; text-decoration: none; font-weight: 700; font-size: 1em;
  transition: opacity .2s, transform .15s;
}
.btn-primary:hover { opacity: .88; transform: translateY(-1px); }
.btn-primary svg { width: 16px; height: 16px; }
.btn-outline {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 14px 32px; border: 1px solid var(--border-hi); border-radius: 8px;
  color: var(--text); text-decoration: none; font-weight: 500; font-size: 1em;
  transition: border-color .2s, transform .15s;
}
.btn-outline:hover { border-color: var(--accent); transform: translateY(-1px); }
.hero-trust { display: flex; gap: 24px; flex-wrap: wrap; }
.trust-item { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: .82em; }
.trust-item svg { color: var(--accent2); }

/* HERO TERMINAL */
.hero-visual { position: relative; z-index: 1; }
.terminal {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden;
  box-shadow: 0 40px 80px rgba(0,0,0,.6), 0 0 0 1px rgba(0,212,255,.08);
}
.terminal-bar {
  padding: 12px 16px; background: var(--bg-2); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 8px;
}
.t-dot { width: 12px; height: 12px; border-radius: 50%; }
.terminal-body { padding: 20px; font-family: var(--mono); font-size: .8em; }
.t-line { margin-bottom: 6px; }
.t-green { color: var(--green); }
.t-blue  { color: var(--accent); }
.t-gold  { color: var(--gold); }
.t-red   { color: var(--red); }
.t-muted { color: var(--muted); }
.t-white { color: var(--text); }
.chart-container { padding: 16px 20px 20px; }
canvas { display: block; }

/* ═══════════════════════════════════════════════
   TICKER
═══════════════════════════════════════════════ */
.ticker {
  background: var(--bg-2); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
  padding: 14px 0; overflow: hidden; white-space: nowrap;
}
.ticker-inner {
  display: inline-flex; gap: 48px;
  animation: ticker 30s linear infinite;
}
@keyframes ticker { from{transform:translateX(0)} to{transform:translateX(-50%)} }
.tick-item { display: inline-flex; align-items: center; gap: 10px; font-family: var(--mono); font-size: .82em; }
.tick-sym { color: var(--text); font-weight: 600; }
.tick-price { color: var(--muted); }
.tick-up { color: var(--green); }
.tick-down { color: var(--red); }

/* ═══════════════════════════════════════════════
   STATS STRIP
═══════════════════════════════════════════════ */
.stats-strip {
  display: grid; grid-template-columns: repeat(4,1fr);
  border-bottom: 1px solid var(--border);
}
.stat-item {
  padding: 40px 32px; border-right: 1px solid var(--border); text-align: center;
}
.stat-item:last-child { border-right: none; }
.stat-num { font-size: 2.8em; font-weight: 800; color: var(--accent); line-height: 1; display: block; }
.stat-label { font-size: .8em; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-top: 6px; }

/* ═══════════════════════════════════════════════
   SECTIONS
═══════════════════════════════════════════════ */
section { padding: 100px 80px; }
.section-label {
  font-family: var(--mono); font-size: .72em; color: var(--accent);
  text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px;
}
.section-title {
  font-size: clamp(2em, 4vw, 3em); font-weight: 700; line-height: 1.15;
  letter-spacing: -.02em; margin-bottom: 16px;
}
.section-sub { font-size: 1.05em; color: var(--muted); max-width: 560px; line-height: 1.7; margin-bottom: 60px; }

/* ═══════════════════════════════════════════════
   FEATURES
═══════════════════════════════════════════════ */
#features { background: var(--bg-1); }
.features-grid {
  display: grid; grid-template-columns: repeat(3,1fr); gap: 1px;
  background: var(--border); border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
}
.feat {
  background: var(--bg-card); padding: 36px 32px;
  transition: background .2s;
}
.feat:hover { background: var(--bg-2); }
.feat-icon {
  width: 48px; height: 48px; border-radius: 10px;
  background: rgba(0,212,255,.1); border: 1px solid rgba(0,212,255,.2);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4em; margin-bottom: 20px;
}
.feat h3 { font-size: 1.05em; font-weight: 600; margin-bottom: 10px; }
.feat p { font-size: .88em; color: var(--muted); line-height: 1.7; }

/* ═══════════════════════════════════════════════
   HOW IT WORKS
═══════════════════════════════════════════════ */
.steps {
  display: grid; grid-template-columns: repeat(5,1fr); gap: 0; position: relative;
}
.steps::before {
  content: '';
  position: absolute; top: 28px; left: 10%; right: 10%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-hi), transparent);
}
.step { padding: 0 20px; text-align: center; position: relative; }
.step-num {
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--bg-card); border: 1px solid var(--border-hi);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--mono); font-weight: 700; font-size: 1.1em; color: var(--accent);
  margin: 0 auto 20px;
}
.step h3 { font-size: .95em; font-weight: 600; margin-bottom: 8px; }
.step p { font-size: .82em; color: var(--muted); line-height: 1.6; }

/* ═══════════════════════════════════════════════
   PERFORMANCE
═══════════════════════════════════════════════ */
#performance { background: var(--bg-1); }
.perf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: center; }
.perf-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.perf-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 24px;
}
.perf-card-val { font-size: 2em; font-weight: 800; margin-bottom: 4px; }
.perf-card-lbl { font-size: .78em; color: var(--muted); text-transform: uppercase; letter-spacing: .8px; }
.perf-card-sub { font-size: .8em; color: var(--muted); margin-top: 8px; }
.chart-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px;
}
.chart-card-title { font-size: .82em; color: var(--muted); margin-bottom: 16px; font-family: var(--mono); }

/* ═══════════════════════════════════════════════
   PAIRS TABLE
═══════════════════════════════════════════════ */
.pairs-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .9em; }
th {
  text-align: left; padding: 12px 16px; font-size: .72em; font-weight: 600;
  color: var(--muted); text-transform: uppercase; letter-spacing: 1px;
  border-bottom: 1px solid var(--border);
}
td { padding: 14px 16px; border-bottom: 1px solid var(--border); }
tr:hover td { background: var(--bg-2); }
tr:last-child td { border-bottom: none; }
.badge-buy { padding: 3px 10px; background: rgba(0,200,83,.15); color: var(--green); border-radius: 4px; font-size: .78em; font-weight: 700; }
.badge-sell { padding: 3px 10px; background: rgba(255,61,87,.15); color: var(--red); border-radius: 4px; font-size: .78em; font-weight: 700; }
.badge-ai { padding: 3px 10px; background: rgba(0,212,255,.1); color: var(--accent); border-radius: 4px; font-size: .78em; font-weight: 700; }
.g { color: var(--green); font-weight: 600; }
.r { color: var(--red); font-weight: 600; }

/* ═══════════════════════════════════════════════
   PLATFORM
═══════════════════════════════════════════════ */
.platform-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 60px; align-items: center; }
.platform-pills { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 32px; }
.platform-pill {
  padding: 6px 16px; border: 1px solid var(--border-hi); border-radius: 20px;
  font-size: .82em; color: var(--muted); display: flex; align-items: center; gap: 6px;
}
.platform-pill.active { border-color: var(--accent); color: var(--accent); background: rgba(0,212,255,.08); }
.platform-features { display: flex; flex-direction: column; gap: 16px; }
.pf { display: flex; align-items: flex-start; gap: 14px; }
.pf-icon { width: 36px; height: 36px; border-radius: 8px; background: rgba(0,212,255,.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1em; }
.pf-text h4 { font-size: .95em; font-weight: 600; margin-bottom: 4px; }
.pf-text p { font-size: .83em; color: var(--muted); line-height: 1.6; }
.dash-mock {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px;
  box-shadow: 0 30px 60px rgba(0,0,0,.5);
}
.dash-mock-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.dash-mock-brand { font-size: .85em; font-weight: 700; color: var(--accent); }
.dash-kpis { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-bottom: 16px; }
.dash-kpi { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.dash-kpi-val { font-size: 1.1em; font-weight: 700; color: var(--green); }
.dash-kpi-lbl { font-size: .7em; color: var(--muted); margin-top: 2px; }
.dash-chart { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }

/* ═══════════════════════════════════════════════
   PRICING / ACCESS
═══════════════════════════════════════════════ */
#access { background: var(--bg-1); }
.access-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 24px; }
.access-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 36px 32px;
  transition: border-color .2s, transform .2s;
}
.access-card:hover { border-color: var(--border-hi); transform: translateY(-4px); }
.access-card.featured {
  border-color: var(--accent); background: linear-gradient(135deg, var(--bg-card), rgba(0,212,255,.04));
}
.access-tag {
  font-family: var(--mono); font-size: .72em; color: var(--accent);
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;
  display: inline-block; padding: 4px 12px; border: 1px solid rgba(0,212,255,.3); border-radius: 4px;
}
.access-price { font-size: 2.6em; font-weight: 800; color: var(--text); line-height: 1; margin-bottom: 8px; }
.access-price span { font-size: .45em; color: var(--muted); font-weight: 400; }
.access-desc { font-size: .88em; color: var(--muted); margin-bottom: 28px; line-height: 1.6; }
.access-list { list-style: none; display: flex; flex-direction: column; gap: 10px; margin-bottom: 32px; }
.access-list li { font-size: .88em; color: var(--muted); display: flex; align-items: center; gap: 10px; }
.access-list li::before { content: '✓'; color: var(--accent2); font-weight: 700; flex-shrink: 0; }
.btn-full {
  display: block; text-align: center; padding: 13px 24px; border-radius: 8px;
  font-weight: 700; font-size: .95em; text-decoration: none;
  transition: opacity .2s;
}
.btn-full:hover { opacity: .85; }
.btn-full-accent { background: var(--accent); color: #000; }
.btn-full-outline { background: transparent; border: 1px solid var(--border-hi); color: var(--text); }

/* ═══════════════════════════════════════════════
   CTA BAND
═══════════════════════════════════════════════ */
.cta-band {
  padding: 100px 80px; text-align: center;
  background:
    radial-gradient(ellipse 60% 80% at 50% 50%, rgba(0,212,255,.07), transparent 70%),
    var(--bg);
  border-top: 1px solid var(--border);
}
.cta-band h2 { font-size: clamp(2em, 4vw, 3.2em); font-weight: 700; letter-spacing: -.02em; margin-bottom: 20px; }
.cta-band p { font-size: 1.05em; color: var(--muted); margin-bottom: 40px; }
.cta-buttons { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }

/* ═══════════════════════════════════════════════
   FAQ
═══════════════════════════════════════════════ */
.faq-grid { max-width: 760px; margin: 0 auto; }
details {
  border-bottom: 1px solid var(--border); padding: 20px 0;
}
details:first-child { border-top: 1px solid var(--border); }
summary {
  font-weight: 600; font-size: .98em; cursor: pointer; list-style: none;
  display: flex; justify-content: space-between; align-items: center;
}
summary::after { content: '+'; font-size: 1.4em; color: var(--accent); line-height: 1; }
details[open] summary::after { content: '−'; }
details p { margin-top: 14px; font-size: .9em; color: var(--muted); line-height: 1.8; }

/* ═══════════════════════════════════════════════
   FOOTER
═══════════════════════════════════════════════ */
footer {
  border-top: 1px solid var(--border);
  padding: 60px 80px 40px;
  background: var(--bg-1);
}
.foot-top { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 40px; margin-bottom: 48px; }
.foot-brand { font-weight: 700; font-size: 1.1em; color: var(--text); margin-bottom: 12px; }
.foot-desc { font-size: .85em; color: var(--muted); line-height: 1.7; }
.foot-col h4 { font-size: .82em; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin-bottom: 16px; }
.foot-col a { display: block; font-size: .88em; color: var(--muted); text-decoration: none; margin-bottom: 10px; transition: color .2s; }
.foot-col a:hover { color: var(--text); }
.foot-bottom { display: flex; justify-content: space-between; align-items: center; padding-top: 24px; border-top: 1px solid var(--border); }
.foot-copy { font-size: .78em; color: var(--muted); }
.foot-risk { font-size: .72em; color: var(--muted); max-width: 600px; text-align: right; line-height: 1.5; }

/* ═══════════════════════════════════════════════
   RESPONSIVE
═══════════════════════════════════════════════ */
@media(max-width: 1024px) {
  .hero { grid-template-columns: 1fr; padding: 100px 40px 60px; }
  .hero-visual { display: none; }
  .stats-strip { grid-template-columns: repeat(2,1fr); }
  .stat-item:nth-child(2) { border-right: none; }
  .features-grid { grid-template-columns: 1fr 1fr; }
  .steps { grid-template-columns: 1fr 1fr; gap: 32px; }
  .steps::before { display: none; }
  .perf-grid, .platform-grid, .access-grid { grid-template-columns: 1fr; }
  section { padding: 70px 40px; }
  footer { padding: 50px 40px 30px; }
  .foot-top { grid-template-columns: 1fr 1fr; }
  .cta-band { padding: 70px 40px; }
}
@media(max-width: 640px) {
  nav { padding: 0 20px; }
  .nav-links { display: none; }
  .hero { padding: 90px 20px 50px; }
  .features-grid { grid-template-columns: 1fr; }
  .stats-strip { grid-template-columns: 1fr 1fr; }
  section { padding: 60px 20px; }
  .foot-top { grid-template-columns: 1fr; }
  footer { padding: 40px 20px 24px; }
  .cta-band { padding: 60px 20px; }
  .foot-bottom { flex-direction: column; gap: 12px; }
  .foot-risk { text-align: left; }
}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <a href="/" class="nav-brand">
    <span class="dot"></span> FXPulse
  </a>
  <div class="nav-links">
    <a href="#features">Features</a>
    <a href="#how">How It Works</a>
    <a href="#performance">Performance</a>
    <a href="#access">Access</a>
    <a href="#faq">FAQ</a>
  </div>
  <div class="nav-cta">
    <a href="login.php" class="btn-ghost-sm">Sign In</a>
    <a href="register.php" class="btn-accent-sm">Get Access</a>
  </div>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="hero-content">
    <div class="hero-label">Live on Pepperstone MT5</div>
    <h1>
      Trade with<br>
      <em>AI Currency</em><br>
      <span class="gold">Intelligence</span>
    </h1>
    <p class="hero-sub">
      FXPulse runs 24/7 on a cloud server, scanning 28 forex pairs every 60 seconds using currency strength + Renko timing + XGBoost AI. No guesswork. Just edge.
    </p>
    <div class="hero-btns">
      <a href="register.php" class="btn-primary">
        <svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.873 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/></svg>
        Request Access
      </a>
      <a href="login.php" class="btn-outline">Sign In →</a>
    </div>
    <div class="hero-trust">
      <div class="trust-item">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0L6.2 5.9H0l4.9 3.6-1.9 5.9L8 12l4.9 3.4-1.9-5.9L16 5.9h-6.2z"/></svg>
        Pepperstone MT5
      </div>
      <div class="trust-item">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0L6.2 5.9H0l4.9 3.6-1.9 5.9L8 12l4.9 3.4-1.9-5.9L16 5.9h-6.2z"/></svg>
        Paper &amp; Live Trading
      </div>
      <div class="trust-item">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0L6.2 5.9H0l4.9 3.6-1.9 5.9L8 12l4.9 3.4-1.9-5.9L16 5.9h-6.2z"/></svg>
        24/7 Cloud Server
      </div>
    </div>
  </div>
  <div class="hero-visual">
    <div class="terminal">
      <div class="terminal-bar">
        <div class="t-dot" style="background:#ff5f57"></div>
        <div class="t-dot" style="background:#febc2e"></div>
        <div class="t-dot" style="background:#28c840"></div>
        <span style="margin-left:10px;font-family:var(--mono);font-size:.72em;color:var(--muted);">fxpulse — live scan</span>
      </div>
      <div class="terminal-body">
        <div class="t-line t-muted">═══════════════════════════════════</div>
        <div class="t-line"><span class="t-blue">CURRENCY STRENGTH</span> <span class="t-muted">15:42:07 UTC</span></div>
        <div class="t-line t-muted">───────────────────────────────────</div>
        <div class="t-line"><span class="t-muted">#1</span> <span class="t-green">USD  ▲  +0.0024</span> <span class="t-muted">████████</span></div>
        <div class="t-line"><span class="t-muted">#2</span> <span class="t-green">GBP  ▲  +0.0018</span> <span class="t-muted">██████</span></div>
        <div class="t-line"><span class="t-muted">#3</span> <span class="t-white">EUR  ─  +0.0003</span> <span class="t-muted">██</span></div>
        <div class="t-line"><span class="t-muted">#6</span> <span class="t-red">JPY  ▼  -0.0019</span> <span class="t-muted">██████</span></div>
        <div class="t-line"><span class="t-muted">#8</span> <span class="t-red">NZD  ▼  -0.0031</span> <span class="t-muted">█████████</span></div>
        <div class="t-line t-muted" style="margin-top:8px;">───────────────────────────────────</div>
        <div class="t-line"><span class="t-blue">TOP SETUP</span> <span class="t-gold">USDJPY.a</span></div>
        <div class="t-line"><span class="t-muted">  Direction:</span> <span class="t-green">BUY</span></div>
        <div class="t-line"><span class="t-muted">  AI Confidence:</span> <span class="t-green">78.4%</span> <span class="t-muted">✓ &gt;65% threshold</span></div>
        <div class="t-line"><span class="t-muted">  Gap:</span> <span class="t-gold">+0.0043</span></div>
        <div class="t-line"><span class="t-muted">  Regime:</span> <span class="t-green">TRENDING</span></div>
        <div class="t-line t-muted" style="margin-top:8px;">───────────────────────────────────</div>
        <div class="t-line t-green">✓ ORDER PLACED — 0.02 lots @ 157.842</div>
        <div class="t-line t-muted">  SL: 157.562 | TP: 158.402 | R:R 2:1</div>
      </div>
      <div class="chart-container">
        <canvas id="heroChart" height="100"></canvas>
      </div>
    </div>
  </div>
</section>

<!-- LIVE TICKER -->
<div class="ticker">
  <div class="ticker-inner" id="tickerInner">
    <div class="tick-item"><span class="tick-sym">EURUSD</span><span class="tick-price">1.0847</span><span class="tick-up">+0.12%</span></div>
    <div class="tick-item"><span class="tick-sym">GBPUSD</span><span class="tick-price">1.2634</span><span class="tick-up">+0.08%</span></div>
    <div class="tick-item"><span class="tick-sym">USDJPY</span><span class="tick-price">157.84</span><span class="tick-up">+0.31%</span></div>
    <div class="tick-item"><span class="tick-sym">USDCHF</span><span class="tick-price">0.9021</span><span class="tick-down">-0.05%</span></div>
    <div class="tick-item"><span class="tick-sym">AUDUSD</span><span class="tick-price">0.6548</span><span class="tick-down">-0.14%</span></div>
    <div class="tick-item"><span class="tick-sym">NZDUSD</span><span class="tick-price">0.5934</span><span class="tick-down">-0.22%</span></div>
    <div class="tick-item"><span class="tick-sym">USDCAD</span><span class="tick-price">1.3821</span><span class="tick-up">+0.09%</span></div>
    <div class="tick-item"><span class="tick-sym">XAUUSD</span><span class="tick-price">2,312.4</span><span class="tick-up">+0.55%</span></div>
    <div class="tick-item"><span class="tick-sym">EURJPY</span><span class="tick-price">171.18</span><span class="tick-up">+0.43%</span></div>
    <div class="tick-item"><span class="tick-sym">GBPJPY</span><span class="tick-price">199.42</span><span class="tick-up">+0.38%</span></div>
    <!-- duplicate for infinite scroll -->
    <div class="tick-item"><span class="tick-sym">EURUSD</span><span class="tick-price">1.0847</span><span class="tick-up">+0.12%</span></div>
    <div class="tick-item"><span class="tick-sym">GBPUSD</span><span class="tick-price">1.2634</span><span class="tick-up">+0.08%</span></div>
    <div class="tick-item"><span class="tick-sym">USDJPY</span><span class="tick-price">157.84</span><span class="tick-up">+0.31%</span></div>
    <div class="tick-item"><span class="tick-sym">USDCHF</span><span class="tick-price">0.9021</span><span class="tick-down">-0.05%</span></div>
    <div class="tick-item"><span class="tick-sym">AUDUSD</span><span class="tick-price">0.6548</span><span class="tick-down">-0.14%</span></div>
    <div class="tick-item"><span class="tick-sym">XAUUSD</span><span class="tick-price">2,312.4</span><span class="tick-up">+0.55%</span></div>
  </div>
</div>

<!-- STATS STRIP -->
<div class="stats-strip">
  <div class="stat-item">
    <span class="stat-num">65%+</span>
    <div class="stat-label">Target Win Rate</div>
  </div>
  <div class="stat-item">
    <span class="stat-num">28</span>
    <div class="stat-label">Pairs Monitored</div>
  </div>
  <div class="stat-item">
    <span class="stat-num">60s</span>
    <div class="stat-label">Scan Interval</div>
  </div>
  <div class="stat-item">
    <span class="stat-num">24/7</span>
    <div class="stat-label">Cloud Operation</div>
  </div>
</div>

<!-- FEATURES -->
<section id="features">
  <div class="section-label">Core Engine</div>
  <h2 class="section-title">Six layers of intelligence<br>before every trade</h2>
  <p class="section-sub">Most bots use one signal. FXPulse stacks six — and only fires when all align.</p>
  <div class="features-grid">
    <div class="feat">
      <div class="feat-icon">📊</div>
      <h3>Currency Strength Engine</h3>
      <p>Ranks all 8 major currencies (USD, EUR, GBP, JPY, AUD, NZD, CAD, CHF) across M15 + H1 timeframes every 60 seconds. Always trades the strongest vs. the weakest.</p>
    </div>
    <div class="feat">
      <div class="feat-icon">🤖</div>
      <h3>XGBoost + LSTM AI</h3>
      <p>Ensemble machine learning trained on thousands of historical setups. Assigns a win probability to every potential trade — only fires above 65% confidence.</p>
    </div>
    <div class="feat">
      <div class="feat-icon">🎯</div>
      <h3>Renko Pullback Timing</h3>
      <p>Simulates Renko charts from raw M1 data. Detects 2–4 brick pullbacks against the trend for precise continuation entry — not random breakouts.</p>
    </div>
    <div class="feat">
      <div class="feat-icon">📰</div>
      <h3>News & Regime Filter</h3>
      <p>Blocks all trading 30 minutes before high-impact economic events. ADX + ATR regime detector automatically skips ranging and crisis market conditions.</p>
    </div>
    <div class="feat">
      <div class="feat-icon">🛡️</div>
      <h3>Smart Risk Management</h3>
      <p>Kelly Criterion position sizing adapts to your win rate. Renko trailing stops, 50% partial close at 1R, break-even lock, and 5% daily drawdown circuit breaker.</p>
    </div>
    <div class="feat">
      <div class="feat-icon">🔗</div>
      <h3>Correlation Filter</h3>
      <p>Detects when proposed trades are correlated with existing open positions. Blocks duplicate exposure so you never accidentally double your risk.</p>
    </div>
  </div>
</section>

<!-- HOW IT WORKS -->
<section id="how" style="background:var(--bg-1);">
  <div style="text-align:center; margin-bottom:60px;">
    <div class="section-label" style="text-align:center;">Process</div>
    <h2 class="section-title">Five steps. 60 seconds. Repeat.</h2>
  </div>
  <div class="steps">
    <div class="step">
      <div class="step-num">01</div>
      <h3>Rank Currencies</h3>
      <p>Fetches M15 + H1 bars from MT5, calculates RSI momentum and MA divergence for all 8 currencies.</p>
    </div>
    <div class="step">
      <div class="step-num">02</div>
      <h3>Find the Gap</h3>
      <p>Identifies top 3 pairs where the gap between strongest and weakest exceeds the minimum threshold.</p>
    </div>
    <div class="step">
      <div class="step-num">03</div>
      <h3>Check Filters</h3>
      <p>Validates regime, session, spread, news calendar, correlation — any failure kills the trade idea.</p>
    </div>
    <div class="step">
      <div class="step-num">04</div>
      <h3>AI Scores It</h3>
      <p>XGBoost + LSTM ensemble scores the setup. Below 65% confidence = skipped. No exceptions.</p>
    </div>
    <div class="step">
      <div class="step-num">05</div>
      <h3>Execute & Manage</h3>
      <p>Places trade with Kelly-sized lots. Autonomously manages SL, partial close, break-even, Renko trail.</p>
    </div>
  </div>
</section>

<!-- PERFORMANCE -->
<section id="performance">
  <div class="section-label">Edge</div>
  <h2 class="section-title">Built for consistent edge,<br>not lottery wins</h2>
  <p class="section-sub">Paper trading targets validate the model before risking real capital.</p>
  <div class="perf-grid">
    <div class="perf-cards">
      <div class="perf-card">
        <div class="perf-card-val" style="color:var(--accent)">65%+</div>
        <div class="perf-card-lbl">Target Win Rate</div>
        <div class="perf-card-sub">XGBoost threshold gate</div>
      </div>
      <div class="perf-card">
        <div class="perf-card-val" style="color:var(--green)">2:1</div>
        <div class="perf-card-lbl">Risk:Reward</div>
        <div class="perf-card-sub">TP at 2R, SL at 1R</div>
      </div>
      <div class="perf-card">
        <div class="perf-card-val" style="color:var(--gold)">1%</div>
        <div class="perf-card-lbl">Risk Per Trade</div>
        <div class="perf-card-sub">Kelly-adjusted sizing</div>
      </div>
      <div class="perf-card">
        <div class="perf-card-val" style="color:var(--red)">5%</div>
        <div class="perf-card-lbl">Daily Drawdown Limit</div>
        <div class="perf-card-sub">Hard stop — bot pauses</div>
      </div>
    </div>
    <div class="chart-card">
      <div class="chart-card-title">SAMPLE EQUITY CURVE — Paper Trading Simulation</div>
      <canvas id="perfChart" height="200"></canvas>
    </div>
  </div>
</section>

<!-- PAIRS TABLE -->
<section style="background:var(--bg-1); padding-top:0;">
  <h3 style="font-size:1em;color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-family:var(--mono);margin-bottom:20px;">Monitored Instruments</h3>
  <div class="pairs-wrap">
    <table>
      <thead>
        <tr>
          <th>Symbol</th><th>Category</th><th>Typical Direction</th><th>AI Eligible</th><th>Avg Spread</th>
        </tr>
      </thead>
      <tbody>
        <tr><td><b>EURUSD.a</b></td><td>Major</td><td><span class="badge-buy">BUY/SELL</span></td><td><span class="badge-ai">✓ AI</span></td><td class="g">0.8 pips</td></tr>
        <tr><td><b>GBPUSD.a</b></td><td>Major</td><td><span class="badge-buy">BUY/SELL</span></td><td><span class="badge-ai">✓ AI</span></td><td class="g">1.0 pips</td></tr>
        <tr><td><b>USDJPY.a</b></td><td>Major</td><td><span class="badge-buy">BUY/SELL</span></td><td><span class="badge-ai">✓ AI</span></td><td class="g">0.7 pips</td></tr>
        <tr><td><b>XAUUSD.a</b></td><td>Commodity</td><td><span class="badge-buy">BUY/SELL</span></td><td><span class="badge-ai">✓ AI</span></td><td>2.1 pips</td></tr>
        <tr><td><b>GBPJPY.a</b></td><td>Cross</td><td><span class="badge-buy">BUY/SELL</span></td><td><span class="badge-ai">✓ AI</span></td><td>1.8 pips</td></tr>
        <tr><td><b>US500.a</b></td><td>Index</td><td><span class="badge-buy">BUY/SELL</span></td><td><span class="badge-ai">✓ AI</span></td><td>0.4 pips</td></tr>
      </tbody>
    </table>
  </div>
</section>

<!-- PLATFORM -->
<section id="platform">
  <div class="platform-grid">
    <div>
      <div class="section-label">Dashboard</div>
      <h2 class="section-title">Your live command<br>centre</h2>
      <p class="section-sub">View real-time currency rankings, AI trade scores, open positions and P&L from any browser — anywhere in the world.</p>
      <div class="platform-pills">
        <div class="platform-pill active">Web Dashboard</div>
        <div class="platform-pill">Telegram Alerts</div>
        <div class="platform-pill">MT5 Terminal</div>
        <div class="platform-pill">Performance CSV</div>
      </div>
      <div class="platform-features">
        <div class="pf">
          <div class="pf-icon">⚡</div>
          <div class="pf-text">
            <h4>30-Second Auto-Refresh</h4>
            <p>Dashboard pulls new bot state every 30 seconds. Watch trades open and close in near-real-time.</p>
          </div>
        </div>
        <div class="pf">
          <div class="pf-icon">📱</div>
          <div class="pf-text">
            <h4>Telegram Push Alerts</h4>
            <p>Instant notification every time a trade opens, closes, or hits its stop — straight to your phone.</p>
          </div>
        </div>
        <div class="pf">
          <div class="pf-icon">👥</div>
          <div class="pf-text">
            <h4>Multi-User Access</h4>
            <p>Share view-only access with clients or partners. Separate roles for admin and viewer accounts.</p>
          </div>
        </div>
      </div>
    </div>
    <div>
      <div class="dash-mock">
        <div class="dash-mock-bar">
          <div class="dash-mock-brand">▲ FXPulse</div>
          <div style="font-family:var(--mono);font-size:.72em;color:var(--green);">● LIVE</div>
        </div>
        <div class="dash-kpis">
          <div class="dash-kpi"><div class="dash-kpi-val">$10,284</div><div class="dash-kpi-lbl">Balance</div></div>
          <div class="dash-kpi"><div class="dash-kpi-val" style="color:var(--accent)">68.2%</div><div class="dash-kpi-lbl">Win Rate</div></div>
          <div class="dash-kpi"><div class="dash-kpi-val">+$284</div><div class="dash-kpi-lbl">P&L</div></div>
        </div>
        <div class="dash-chart">
          <canvas id="mockChart" height="80"></canvas>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ACCESS / PRICING -->
<section id="access">
  <div style="text-align:center; margin-bottom:60px;">
    <div class="section-label" style="text-align:center;">Access</div>
    <h2 class="section-title">Start with zero risk</h2>
    <p class="section-sub" style="margin:0 auto 0;">Paper trading mode included — test for weeks before going live. Request access and an admin approves you within 5 minutes.</p>
  </div>
  <div class="access-grid">
    <div class="access-card">
      <div class="access-tag">Paper Demo</div>
      <div class="access-price">Free</div>
      <p class="access-desc">Full access to dashboard and all signals in paper trading mode. Zero risk.</p>
      <ul class="access-list">
        <li>Live dashboard access</li>
        <li>Currency strength rankings</li>
        <li>AI signal confidence scores</li>
        <li>Virtual $10,000 paper balance</li>
        <li>Telegram alerts</li>
      </ul>
      <a href="register.php" class="btn-full btn-full-outline">Request Access →</a>
    </div>
    <div class="access-card featured">
      <div class="access-tag">Live Trading</div>
      <div class="access-price">By Invite</div>
      <p class="access-desc">Approved after 2–4 weeks of paper trading success. Pepperstone account required.</p>
      <ul class="access-list">
        <li>Everything in Paper Demo</li>
        <li>Live MT5 order execution</li>
        <li>Kelly Criterion sizing</li>
        <li>Full trade management</li>
        <li>Priority support</li>
      </ul>
      <a href="register.php" class="btn-full btn-full-accent">Apply for Live Access →</a>
    </div>
    <div class="access-card">
      <div class="access-tag">Partner / Viewer</div>
      <div class="access-price">Shared</div>
      <p class="access-desc">Investor or partner access to monitor live performance in real time.</p>
      <ul class="access-list">
        <li>Read-only dashboard</li>
        <li>Account balance & P&L</li>
        <li>Open trades view</li>
        <li>Performance history</li>
        <li>No trading controls</li>
      </ul>
      <a href="register.php" class="btn-full btn-full-outline">Request Viewer Access →</a>
    </div>
  </div>
</section>

<!-- CTA BAND -->
<div class="cta-band">
  <h2>Ready to trade with an edge?</h2>
  <p>Join FXPulse — start in paper mode, graduate to live when you're confident.</p>
  <div class="cta-buttons">
    <a href="register.php" class="btn-primary">Request Access →</a>
    <a href="login.php" class="btn-outline">Sign In</a>
  </div>
</div>

<!-- FAQ -->
<section id="faq" style="background:var(--bg-1);">
  <div style="text-align:center; margin-bottom:60px;">
    <div class="section-label" style="text-align:center;">FAQ</div>
    <h2 class="section-title">Common questions</h2>
  </div>
  <div class="faq-grid">
    <details>
      <summary>Does the bot trade automatically without my input?</summary>
      <p>Yes. FXPulse runs entirely autonomously 24/7 on a cloud Windows VPS with MetaTrader 5 installed. Once configured, it scans markets every 60 seconds, places trades, manages stops, and closes positions — all without human intervention.</p>
    </details>
    <details>
      <summary>Which broker do I need?</summary>
      <p>FXPulse is built for Pepperstone MT5 (demo or live). Pepperstone offers tight spreads, fast execution, and reliable demo accounts with no time limit. You'll need to open a free Pepperstone account and link it in the configuration.</p>
    </details>
    <details>
      <summary>What does the AI actually do?</summary>
      <p>The XGBoost model is trained on historical trade setups — taking 20+ features including currency strength scores, Renko pattern data, regime, spread, and session — and outputs a win probability. Only setups scoring 65%+ are executed.</p>
    </details>
    <details>
      <summary>How is risk managed?</summary>
      <p>Risk is managed at multiple levels: 1% per trade (Kelly-adjusted), 5% daily drawdown halt, correlation filter blocking duplicate exposure, news filter blocking high-impact events, and automatic partial close + break-even at 1R.</p>
    </details>
    <details>
      <summary>Can I view results without running the bot?</summary>
      <p>Yes. The web dashboard at <a href="https://myforexpulse.com/dashboard.php" style="color:var(--accent);">myforexpulse.com</a> shows live data pushed from the bot. Viewer accounts can monitor all performance metrics, open trades, and currency rankings without any access to the bot configuration.</p>
    </details>
    <details>
      <summary>How long before I can go live?</summary>
      <p>We recommend at least 2–4 weeks of paper trading to validate the strategy in current market conditions. Live access is granted by invite after reviewing paper trading performance.</p>
    </details>
  </div>
</section>

<!-- FOOTER -->
<footer>
  <div class="foot-top">
    <div>
      <div class="foot-brand">▲ FXPulse</div>
      <p class="foot-desc">AI-powered forex intelligence combining currency strength, Renko timing, and machine learning. Built for Pepperstone MT5.</p>
    </div>
    <div class="foot-col">
      <h4>Platform</h4>
      <a href="#features">Features</a>
      <a href="#how">How It Works</a>
      <a href="#performance">Performance</a>
      <a href="dashboard.php">Dashboard</a>
      <a href="guide.html">Trader's Guide</a>
    </div>
    <div class="foot-col">
      <h4>Access</h4>
      <a href="register.php">Request Access</a>
      <a href="login.php">Sign In</a>
      <a href="#faq">FAQ</a>
    </div>
    <div class="foot-col">
      <h4>Broker</h4>
      <a href="https://pepperstone.com" target="_blank" rel="noopener">Pepperstone</a>
      <a href="https://www.metatrader5.com/en/download" target="_blank" rel="noopener">MT5 Platform</a>
      <a href="#access">Demo Account</a>
    </div>
  </div>
  <div class="foot-bottom">
    <div class="foot-copy">&copy; 2026 FXPulse. All rights reserved.</div>
    <div class="foot-risk">Trading forex and CFDs involves significant risk of loss and is not suitable for all investors. Past performance is not indicative of future results. FXPulse operates in paper trading mode by default.</div>
  </div>
</footer>

<script>
// Hero sparkline
(function(){
  const d = [100,102,101,104,103,106,105,108,107,110,109,112,111,114,116,115,118,117,120];
  const ctx = document.getElementById('heroChart');
  if(!ctx) return;
  new Chart(ctx.getContext('2d'), {
    type:'line',
    data:{labels:d.map((_,i)=>i),datasets:[{data:d,borderColor:'#00ff88',borderWidth:2,
      backgroundColor:'rgba(0,255,136,.08)',fill:true,tension:.4,pointRadius:0}]},
    options:{responsive:true,animation:false,plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{x:{display:false},y:{display:false}}}
  });
})();

// Performance chart
(function(){
  const ctx = document.getElementById('perfChart');
  if(!ctx) return;
  const labels=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const data=[10000,10180,10290,10420,10380,10510,10690,10820,10780,10950,11120,11284];
  new Chart(ctx.getContext('2d'), {
    type:'line',
    data:{labels,datasets:[{label:'Equity',data,borderColor:'#00d4ff',borderWidth:2,
      backgroundColor:'rgba(0,212,255,.07)',fill:true,tension:.4,pointRadius:3,
      pointBackgroundColor:'#00d4ff',pointHoverRadius:5}]},
    options:{
      responsive:true,animation:false,
      plugins:{legend:{display:false},
        tooltip:{backgroundColor:'#131a23',borderColor:'#1e2d3d',borderWidth:1,
          titleColor:'#8b949e',bodyColor:'#e2eaf3',
          callbacks:{label:c=>'$'+c.parsed.y.toLocaleString()}}},
      scales:{
        x:{grid:{color:'#1e2d3d'},ticks:{color:'#6b8299',font:{size:11}}},
        y:{grid:{color:'#1e2d3d'},ticks:{color:'#6b8299',font:{size:11},callback:v=>'$'+v.toLocaleString()}}
      }
    }
  });
})();

// Mock dashboard chart
(function(){
  const ctx = document.getElementById('mockChart');
  if(!ctx) return;
  const d=[100,102,101,103,105,104,106,108,107,109,111,110,113,112,115];
  new Chart(ctx.getContext('2d'), {
    type:'line',
    data:{labels:d.map((_,i)=>i),datasets:[{data:d,borderColor:'#58a6ff',borderWidth:2,
      backgroundColor:'rgba(88,166,255,.08)',fill:true,tension:.4,pointRadius:0}]},
    options:{responsive:true,animation:false,plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{x:{display:false},y:{display:false}}}
  });
})();
</script>
</body>
</html>

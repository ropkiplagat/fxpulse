<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/mt5_accounts.php';

session_init();
require_login();

$user     = current_user();
$username = $user['username'];
$errors   = [];
$success  = false;

// ── Handle disconnect ──────────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'disconnect') {
    if (!verify_csrf($_POST['csrf_token'] ?? '')) {
        $errors[] = 'Invalid request. Please try again.';
    } else {
        disconnect_mt5_account($username);
        header('Location: connect-mt5.php?disconnected=1');
        exit;
    }
}

// ── If already connected, show manage screen ──────────────────────────────
$existing    = get_mt5_account($username);
$has_account = has_active_mt5_account($username);

// ── Handle new connection ─────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'connect') {

    // Honeypot — bots fill this field, humans don't
    if (!empty($_POST['website'])) {
        header('Location: connect-mt5.php');
        exit;
    }

    if (!verify_csrf($_POST['csrf_token'] ?? '')) {
        $errors[] = 'Invalid security token. Please refresh and try again.';
    } else {
        $mt5_login    = preg_replace('/\D/', '', $_POST['mt5_login']    ?? '');
        $mt5_password = $_POST['mt5_password'] ?? '';
        $broker       = $_POST['broker_server']  ?? '';
        $lot_size     = $_POST['lot_size']      ?? '';
        $acct_type    = $_POST['account_type']  ?? '';

        if (strlen($mt5_login) < 5 || strlen($mt5_login) > 9)
            $errors[] = 'MT5 Account Number must be 5–9 digits.';

        if (strlen($mt5_password) < 4)
            $errors[] = 'MT5 Password must be at least 4 characters.';

        if (!in_array($broker, allowed_brokers(), true))
            $errors[] = 'Please select a valid broker server.';

        if (!in_array($lot_size, allowed_lot_sizes(), true))
            $errors[] = 'Please select a valid lot size.';

        if (!in_array($acct_type, ['demo', 'live'], true))
            $errors[] = 'Please select Demo or Live.';

        if (empty($errors)) {
            create_mt5_account($username, $mt5_login, $mt5_password, $broker, $lot_size, $acct_type);
            header('Location: dashboard.php');
            exit;
        }
    }
}

$csrf         = generate_csrf();
$disconnected = isset($_GET['disconnected']);
$new_user     = isset($_GET['new']);
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connect MT5 — FXPulse</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg:        #06080f;
  --panel:     #0b0f1c;
  --card:      rgba(255,255,255,0.035);
  --border:    rgba(255,255,255,0.07);
  --blue:      #1a6fff;
  --blue-dim:  rgba(26,111,255,0.12);
  --blue-glow: rgba(26,111,255,0.25);
  --gold:      #e8a022;
  --gold-dim:  rgba(232,160,34,0.1);
  --green:     #00d98b;
  --red:       #ff4757;
  --text:      #c8d8ed;
  --muted:     rgba(200,216,237,0.35);
  --faint:     rgba(200,216,237,0.12);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;font-family:'Sora',sans-serif;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}

/* ═══════════════════════════════════════════
   LAYOUT
═══════════════════════════════════════════ */
.wrap{display:flex;min-height:100vh;width:100%}

/* ═══════════════════════════════════════════
   LEFT PANEL — INTELLIGENCE CANVAS
═══════════════════════════════════════════ */
.left{
  flex:1.2;position:relative;overflow:hidden;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:44px 48px;background:var(--bg);
}

/* Animated mesh gradient bg */
.left-bg{
  position:absolute;inset:0;z-index:0;
  background:
    radial-gradient(ellipse 70% 50% at 20% 20%, rgba(26,111,255,0.07) 0%, transparent 60%),
    radial-gradient(ellipse 50% 40% at 80% 80%, rgba(232,160,34,0.05) 0%, transparent 60%),
    radial-gradient(ellipse 60% 60% at 50% 50%, rgba(0,217,139,0.02) 0%, transparent 70%),
    #06080f;
  animation:mesh-drift 12s ease-in-out infinite alternate;
}
@keyframes mesh-drift{
  0%  {background-position:0% 0%,100% 100%,50% 50%}
  100%{background-position:5% 8%,93% 96%,48% 53%}
}

/* Fine grid */
.left-grid{
  position:absolute;inset:0;z-index:1;
  background-image:
    linear-gradient(rgba(26,111,255,0.06) 1px,transparent 1px),
    linear-gradient(90deg,rgba(26,111,255,0.06) 1px,transparent 1px);
  background-size:48px 48px;
  mask-image:radial-gradient(ellipse 90% 90% at 50% 50%,black 0%,transparent 100%);
}

/* SVG network canvas */
.left-svg{position:absolute;inset:0;z-index:2;pointer-events:none;opacity:0.55}

/* Content layers */
.l-inner{position:relative;z-index:3;display:flex;flex-direction:column;height:100%;gap:0}

/* Brand */
.l-brand{display:flex;align-items:center;gap:10px}
.l-brand-mark{
  width:32px;height:32px;border-radius:8px;
  background:linear-gradient(135deg,var(--blue) 0%,#0047cc 100%);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 16px rgba(26,111,255,0.35);
  flex-shrink:0;
}
.l-brand-mark svg{width:18px;height:18px;fill:#fff}
.l-brand-text{display:flex;flex-direction:column}
.l-brand-name{font-size:18px;font-weight:700;color:#fff;letter-spacing:-0.3px;line-height:1}
.l-brand-name em{color:var(--blue);font-style:normal}
.l-brand-sub{font-size:9px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);margin-top:3px}

/* Step indicator */
.l-step{
  display:inline-flex;align-items:center;gap:8px;margin-top:auto;padding-top:52px;
}
.l-step-nodes{display:flex;align-items:center;gap:0}
.l-step-node{
  width:28px;height:28px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:600;
}
.l-step-node.done{background:var(--blue);color:#fff;box-shadow:0 0 12px var(--blue-glow)}
.l-step-node.active{background:var(--panel);border:2px solid var(--blue);color:var(--blue)}
.l-step-line{width:32px;height:2px;background:var(--blue);opacity:0.5}
.l-step-label{font-size:11px;color:var(--muted);margin-left:12px;letter-spacing:0.3px}

/* Headline */
.l-headline{
  margin-top:28px;
}
.l-eyebrow{
  font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--blue);
  opacity:0.8;margin-bottom:14px;
  display:flex;align-items:center;gap:8px;
}
.l-eyebrow::before{content:'';width:20px;height:1px;background:var(--blue);opacity:0.6}
.l-title{font-size:clamp(26px,3vw,36px);font-weight:700;line-height:1.1;color:#fff;letter-spacing:-0.5px}
.l-title span{color:var(--blue);display:block}
.l-desc{margin-top:14px;font-size:13px;line-height:1.75;color:var(--muted);max-width:320px;font-weight:300}

/* Live signal badge */
.l-signal{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(0,217,139,0.07);border:1px solid rgba(0,217,139,0.2);
  border-radius:20px;padding:6px 14px;font-size:11px;color:var(--green);
  margin-top:20px;width:fit-content;letter-spacing:0.4px;
}
.l-dot{
  width:6px;height:6px;border-radius:50%;background:var(--green);flex-shrink:0;
  animation:sig-pulse 1.8s ease-in-out infinite;
}
@keyframes sig-pulse{0%,100%{box-shadow:0 0 0 0 rgba(0,217,139,0.5)}50%{box-shadow:0 0 0 5px rgba(0,217,139,0)}}

/* Price board */
.l-prices{
  margin-top:32px;
  background:rgba(255,255,255,0.025);
  border:1px solid var(--border);
  border-radius:12px;overflow:hidden;
}
.l-prices-hdr{
  display:flex;align-items:center;justify-content:space-between;
  padding:11px 16px;border-bottom:1px solid var(--border);
}
.l-prices-title{font-size:9px;letter-spacing:3px;text-transform:uppercase;color:rgba(26,111,255,0.7)}
.l-prices-live{font-size:9px;color:var(--green);letter-spacing:1px;text-transform:uppercase;display:flex;align-items:center;gap:5px}
.l-prices-live::before{content:'';width:5px;height:5px;border-radius:50%;background:var(--green);display:inline-block;animation:sig-pulse 1.8s infinite}

.l-pair{
  display:grid;grid-template-columns:80px 1fr auto 70px;align-items:center;
  padding:9px 16px;border-bottom:1px solid rgba(255,255,255,0.025);
  transition:background 0.15s;
}
.l-pair:last-child{border-bottom:none}
.l-pair:hover{background:rgba(26,111,255,0.03)}
.l-pair-name{font-family:'JetBrains Mono',monospace;font-size:12px;color:#fff;font-weight:500;letter-spacing:0.5px}
.l-pair-bar{height:2px;border-radius:2px;background:rgba(255,255,255,0.06);position:relative;margin:0 12px}
.l-pair-bar-fill{height:100%;border-radius:2px;animation:bar-grow 1.2s ease-out forwards}
@keyframes bar-grow{from{width:0%}to{width:var(--w)}}
.l-pair-price{font-family:'JetBrains Mono',monospace;font-size:12px;color:#fff;text-align:right}
.l-pair-chg{font-size:11px;font-family:'JetBrains Mono',monospace;padding:2px 8px;border-radius:4px;text-align:right;font-weight:500}
.chg-up{color:var(--green);background:rgba(0,217,139,0.08)}
.chg-dn{color:var(--red);background:rgba(255,71,87,0.08)}

/* Trust bar */
.l-trust{
  margin-top:24px;display:flex;gap:20px;flex-wrap:wrap;
}
.l-trust-item{
  display:flex;align-items:center;gap:7px;
  font-size:11px;color:var(--faint);font-weight:400;
}
.l-trust-check{
  width:16px;height:16px;border-radius:4px;flex-shrink:0;
  background:rgba(232,160,34,0.12);border:1px solid rgba(232,160,34,0.3);
  display:flex;align-items:center;justify-content:center;
  font-size:9px;color:var(--gold);
}

/* ═══════════════════════════════════════════
   RIGHT PANEL — FORM
═══════════════════════════════════════════ */
.right{
  width:480px;flex-shrink:0;
  background:var(--panel);
  border-left:1px solid var(--border);
  display:flex;flex-direction:column;justify-content:center;
  padding:52px 44px;overflow-y:auto;
  position:relative;
}
.right::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--blue-glow),transparent);
  opacity:0.6;
}

/* Form header */
.f-eyebrow{font-size:9px;letter-spacing:3.5px;text-transform:uppercase;color:var(--blue);opacity:0.85;margin-bottom:8px}
.f-title{font-size:26px;font-weight:700;color:#fff;line-height:1.15;letter-spacing:-0.4px}
.f-sub{font-size:13px;color:var(--muted);margin-top:8px;line-height:1.65;margin-bottom:28px;font-weight:300}

/* Alerts */
.alert{border-radius:10px;padding:12px 16px;margin-bottom:20px;font-size:13px;line-height:1.6}
.alert-error{background:rgba(255,71,87,0.07);border:1px solid rgba(255,71,87,0.25);color:#ff8a99}
.alert-info{background:rgba(26,111,255,0.06);border:1px solid rgba(26,111,255,0.2);color:#7db8ff}
.alert ul{padding-left:16px}.alert li{margin-bottom:3px}

/* Floating label fields */
.field{position:relative;margin-bottom:18px}
.field label{
  display:block;font-size:10px;letter-spacing:2px;text-transform:uppercase;
  color:var(--muted);margin-bottom:8px;font-weight:500;
}
.field input,.field select{
  width:100%;
  background:rgba(255,255,255,0.04);
  border:1px solid var(--border);
  border-radius:10px;padding:13px 16px;
  color:#fff;font-family:'Sora',sans-serif;font-size:14px;font-weight:400;
  outline:none;
  transition:border-color 0.2s,background 0.2s,box-shadow 0.2s;
  appearance:none;-webkit-appearance:none;
}
.field input::placeholder{color:rgba(200,216,237,0.2)}
.field input:focus,.field select:focus{
  border-color:rgba(26,111,255,0.6);
  background:rgba(26,111,255,0.04);
  box-shadow:0 0 0 3px rgba(26,111,255,0.1);
}
.field select option{background:#0b0f1c;color:#fff}

/* Password field with eye toggle */
.pw-wrap{position:relative}
.pw-wrap input{padding-right:44px}
.pw-eye{
  position:absolute;right:14px;top:50%;transform:translateY(-50%);
  background:none;border:none;cursor:pointer;color:var(--muted);padding:0;
  transition:color 0.2s;line-height:1;
}
.pw-eye:hover{color:var(--blue)}

/* Select arrow */
.sel-wrap{position:relative}
.sel-wrap::after{
  content:'';position:absolute;right:16px;top:50%;transform:translateY(-50%) rotate(45deg);
  width:6px;height:6px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);
  pointer-events:none;margin-top:-2px;
}

/* Account type toggle */
.type-group{display:flex;gap:8px;margin-bottom:0}
.type-btn{
  flex:1;padding:11px 8px;border-radius:9px;text-align:center;cursor:pointer;
  border:1px solid var(--border);background:var(--card);
  font-family:'Sora',sans-serif;font-size:13px;font-weight:500;
  color:var(--muted);transition:all 0.2s;user-select:none;
}
.type-btn:hover{border-color:rgba(200,216,237,0.15);color:var(--text)}
.type-btn.sel-demo{
  border-color:rgba(26,111,255,0.5);background:var(--blue-dim);
  color:var(--blue);box-shadow:0 0 16px rgba(26,111,255,0.1);
}
.type-btn.sel-live{
  border-color:rgba(232,160,34,0.5);background:var(--gold-dim);
  color:var(--gold);box-shadow:0 0 16px rgba(232,160,34,0.08);
}
.type-label{font-size:9px;display:block;margin-top:2px;opacity:0.55;font-weight:400;text-transform:uppercase;letter-spacing:1px}

/* Lot size selector */
.lot-group{display:flex;gap:8px}
.lot-btn{
  flex:1;padding:11px 8px;border-radius:9px;text-align:center;cursor:pointer;
  border:1px solid var(--border);background:var(--card);
  font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:500;
  color:var(--muted);transition:all 0.2s;user-select:none;
}
.lot-btn:hover{border-color:rgba(200,216,237,0.15);color:var(--text)}
.lot-btn.sel{
  border-color:rgba(232,160,34,0.45);background:var(--gold-dim);
  color:var(--gold);box-shadow:0 0 12px rgba(232,160,34,0.08);
}
.lot-lbl{font-size:9px;display:block;margin-top:3px;font-family:'Sora',sans-serif;opacity:0.5;text-transform:uppercase;letter-spacing:0.8px}

/* Submit button */
.btn-submit{
  width:100%;margin-top:10px;padding:15px;border:none;border-radius:10px;cursor:pointer;
  background:linear-gradient(135deg,var(--blue) 0%,#0047cc 100%);
  color:#fff;font-family:'Sora',sans-serif;font-size:14px;font-weight:600;
  letter-spacing:0.5px;position:relative;overflow:hidden;
  box-shadow:0 4px 24px rgba(26,111,255,0.3);
  transition:opacity 0.2s,transform 0.15s,box-shadow 0.2s;
}
.btn-submit:hover{opacity:0.92;transform:translateY(-1px);box-shadow:0 8px 32px rgba(26,111,255,0.4)}
.btn-submit:active{transform:translateY(0)}
.btn-submit::after{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,0.1) 0%,transparent 50%);
  pointer-events:none;
}

/* Security note */
.enc-note{
  display:flex;align-items:center;justify-content:center;gap:6px;
  margin-top:14px;font-size:11px;color:var(--faint);
}
.enc-lock{
  width:14px;height:14px;border-radius:3px;border:1px solid rgba(232,160,34,0.3);
  background:rgba(232,160,34,0.08);display:flex;align-items:center;justify-content:center;
  font-size:8px;color:var(--gold);flex-shrink:0;
}
.back-link{
  display:block;text-align:center;margin-top:16px;font-size:12px;
  color:var(--faint);text-decoration:none;transition:color 0.2s;
}
.back-link:hover{color:var(--blue)}

/* Account card (manage screen) */
.acct-card{
  background:rgba(26,111,255,0.04);
  border:1px solid rgba(26,111,255,0.15);
  border-radius:12px;padding:20px;margin-bottom:24px;
}
.acct-row{display:flex;justify-content:space-between;align-items:center;padding:9px 0}
.acct-row:not(:last-child){border-bottom:1px solid rgba(255,255,255,0.04)}
.acct-key{font-size:9px;text-transform:uppercase;letter-spacing:2.5px;color:var(--muted)}
.acct-val{font-size:13px;font-weight:600;color:#fff;font-family:'JetBrains Mono',monospace}
.acct-val.accent{color:var(--blue)}
.badge-demo{background:rgba(26,111,255,0.1);color:var(--blue);border:1px solid rgba(26,111,255,0.3);padding:3px 10px;border-radius:20px;font-size:10px;font-family:'Sora',sans-serif;letter-spacing:0.5px}
.badge-live{background:rgba(0,217,139,0.1);color:var(--green);border:1px solid rgba(0,217,139,0.3);padding:3px 10px;border-radius:20px;font-size:10px;font-family:'Sora',sans-serif;letter-spacing:0.5px}
.btn-danger{
  width:100%;padding:14px;background:transparent;color:var(--red);
  border:1px solid rgba(255,71,87,0.25);border-radius:10px;
  font-family:'Sora',sans-serif;font-size:13px;font-weight:600;cursor:pointer;
  transition:background 0.2s,border-color 0.2s;letter-spacing:0.3px;
}
.btn-danger:hover{background:rgba(255,71,87,0.06);border-color:var(--red)}

/* Responsive */
@media(max-width:960px){
  html,body{height:auto}
  .left{display:none}
  .wrap{justify-content:center;min-height:100vh}
  .right{width:100%;max-width:520px;margin:0 auto;padding:52px 24px;border-left:none;justify-content:flex-start;padding-top:60px}
}
@media(max-width:480px){
  .right{padding:40px 20px}
  .f-title{font-size:22px}
  .type-group,.lot-group{flex-wrap:wrap}
  .type-btn,.lot-btn{flex:1 1 calc(50% - 4px)}
}
</style>
</head>
<body>
<div class="wrap">

  <!-- ═══ LEFT PANEL ═══ -->
  <div class="left">
    <div class="left-bg"></div>
    <div class="left-grid"></div>

    <!-- Animated network SVG -->
    <svg class="left-svg" viewBox="0 0 600 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="ng" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#1a6fff" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#1a6fff" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <!-- Connection lines -->
      <line x1="80" y1="200" x2="300" y2="420" stroke="rgba(26,111,255,0.15)" stroke-width="1">
        <animate attributeName="stroke-opacity" values="0.15;0.4;0.15" dur="4s" repeatCount="indefinite"/>
      </line>
      <line x1="300" y1="420" x2="520" y2="280" stroke="rgba(26,111,255,0.1)" stroke-width="1">
        <animate attributeName="stroke-opacity" values="0.1;0.3;0.1" dur="5s" repeatCount="indefinite"/>
      </line>
      <line x1="300" y1="420" x2="180" y2="650" stroke="rgba(232,160,34,0.12)" stroke-width="1">
        <animate attributeName="stroke-opacity" values="0.12;0.35;0.12" dur="6s" repeatCount="indefinite"/>
      </line>
      <line x1="520" y1="280" x2="450" y2="600" stroke="rgba(26,111,255,0.08)" stroke-width="1">
        <animate attributeName="stroke-opacity" values="0.08;0.25;0.08" dur="7s" repeatCount="indefinite"/>
      </line>
      <line x1="80" y1="200" x2="180" y2="650" stroke="rgba(0,217,139,0.06)" stroke-width="1">
        <animate attributeName="stroke-opacity" values="0.06;0.2;0.06" dur="8s" repeatCount="indefinite"/>
      </line>
      <!-- Nodes -->
      <circle cx="80" cy="200" r="4" fill="rgba(26,111,255,0.6)">
        <animate attributeName="r" values="4;6;4" dur="3s" repeatCount="indefinite"/>
      </circle>
      <circle cx="300" cy="420" r="5" fill="rgba(26,111,255,0.7)">
        <animate attributeName="r" values="5;7;5" dur="4s" repeatCount="indefinite"/>
      </circle>
      <circle cx="520" cy="280" r="3.5" fill="rgba(232,160,34,0.6)">
        <animate attributeName="r" values="3.5;5;3.5" dur="5s" repeatCount="indefinite"/>
      </circle>
      <circle cx="180" cy="650" r="3" fill="rgba(0,217,139,0.5)">
        <animate attributeName="r" values="3;5;3" dur="4.5s" repeatCount="indefinite"/>
      </circle>
      <circle cx="450" cy="600" r="4" fill="rgba(26,111,255,0.4)">
        <animate attributeName="r" values="4;6;4" dur="6s" repeatCount="indefinite"/>
      </circle>
      <!-- Travelling pulse -->
      <circle r="3" fill="rgba(26,111,255,0.8)">
        <animateMotion path="M80,200 L300,420 L520,280 L450,600 L180,650 L80,200" dur="10s" repeatCount="indefinite"/>
      </circle>
    </svg>

    <div class="l-inner">
      <!-- Brand -->
      <div class="l-brand">
        <div class="l-brand-mark">
          <svg viewBox="0 0 18 18"><path d="M9 2L2 7v9h5v-5h4v5h5V7z"/></svg>
        </div>
        <div class="l-brand-text">
          <div class="l-brand-name">FX<em>Pulse</em></div>
          <div class="l-brand-sub">Intelligent Trading</div>
        </div>
      </div>

      <!-- Step progress -->
      <div class="l-step">
        <div class="l-step-nodes">
          <div class="l-step-node done">1</div>
          <div class="l-step-line"></div>
          <div class="l-step-node active">2</div>
        </div>
        <span class="l-step-label">Connect your broker</span>
      </div>

      <!-- Headline -->
      <div class="l-headline">
        <div class="l-eyebrow">Brokerage Setup</div>
        <div class="l-title">Link Your MT5<span>Trading Account</span></div>
        <div class="l-desc">Your credentials are AES-256 encrypted before storage and never transmitted to third parties. Your funds stay at your broker — always.</div>
        <div class="l-signal">
          <span class="l-dot"></span>
          AI scanning 28 pairs — London session active
        </div>
      </div>

      <!-- Live prices -->
      <div class="l-prices">
        <div class="l-prices-hdr">
          <span class="l-prices-title">Live Market Data</span>
          <span class="l-prices-live">Live</span>
        </div>
        <div class="l-pair">
          <span class="l-pair-name">AUD/USD</span>
          <div class="l-pair-bar"><div class="l-pair-bar-fill" style="--w:68%;background:var(--green)"></div></div>
          <span class="l-pair-price" id="aud-p">0.6384</span>
          <span class="l-pair-chg chg-up" id="aud-c">+0.41%</span>
        </div>
        <div class="l-pair">
          <span class="l-pair-name">GBP/USD</span>
          <div class="l-pair-bar"><div class="l-pair-bar-fill" style="--w:72%;background:var(--green)"></div></div>
          <span class="l-pair-price">1.2743</span>
          <span class="l-pair-chg chg-up">+0.30%</span>
        </div>
        <div class="l-pair">
          <span class="l-pair-name">EUR/USD</span>
          <div class="l-pair-bar"><div class="l-pair-bar-fill" style="--w:60%;background:var(--green)"></div></div>
          <span class="l-pair-price">1.0812</span>
          <span class="l-pair-chg chg-up">+0.48%</span>
        </div>
        <div class="l-pair">
          <span class="l-pair-name">USD/JPY</span>
          <div class="l-pair-bar"><div class="l-pair-bar-fill" style="--w:35%;background:var(--red)"></div></div>
          <span class="l-pair-price">154.32</span>
          <span class="l-pair-chg chg-dn">−0.09%</span>
        </div>
        <div class="l-pair">
          <span class="l-pair-name">NZD/USD</span>
          <div class="l-pair-bar"><div class="l-pair-bar-fill" style="--w:28%;background:var(--red)"></div></div>
          <span class="l-pair-price">0.5891</span>
          <span class="l-pair-chg chg-dn">−0.52%</span>
        </div>
      </div>

      <!-- Trust -->
      <div class="l-trust">
        <div class="l-trust-item"><div class="l-trust-check">✓</div>AES-256 Encrypted</div>
        <div class="l-trust-item"><div class="l-trust-check">✓</div>ASIC Regulated Brokers</div>
        <div class="l-trust-item"><div class="l-trust-check">✓</div>Disconnect Anytime</div>
      </div>
    </div>
  </div>

  <!-- ═══ RIGHT PANEL ═══ -->
  <div class="right">

  <?php if ($has_account && empty($errors)): ?>
    <!-- MANAGE SCREEN -->
    <div class="f-eyebrow">MT5 Account</div>
    <div class="f-title">Account Connected</div>
    <div class="f-sub">Your trading account is active. Disconnect below to switch brokers or update credentials.</div>

    <?php if ($disconnected): ?>
      <div class="alert alert-info">Account disconnected successfully. Connect a new one below.</div>
    <?php endif; ?>

    <div class="acct-card">
      <div class="acct-row">
        <span class="acct-key">Account</span>
        <span class="acct-val accent">••••<?= htmlspecialchars(substr($existing['mt5_login'], -4)) ?></span>
      </div>
      <div class="acct-row">
        <span class="acct-key">Broker</span>
        <span class="acct-val"><?= htmlspecialchars($existing['broker_server']) ?></span>
      </div>
      <div class="acct-row">
        <span class="acct-key">Account Type</span>
        <span class="acct-val">
          <span class="<?= $existing['account_type'] === 'live' ? 'badge-live' : 'badge-demo' ?>">
            <?= strtoupper($existing['account_type']) ?>
          </span>
        </span>
      </div>
      <div class="acct-row">
        <span class="acct-key">Default Lot</span>
        <span class="acct-val" style="color:var(--green)"><?= htmlspecialchars($existing['lot_size']) ?></span>
      </div>
      <div class="acct-row">
        <span class="acct-key">Connected Since</span>
        <span class="acct-val" style="font-size:12px;color:var(--muted)">
          <?= date('d M Y, H:i', strtotime($existing['connected_at'])) ?> UTC
        </span>
      </div>
    </div>

    <form method="POST" action="connect-mt5.php" onsubmit="return confirm('Disconnect your MT5 account?');">
      <input type="hidden" name="action"     value="disconnect">
      <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrf) ?>">
      <button type="submit" class="btn-danger">Disconnect Account</button>
    </form>
    <a href="dashboard.php" class="back-link">&#8592; Back to dashboard</a>

  <?php else: ?>
    <!-- CONNECT SCREEN -->
    <div class="f-eyebrow">Step 2 of 2</div>
    <div class="f-title">Connect MT5</div>
    <div class="f-sub">Link your MetaTrader 5 account to start automated trading across 28 currency pairs.</div>

    <?php if ($new_user): ?>
      <div class="alert alert-info">&#128075; Welcome to FXPulse! Connect your MT5 broker account below to start monitoring your trades.</div>
    <?php endif; ?>
    <?php if ($disconnected): ?>
      <div class="alert alert-info">Account disconnected. Connect a new one below.</div>
    <?php endif; ?>
    <?php if (!empty($errors)): ?>
      <div class="alert alert-error">
        <ul><?php foreach ($errors as $e): ?><li><?= htmlspecialchars($e) ?></li><?php endforeach; ?></ul>
      </div>
    <?php endif; ?>

    <form method="POST" action="/connect-mt5.php" autocomplete="off">
      <input type="hidden" name="action"     value="connect">
      <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrf) ?>">
      <div style="position:absolute;left:-9999px">
        <input type="text" name="website" tabindex="-1" autocomplete="off">
      </div>

      <div class="field">
        <label>MT5 Account Number</label>
        <input type="text" name="mt5_login"
               placeholder="e.g. 61508353"
               value="<?= htmlspecialchars($_POST['mt5_login'] ?? '') ?>"
               inputmode="numeric" pattern="\d{5,9}" maxlength="9" required>
      </div>

      <div class="field">
        <label>MT5 Password</label>
        <div class="pw-wrap">
          <input type="password" name="mt5_password" id="mt5pw"
                 placeholder="Investor or master password"
                 autocomplete="new-password" required>
          <button type="button" class="pw-eye" id="pw-toggle" aria-label="Toggle password visibility">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
      </div>

      <div class="field">
        <label>Broker / Server</label>
        <div class="sel-wrap">
          <select name="broker_server" required>
            <option value="">— Select your broker —</option>
            <optgroup label="Australia (ASIC)">
              <option <?= ($_POST['broker_server']??'')==='Pepperstone-Demo'   ?'selected':''?>>Pepperstone-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='Pepperstone-Live'   ?'selected':''?>>Pepperstone-Live</option>
              <option <?= ($_POST['broker_server']??'')==='ICMarkets-Demo'     ?'selected':''?>>ICMarkets-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='ICMarkets-Live'     ?'selected':''?>>ICMarkets-Live</option>
              <option <?= ($_POST['broker_server']??'')==='FPMarkets-Demo'     ?'selected':''?>>FPMarkets-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='FPMarkets-Live'     ?'selected':''?>>FPMarkets-Live</option>
              <option <?= ($_POST['broker_server']??'')==='FusionMarkets-Demo' ?'selected':''?>>FusionMarkets-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='Vantage-Demo'       ?'selected':''?>>Vantage-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='Eightcap-Demo'      ?'selected':''?>>Eightcap-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='GOMarkets-Demo'     ?'selected':''?>>GOMarkets-Demo</option>
            </optgroup>
            <optgroup label="Global">
              <option <?= ($_POST['broker_server']??'')==='XMGlobal-Demo'  ?'selected':''?>>XMGlobal-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='AvaTrade-Demo'  ?'selected':''?>>AvaTrade-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='HFM-Demo'       ?'selected':''?>>HFM-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='HFCK-Demo'      ?'selected':''?>>HFCK-Demo</option>
              <option <?= ($_POST['broker_server']??'')==='HFCK-Live'      ?'selected':''?>>HFCK-Live</option>
              <option <?= ($_POST['broker_server']??'')==='Other-MT5'      ?'selected':''?>>Other-MT5</option>
            </optgroup>
          </select>
        </div>
      </div>

      <div class="field">
        <label>Account Type</label>
        <div class="type-group">
          <div class="type-btn <?= ($_POST['account_type']??'demo')==='demo'?'sel-demo':'' ?>"
               onclick="setType(this,'demo')">
            Demo<span class="type-label">Paper trading</span>
          </div>
          <div class="type-btn <?= ($_POST['account_type']??'')==='live'?'sel-live':'' ?>"
               onclick="setType(this,'live')">
            Live<span class="type-label">Real funds</span>
          </div>
        </div>
        <input type="hidden" name="account_type" id="account_type_val"
               value="<?= htmlspecialchars($_POST['account_type'] ?? 'demo') ?>">
      </div>

      <div class="field">
        <label>Default Lot Size</label>
        <div class="lot-group">
          <div class="lot-btn <?= ($_POST['lot_size']??'0.10')==='0.10'?'sel':'' ?>"
               onclick="setLot(this,'0.10')">0.10<span class="lot-lbl">Conservative</span></div>
          <div class="lot-btn <?= ($_POST['lot_size']??'')==='0.20'?'sel':'' ?>"
               onclick="setLot(this,'0.20')">0.20<span class="lot-lbl">Moderate</span></div>
          <div class="lot-btn <?= ($_POST['lot_size']??'')==='0.30'?'sel':'' ?>"
               onclick="setLot(this,'0.30')">0.30<span class="lot-lbl">Aggressive</span></div>
        </div>
        <input type="hidden" name="lot_size" id="lot_size_val"
               value="<?= htmlspecialchars($_POST['lot_size'] ?? '0.10') ?>">
      </div>

      <button type="submit" class="btn-submit">Connect Account &#8594;</button>
    </form>

    <div class="enc-note">
      <div class="enc-lock">&#x1F512;</div>
      AES-256 encrypted &mdash; your password is never stored in plaintext
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px">
      <a href="/dashboard.php" class="back-link" style="margin:0">&#8592; Dashboard</a>
      <a href="/" class="back-link" style="margin:0">&#8962; Home</a>
    </div>
    <div style="margin-top:20px;padding:14px 16px;background:rgba(255,71,87,0.05);border:1px solid rgba(255,71,87,0.15);border-radius:8px;font-size:11px;color:rgba(200,216,237,0.4);line-height:1.65;text-align:center">
      <strong style="color:rgba(255,120,120,0.7)">Risk Disclaimer:</strong> FXPulse is not a financial advisory service. All signals are algorithmic predictions only. Trading forex involves significant risk — you may lose more than your deposit. You trade at your own risk. Past performance does not guarantee future results.
    </div>

  <?php endif; ?>
  </div><!-- /.right -->
</div><!-- /.wrap -->

<script>
// Account type toggle
function setType(el, type) {
  document.querySelectorAll('.type-btn').forEach(function(b){
    b.className = 'type-btn';
  });
  el.className = 'type-btn sel-' + type;
  document.getElementById('account_type_val').value = type;
}

// Lot size toggle
function setLot(el, val) {
  document.querySelectorAll('.lot-btn').forEach(function(b){
    b.className = 'lot-btn';
  });
  el.className = 'lot-btn sel';
  document.getElementById('lot_size_val').value = val;
}

// Password show/hide
(function(){
  var btn = document.getElementById('pw-toggle');
  var inp = document.getElementById('mt5pw');
  if (!btn || !inp) return;
  btn.addEventListener('click', function(){
    var show = inp.type === 'password';
    inp.type = show ? 'text' : 'password';
    btn.innerHTML = show
      ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
      : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  });
})();

// AUD/USD live tick
(function(){
  var base = 0.6384, ref = 0.6361;
  setInterval(function(){
    base += (Math.random() - 0.495) * 0.0003;
    base = parseFloat(Math.max(0.630, Math.min(0.645, base)).toFixed(4));
    var chg = ((base - ref) / ref * 100).toFixed(2);
    var up  = parseFloat(chg) >= 0;
    var p = document.getElementById('aud-p');
    var c = document.getElementById('aud-c');
    if (p) p.textContent = base.toFixed(4);
    if (c) {
      c.textContent  = (up ? '+' : '') + chg + '%';
      c.className    = 'l-pair-chg ' + (up ? 'chg-up' : 'chg-dn');
    }
  }, 1500);
})();
</script>
</body>
</html>

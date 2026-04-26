<?php
require_once __DIR__ . '/includes/config.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/users.php';
require_once __DIR__ . '/includes/tokens.php';
require_once __DIR__ . '/includes/mailer.php';

session_init();
if (is_logged_in()) { header('Location: dashboard.php'); exit; }

$errors  = [];
$success = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username  = trim($_POST['username']  ?? '');
    $email     = trim($_POST['email']     ?? '');
    $full_name = trim($_POST['full_name'] ?? '');
    $password  = $_POST['password']  ?? '';
    $confirm   = $_POST['confirm']   ?? '';

    if (!preg_match('/^[a-zA-Z0-9_]{3,20}$/', $username))
        $errors[] = 'Username must be 3–20 characters (letters, numbers, underscore).';
    elseif (user_exists($username))
        $errors[] = 'That username is already taken.';

    if (!filter_var($email, FILTER_VALIDATE_EMAIL))
        $errors[] = 'Please enter a valid email address.';
    elseif (email_taken($email))
        $errors[] = 'That email address is already registered.';

    if (strlen($full_name) < 2)
        $errors[] = 'Please enter your full name.';

    if (strlen($password) < 8)
        $errors[] = 'Password must be at least 8 characters.';
    elseif ($password !== $confirm)
        $errors[] = 'Passwords do not match.';

    if (empty($errors)) {
        create_user($username, $password, $email, $full_name);
        $token = generate_token('email_confirm', $username, 24);
        mail_confirm_email($email, $full_name, $username, $token);
        $success = true;
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Request Access — FXPulse</title>
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

.wrap{display:flex;min-height:100vh;width:100%}

/* ── LEFT PANEL ── */
.left{
  flex:1.2;position:relative;overflow:hidden;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:44px 48px;background:var(--bg);
}
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
.left-grid{
  position:absolute;inset:0;z-index:1;
  background-image:
    linear-gradient(rgba(26,111,255,0.06) 1px,transparent 1px),
    linear-gradient(90deg,rgba(26,111,255,0.06) 1px,transparent 1px);
  background-size:48px 48px;
  mask-image:radial-gradient(ellipse 90% 90% at 50% 50%,black 0%,transparent 100%);
}
.left-svg{position:absolute;inset:0;z-index:2;pointer-events:none;opacity:0.55}
.l-inner{position:relative;z-index:3;display:flex;flex-direction:column;height:100%;gap:0}

.l-brand{display:flex;align-items:center;gap:10px}
.l-brand-mark{
  width:32px;height:32px;border-radius:8px;
  background:linear-gradient(135deg,var(--blue) 0%,#0047cc 100%);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 16px rgba(26,111,255,0.35);flex-shrink:0;
}
.l-brand-mark svg{width:18px;height:18px;fill:#fff}
.l-brand-text{display:flex;flex-direction:column}
.l-brand-name{font-size:18px;font-weight:700;color:#fff;letter-spacing:-0.3px;line-height:1}
.l-brand-name em{color:var(--blue);font-style:normal}
.l-brand-sub{font-size:9px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);margin-top:3px}

.l-headline{margin-top:auto;padding-top:52px}
.l-eyebrow{
  font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--blue);
  opacity:0.8;margin-bottom:14px;display:flex;align-items:center;gap:8px;
}
.l-eyebrow::before{content:'';width:20px;height:1px;background:var(--blue);opacity:0.6}
.l-title{font-size:clamp(26px,3vw,36px);font-weight:700;line-height:1.1;color:#fff;letter-spacing:-0.5px}
.l-title span{color:var(--blue);display:block}
.l-desc{margin-top:14px;font-size:13px;line-height:1.75;color:var(--muted);max-width:320px;font-weight:300}

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

.l-prices{
  margin-top:32px;background:rgba(255,255,255,0.025);
  border:1px solid var(--border);border-radius:12px;overflow:hidden;
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
  padding:9px 16px;border-bottom:1px solid rgba(255,255,255,0.025);transition:background 0.15s;
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

.l-trust{margin-top:24px;display:flex;gap:20px;flex-wrap:wrap}
.l-trust-item{display:flex;align-items:center;gap:7px;font-size:11px;color:var(--faint);font-weight:400}
.l-trust-check{
  width:16px;height:16px;border-radius:4px;flex-shrink:0;
  background:rgba(232,160,34,0.12);border:1px solid rgba(232,160,34,0.3);
  display:flex;align-items:center;justify-content:center;font-size:9px;color:var(--gold);
}

/* ── RIGHT PANEL ── */
.right{
  width:480px;flex-shrink:0;
  background:var(--panel);border-left:1px solid var(--border);
  display:flex;flex-direction:column;justify-content:center;
  padding:52px 44px;overflow-y:auto;position:relative;
}
.right::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--blue-glow),transparent);opacity:0.6;
}

.f-eyebrow{font-size:9px;letter-spacing:3.5px;text-transform:uppercase;color:var(--blue);opacity:0.85;margin-bottom:8px}
.f-title{font-size:26px;font-weight:700;color:#fff;line-height:1.15;letter-spacing:-0.4px}
.f-sub{font-size:13px;color:var(--muted);margin-top:8px;line-height:1.65;margin-bottom:28px;font-weight:300}

.alert{border-radius:10px;padding:12px 16px;margin-bottom:20px;font-size:13px;line-height:1.6}
.alert-error{background:rgba(255,71,87,0.07);border:1px solid rgba(255,71,87,0.25);color:#ff8a99}
.alert-success{background:rgba(0,217,139,0.07);border:1px solid rgba(0,217,139,0.25);color:#4de8b0}
.alert ul{padding-left:16px}.alert li{margin-bottom:3px}

.field{position:relative;margin-bottom:16px}
.field label{display:block;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:8px;font-weight:500}
.field input{
  width:100%;background:rgba(255,255,255,0.04);border:1px solid var(--border);
  border-radius:10px;padding:13px 16px;color:#fff;
  font-family:'Sora',sans-serif;font-size:14px;font-weight:400;
  outline:none;transition:border-color 0.2s,background 0.2s,box-shadow 0.2s;
}
.field input::placeholder{color:rgba(200,216,237,0.2)}
.field input:focus{
  border-color:rgba(26,111,255,0.6);background:rgba(26,111,255,0.04);
  box-shadow:0 0 0 3px rgba(26,111,255,0.08);
}
.field .hint{display:block;font-size:11px;color:var(--muted);margin-top:5px;line-height:1.4}

.pw-wrap{position:relative}
.pw-wrap input{padding-right:44px}
.pw-eye{
  position:absolute;right:14px;top:50%;transform:translateY(-50%);
  background:none;border:none;cursor:pointer;color:var(--muted);padding:0;
  transition:color 0.2s;line-height:1;
}
.pw-eye:hover{color:var(--blue)}

.btn-submit{
  width:100%;margin-top:8px;padding:15px;border:none;border-radius:10px;cursor:pointer;
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
  background:linear-gradient(135deg,rgba(255,255,255,0.1) 0%,transparent 50%);pointer-events:none;
}

.f-footer{margin-top:20px;text-align:center;font-size:12px;color:var(--faint)}
.f-footer a{color:var(--blue);text-decoration:none;transition:color 0.2s}
.f-footer a:hover{color:#5a9fff}

@media(max-width:960px){
  .left{display:none}
  .wrap{justify-content:center}
  .right{width:100%;max-width:520px;margin:0 auto;padding:52px 24px;border-left:none;justify-content:flex-start;padding-top:60px}
}
</style>
</head>
<body>
<div class="wrap">

  <!-- ═══ LEFT PANEL ═══ -->
  <div class="left">
    <div class="left-bg"></div>
    <div class="left-grid"></div>

    <svg class="left-svg" viewBox="0 0 600 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="ng" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#1a6fff" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#1a6fff" stop-opacity="0"/>
        </radialGradient>
      </defs>
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
      <circle r="3" fill="rgba(26,111,255,0.8)">
        <animateMotion path="M80,200 L300,420 L520,280 L450,600 L180,650 L80,200" dur="10s" repeatCount="indefinite"/>
      </circle>
    </svg>

    <div class="l-inner">
      <div class="l-brand">
        <div class="l-brand-mark">
          <svg viewBox="0 0 18 18"><path d="M9 2L2 7v9h5v-5h4v5h5V7z"/></svg>
        </div>
        <div class="l-brand-text">
          <div class="l-brand-name">FX<em>Pulse</em></div>
          <div class="l-brand-sub">Intelligent Trading</div>
        </div>
      </div>

      <div class="l-headline">
        <div class="l-eyebrow">Join FXPulse</div>
        <div class="l-title">Get Access to<span>AI-Driven Signals</span></div>
        <div class="l-desc">XGBoost + LSTM models scan 28 currency pairs 24/7. Connect your MT5 broker and let the AI trade for you — fully automated.</div>
        <div class="l-signal">
          <span class="l-dot"></span>
          AI scanning 28 pairs — London session active
        </div>
      </div>

      <div class="l-prices">
        <div class="l-prices-hdr">
          <span class="l-prices-title">Live Market Data</span>
          <span class="l-prices-live">Live</span>
        </div>
        <div class="l-pair">
          <span class="l-pair-name">AUD/USD</span>
          <div class="l-pair-bar"><div class="l-pair-bar-fill" style="--w:68%;background:var(--green)"></div></div>
          <span class="l-pair-price">0.6384</span>
          <span class="l-pair-chg chg-up">+0.41%</span>
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

      <div class="l-trust">
        <div class="l-trust-item"><div class="l-trust-check">✓</div>Free to Join</div>
        <div class="l-trust-item"><div class="l-trust-check">✓</div>ASIC Regulated Brokers</div>
        <div class="l-trust-item"><div class="l-trust-check">✓</div>Approved Within 5 Min</div>
      </div>
    </div>
  </div>

  <!-- ═══ RIGHT PANEL ═══ -->
  <div class="right">

    <?php if ($success): ?>
      <div class="f-eyebrow">One More Step</div>
      <div class="f-title">Check your inbox</div>
      <div class="f-sub">We've sent a confirmation link to <strong style="color:#fff"><?= htmlspecialchars($_POST['email'] ?? '') ?></strong>. Click it to activate your account.</div>
      <div class="alert alert-success">
        &#10003; <strong>Account created!</strong><br><br>
        Confirm your email to unlock access. The link expires in 24 hours. Check spam if you don't see it.
      </div>
      <p class="f-footer">Already confirmed? <a href="login.php">Sign in</a></p>

    <?php else: ?>
      <div class="f-eyebrow">Step 1 of 2</div>
      <div class="f-title">Request Access</div>
      <div class="f-sub">Create your account. An admin will review and approve your request within 5 minutes.</div>

      <?php if ($errors): ?>
        <div class="alert alert-error">
          <ul><?php foreach ($errors as $e): ?><li><?= htmlspecialchars($e) ?></li><?php endforeach; ?></ul>
        </div>
      <?php endif; ?>

      <form method="POST" action="" novalidate>
        <div class="field">
          <label>Full Name</label>
          <input type="text" name="full_name" placeholder="John Smith"
                 value="<?= htmlspecialchars($_POST['full_name'] ?? '') ?>" required>
        </div>
        <div class="field">
          <label>Username</label>
          <input type="text" name="username" placeholder="johnsmith"
                 value="<?= htmlspecialchars($_POST['username'] ?? '') ?>"
                 autocomplete="username" required>
          <span class="hint">Letters, numbers, underscore · 3–20 characters</span>
        </div>
        <div class="field">
          <label>Email Address</label>
          <input type="email" name="email" placeholder="john@example.com"
                 value="<?= htmlspecialchars($_POST['email'] ?? '') ?>" required>
        </div>
        <div class="field">
          <label>Password</label>
          <div class="pw-wrap">
            <input type="password" name="password" id="pw1"
                   placeholder="Minimum 8 characters"
                   autocomplete="new-password" required>
            <button type="button" class="pw-eye" onclick="togglePw('pw1')" aria-label="Show password">
              <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
        </div>
        <div class="field">
          <label>Confirm Password</label>
          <div class="pw-wrap">
            <input type="password" name="confirm" id="pw2"
                   placeholder="Repeat your password"
                   autocomplete="new-password" required>
            <button type="button" class="pw-eye" onclick="togglePw('pw2')" aria-label="Show password">
              <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
        </div>
        <button type="submit" class="btn-submit">Submit Request &rarr;</button>
      </form>

      <p class="f-footer">Already approved? <a href="login.php">Sign in</a></p>
    <?php endif; ?>
  </div>
</div>
<script>
function togglePw(id) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
}
</script>
</body>
</html>

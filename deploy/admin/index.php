<?php
require_once __DIR__ . '/../includes/config.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/users.php';

session_init();
require_admin('../login.php');

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'], $_POST['username'])) {
    $uname  = $_POST['username'];
    $action = $_POST['action'];
    if ($uname === 'admin') { }
    elseif ($action === 'approve') approve_user($uname);
    elseif ($action === 'reject')  reject_user($uname);
    elseif ($action === 'delete')  delete_user($uname);
    header('Location: index.php?done=1');
    exit;
}

$pending  = get_users_by_status(STATUS_PENDING);
$approved = get_users_by_status(STATUS_APPROVED);
$rejected = get_users_by_status(STATUS_REJECTED);
$u = current_user();
$total = count($pending) + count($approved) + count($rejected);
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FXPulse — Admin Panel</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#03070e;--card:#080f1a;--border:#0f1e32;--border2:#172840;--accent:#00c8ff;--accent2:#00ff88;--gold:#ffc107;--danger:#ff3a5c;--text:#dce8f8;--muted:#4a6280;--muted2:#2a3d5a;--ff:'Syne',sans-serif;--fm:'JetBrains Mono',monospace}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--ff);min-height:100vh}
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(0,200,255,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(0,200,255,.018) 1px,transparent 1px);background-size:52px 52px}
header{position:sticky;top:0;z-index:100;background:rgba(3,7,14,.92);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
.hdr{display:flex;align-items:center;justify-content:space-between;padding:14px 32px;max-width:1200px;margin:0 auto}
.logo{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:800;color:var(--text);text-decoration:none}
.logo-box{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:#000;font-family:var(--fm)}
.hdr-links{display:flex;align-items:center;gap:8px}
.hdr-link{color:var(--muted);font-size:13px;padding:7px 14px;border-radius:8px;text-decoration:none;transition:.2s;border:1px solid transparent}
.hdr-link:hover{color:var(--accent);border-color:rgba(0,200,255,.2)}
.hdr-link.active{color:var(--accent);background:rgba(0,200,255,.08);border-color:rgba(0,200,255,.2)}
.btn-so{color:var(--muted);font-size:13px;padding:7px 14px;border-radius:8px;text-decoration:none;border:1px solid var(--border2);transition:.2s}
.btn-so:hover{border-color:var(--danger);color:var(--danger)}
.main{max-width:1200px;margin:0 auto;padding:32px 32px 60px;position:relative;z-index:1}
.page-tag{font-family:var(--fm);font-size:10px;color:var(--accent);letter-spacing:3px;text-transform:uppercase;margin-bottom:10px}
.page-title{font-size:32px;font-weight:800;letter-spacing:-1px;margin-bottom:6px}
.page-sub{font-size:14px;color:var(--muted);margin-bottom:32px}
.alert-ok{padding:12px 20px;background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.2);border-radius:10px;color:var(--accent2);font-family:var(--fm);font-size:13px;margin-bottom:24px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:32px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px 20px;text-align:center;transition:.2s}
.stat:hover{border-color:var(--border2)}
.stat-n{font-family:var(--fm);font-size:36px;font-weight:700;display:block;line-height:1;margin-bottom:8px}
.stat-l{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:2px}
.n-gold{color:var(--gold)}.n-green{color:var(--accent2)}.n-red{color:var(--danger)}.n-blue{color:var(--accent)}
.panel{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:20px}
.panel-hdr{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;border-bottom:1px solid var(--border)}
.panel-title{font-family:var(--fm);font-size:10px;color:var(--accent);letter-spacing:2.5px;text-transform:uppercase}
.panel-badge{font-family:var(--fm);font-size:10px;padding:3px 10px;border-radius:10px;background:rgba(0,200,255,.1);border:1px solid rgba(0,200,255,.2);color:var(--accent)}
.panel-badge.gold{background:rgba(255,193,7,.1);border-color:rgba(255,193,7,.2);color:var(--gold)}
.panel-badge.green{background:rgba(0,255,136,.1);border-color:rgba(0,255,136,.2);color:var(--accent2)}
.panel-badge.red{background:rgba(255,58,92,.1);border-color:rgba(255,58,92,.2);color:var(--danger)}
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
thead th{padding:12px 18px;text-align:left;font-family:var(--fm);font-size:9px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid var(--border);background:rgba(0,0,0,.2)}
tbody td{padding:14px 18px;border-bottom:1px solid rgba(15,30,50,.6);color:var(--muted);vertical-align:middle}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:rgba(0,200,255,.02)}
td strong{color:var(--text)}
td.mono{font-family:var(--fm);font-size:12px}
.badge{display:inline-block;padding:3px 10px;border-radius:8px;font-family:var(--fm);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.badge-admin{background:rgba(0,200,255,.15);color:var(--accent);border:1px solid rgba(0,200,255,.2)}
.badge-viewer{background:rgba(74,98,128,.15);color:var(--muted);border:1px solid rgba(74,98,128,.2)}
.ac{display:flex;gap:6px;align-items:center}
.btn{padding:6px 14px;border-radius:7px;font-size:11px;font-weight:700;font-family:var(--ff);cursor:pointer;border:none;transition:.2s;text-transform:uppercase;letter-spacing:.5px}
.btn-a{background:rgba(0,255,136,.15);color:var(--accent2);border:1px solid rgba(0,255,136,.25)}
.btn-a:hover{background:rgba(0,255,136,.25)}
.btn-r{background:rgba(255,193,7,.15);color:var(--gold);border:1px solid rgba(255,193,7,.25)}
.btn-r:hover{background:rgba(255,193,7,.25)}
.btn-d{background:rgba(255,58,92,.12);color:var(--danger);border:1px solid rgba(255,58,92,.2)}
.btn-d:hover{background:rgba(255,58,92,.22)}
.protected{font-family:var(--fm);font-size:11px;color:var(--muted2);padding:4px 8px}
.empty{text-align:center;padding:40px;font-family:var(--fm);font-size:13px;color:var(--muted)}
footer{border-top:1px solid var(--border);padding:20px 32px;text-align:center;font-family:var(--fm);font-size:11px;color:var(--muted2);position:relative;z-index:1}
</style>
</head>
<body>
<header>
  <div class="hdr">
    <a href="../index.php" class="logo"><div class="logo-box">FX</div>FXPulse</a>
    <div class="hdr-links">
      <a href="../dashboard.php" class="hdr-link">Dashboard</a>
      <a href="index.php" class="hdr-link active">Admin</a>
      <a href="../logout.php" class="btn-so">Sign Out</a>
    </div>
  </div>
</header>
<div class="main">
  <div class="page-tag">⚙ System Administration</div>
  <div class="page-title">Admin Panel</div>
  <div class="page-sub">Manage user accounts, approve access requests, monitor platform activity.</div>
  <?php if (isset($_GET['done'])): ?><div class="alert-ok">✅ Action completed successfully.</div><?php endif; ?>
  <div class="stats">
    <div class="stat"><span class="stat-n n-gold"><?= count($pending) ?></span><span class="stat-l">Pending</span></div>
    <div class="stat"><span class="stat-n n-green"><?= count($approved) ?></span><span class="stat-l">Approved</span></div>
    <div class="stat"><span class="stat-n n-red"><?= count($rejected) ?></span><span class="stat-l">Rejected</span></div>
    <div class="stat"><span class="stat-n n-blue"><?= $total ?></span><span class="stat-l">Total Users</span></div>
  </div>
  <?php if (!empty($pending)): ?>
  <div class="panel">
    <div class="panel-hdr"><span class="panel-title">⏳ Pending Approvals</span><span class="panel-badge gold"><?= count($pending) ?> waiting</span></div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Username</th><th>Full Name</th><th>Email</th><th>Registered</th><th>Actions</th></tr></thead>
      <tbody>
      <?php foreach ($pending as $ud): ?>
      <tr>
        <td><strong><?= htmlspecialchars($ud['username']) ?></strong></td>
        <td><?= htmlspecialchars($ud['full_name']) ?></td>
        <td class="mono"><?= htmlspecialchars($ud['email']) ?></td>
        <td class="mono"><?= date('M j, Y', strtotime($ud['created_at'])) ?></td>
        <td><div class="ac">
          <form method="POST" style="display:inline"><input type="hidden" name="username" value="<?= htmlspecialchars($ud['username']) ?>"><input type="hidden" name="action" value="approve"><button type="submit" class="btn btn-a">Approve</button></form>
          <form method="POST" style="display:inline" onsubmit="return confirm('Reject?')"><input type="hidden" name="username" value="<?= htmlspecialchars($ud['username']) ?>"><input type="hidden" name="action" value="reject"><button type="submit" class="btn btn-r">Reject</button></form>
        </div></td>
      </tr>
      <?php endforeach; ?>
      </tbody>
    </table></div>
  </div>
  <?php endif; ?>
  <div class="panel">
    <div class="panel-hdr"><span class="panel-title">✅ Approved Users</span><span class="panel-badge green"><?= count($approved) ?> active</span></div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Username</th><th>Full Name</th><th>Email</th><th>Role</th><th>Approved</th><th>Last Login</th><th>Actions</th></tr></thead>
      <tbody>
      <?php foreach ($approved as $ud): ?>
      <tr>
        <td><strong><?= htmlspecialchars($ud['username']) ?></strong></td>
        <td><?= htmlspecialchars($ud['full_name']) ?></td>
        <td class="mono"><?= htmlspecialchars($ud['email']) ?></td>
        <td><span class="badge <?= $ud['role'] === ROLE_ADMIN ? 'badge-admin' : 'badge-viewer' ?>"><?= $ud['role'] ?></span></td>
        <td class="mono"><?= $ud['approved_at'] ? date('M j, Y', strtotime($ud['approved_at'])) : '—' ?></td>
        <td class="mono"><?= $ud['last_login'] ? date('M j H:i', strtotime($ud['last_login'])) : 'Never' ?></td>
        <td><?php if ($ud['username'] !== 'admin'): ?><div class="ac"><form method="POST" style="display:inline" onsubmit="return confirm('Delete user?')"><input type="hidden" name="username" value="<?= htmlspecialchars($ud['username']) ?>"><input type="hidden" name="action" value="delete"><button type="submit" class="btn btn-d">Delete</button></form></div><?php else: ?><span class="protected">🔒 Protected</span><?php endif; ?></td>
      </tr>
      <?php endforeach; ?>
      <?php if (empty($approved)): ?><tr><td colspan="7"><div class="empty">No approved users</div></td></tr><?php endif; ?>
      </tbody>
    </table></div>
  </div>
  <?php if (!empty($rejected)): ?>
  <div class="panel">
    <div class="panel-hdr"><span class="panel-title">❌ Rejected Users</span><span class="panel-badge red"><?= count($rejected) ?></span></div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Username</th><th>Email</th><th>Registered</th><th>Actions</th></tr></thead>
      <tbody>
      <?php foreach ($rejected as $ud): ?>
      <tr>
        <td><strong><?= htmlspecialchars($ud['username']) ?></strong></td>
        <td class="mono"><?= htmlspecialchars($ud['email']) ?></td>
        <td class="mono"><?= date('M j, Y', strtotime($ud['created_at'])) ?></td>
        <td><div class="ac">
          <form method="POST" style="display:inline"><input type="hidden" name="username" value="<?= htmlspecialchars($ud['username']) ?>"><input type="hidden" name="action" value="approve"><button type="submit" class="btn btn-a">Approve</button></form>
          <form method="POST" style="display:inline" onsubmit="return confirm('Delete?')"><input type="hidden" name="username" value="<?= htmlspecialchars($ud['username']) ?>"><input type="hidden" name="action" value="delete"><button type="submit" class="btn btn-d">Delete</button></form>
        </div></td>
      </tr>
      <?php endforeach; ?>
      </tbody>
    </table></div>
  </div>
  <?php endif; ?>
</div>
<footer>FXPulse v<?= APP_VERSION ?> · Admin Panel · Authorized Access Only</footer>
</body>
</html>

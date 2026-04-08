<?php
require_once __DIR__ . '/../includes/config.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/users.php';
require_once __DIR__ . '/../includes/layout.php';

session_init();
require_admin('../login.php');

// Handle actions
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'], $_POST['username'])) {
    $uname  = $_POST['username'];
    $action = $_POST['action'];
    if ($uname === 'admin') { /* never touch admin account */ }
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

html_head('Admin Panel');
nav($u);
?>
<main class="main-wrap">
  <div class="page-header">
    <h1>Admin Panel</h1>
    <p class="page-sub">Manage user accounts and access requests.</p>
  </div>

  <?php if (isset($_GET['done'])): ?>
    <div class="alert alert-success" style="margin-bottom:20px">&#10003; Action completed.</div>
  <?php endif; ?>

  <!-- Stats row -->
  <div class="stats-row">
    <div class="stat-box">
      <span class="stat-n yellow"><?= count($pending) ?></span>
      <span class="stat-l">Pending</span>
    </div>
    <div class="stat-box">
      <span class="stat-n green"><?= count($approved) ?></span>
      <span class="stat-l">Approved</span>
    </div>
    <div class="stat-box">
      <span class="stat-n red"><?= count($rejected) ?></span>
      <span class="stat-l">Rejected</span>
    </div>
    <div class="stat-box">
      <span class="stat-n"><?= count($pending) + count($approved) + count($rejected) ?></span>
      <span class="stat-l">Total Users</span>
    </div>
  </div>

  <!-- Pending Approvals -->
  <?php if (!empty($pending)): ?>
  <div class="card" style="margin-bottom:20px">
    <h3 class="card-title yellow-text">&#9201; Pending Approvals (<?= count($pending) ?>)</h3>
    <div class="table-wrap">
    <table>
      <thead><tr><th>Username</th><th>Full Name</th><th>Email</th><th>Registered</th><th>Actions</th></tr></thead>
      <tbody>
      <?php foreach ($pending as $u_data): ?>
        <tr>
          <td><strong><?= htmlspecialchars($u_data['username']) ?></strong></td>
          <td><?= htmlspecialchars($u_data['full_name']) ?></td>
          <td><?= htmlspecialchars($u_data['email']) ?></td>
          <td><?= date('M j, Y', strtotime($u_data['created_at'])) ?></td>
          <td class="action-cell">
            <form method="POST" style="display:inline">
              <input type="hidden" name="username" value="<?= htmlspecialchars($u_data['username']) ?>">
              <input type="hidden" name="action" value="approve">
              <button type="submit" class="btn-sm btn-green">Approve</button>
            </form>
            <form method="POST" style="display:inline" onsubmit="return confirm('Reject this user?')">
              <input type="hidden" name="username" value="<?= htmlspecialchars($u_data['username']) ?>">
              <input type="hidden" name="action" value="reject">
              <button type="submit" class="btn-sm btn-red">Reject</button>
            </form>
          </td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
    </div>
  </div>
  <?php endif; ?>

  <!-- Approved Users -->
  <div class="card" style="margin-bottom:20px">
    <h3 class="card-title green-text">&#10003; Approved Users (<?= count($approved) ?>)</h3>
    <div class="table-wrap">
    <table>
      <thead><tr><th>Username</th><th>Full Name</th><th>Email</th><th>Role</th><th>Approved</th><th>Last Login</th><th>Actions</th></tr></thead>
      <tbody>
      <?php foreach ($approved as $u_data): ?>
        <tr>
          <td><strong><?= htmlspecialchars($u_data['username']) ?></strong></td>
          <td><?= htmlspecialchars($u_data['full_name']) ?></td>
          <td><?= htmlspecialchars($u_data['email']) ?></td>
          <td><span class="badge <?= $u_data['role'] === ROLE_ADMIN ? 'badge-blue' : 'badge-gray' ?>"><?= $u_data['role'] ?></span></td>
          <td><?= $u_data['approved_at'] ? date('M j, Y', strtotime($u_data['approved_at'])) : '—' ?></td>
          <td><?= $u_data['last_login'] ? date('M j H:i', strtotime($u_data['last_login'])) : 'Never' ?></td>
          <td class="action-cell">
            <?php if ($u_data['username'] !== 'admin'): ?>
            <form method="POST" style="display:inline" onsubmit="return confirm('Delete this user?')">
              <input type="hidden" name="username" value="<?= htmlspecialchars($u_data['username']) ?>">
              <input type="hidden" name="action" value="delete">
              <button type="submit" class="btn-sm btn-red">Delete</button>
            </form>
            <?php else: ?>
            <span class="muted">Protected</span>
            <?php endif; ?>
          </td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
    </div>
  </div>

  <!-- Rejected -->
  <?php if (!empty($rejected)): ?>
  <div class="card">
    <h3 class="card-title red-text">&#10005; Rejected Users (<?= count($rejected) ?>)</h3>
    <div class="table-wrap">
    <table>
      <thead><tr><th>Username</th><th>Email</th><th>Registered</th><th>Actions</th></tr></thead>
      <tbody>
      <?php foreach ($rejected as $u_data): ?>
        <tr>
          <td><?= htmlspecialchars($u_data['username']) ?></td>
          <td><?= htmlspecialchars($u_data['email']) ?></td>
          <td><?= date('M j, Y', strtotime($u_data['created_at'])) ?></td>
          <td class="action-cell">
            <form method="POST" style="display:inline">
              <input type="hidden" name="username" value="<?= htmlspecialchars($u_data['username']) ?>">
              <input type="hidden" name="action" value="approve">
              <button type="submit" class="btn-sm btn-green">Approve</button>
            </form>
            <form method="POST" style="display:inline" onsubmit="return confirm('Permanently delete?')">
              <input type="hidden" name="username" value="<?= htmlspecialchars($u_data['username']) ?>">
              <input type="hidden" name="action" value="delete">
              <button type="submit" class="btn-sm btn-red">Delete</button>
            </form>
          </td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
    </div>
  </div>
  <?php endif; ?>
</main>
<?php html_foot(); ?>

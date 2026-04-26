# FXPulse Regression Log

---

## REGRESSION 001 — Homepage Bloomberg Terminal Lost
**Date discovered:** 2026-04-15  
**Severity:** HIGH — public landing page degraded  
**Status:** FIXED

### What broke
`deploy/index.php` reverted from the 1237-line Bloomberg Terminal + live ticker redesign back to the 936-line plain version that had no scrolling ticker and no Bloomberg terminal widget.

### Root cause
Changes were staged in `git stash@{0}` ("WIP on main: b72b617") and never committed. A subsequent session started from `HEAD` instead of applying the stash first, so all Bloomberg terminal work was silently abandoned. The stash itself was not deleted, but it was never checked.

### What was lost
- `<!-- LIVE TICKER -->` — scrolling marquee with 10 FX pairs at top of page
- `<!-- FXPulse Bloomberg Terminal Widget -->` — animated terminal card with live prices, currency strength bars, dual-feed price ticker with auto-scroll
- CSS sections: `.ticker`, `.bloomberg-terminal`, `.bb-wrap`, `.bb-panel`, `.tick-item`
- JavaScript: `buildTicker()`, `genPrices()`, `clock()` functions
- Approx 300 lines total

### Fix applied
`git show stash@{0}:deploy/index.php > deploy/index.php`  
File is now 1237 lines. Bloomberg terminal and live ticker confirmed present.

### How to prevent
See PM WATCHDOG RULES below.

---

## REGRESSION 002 — MT5 Individual Accounts Not Scoped Per User (Bethwel Bug)
**Date discovered:** 2026-04-15  
**Severity:** CRITICAL — users could see wrong account data  
**Status:** FIXED

### What broke
When any user (example: Bethwel) navigated to `connect-mt5.php`, the system was unable to correctly store or retrieve their individual MT5 account. Bethwel saw the admin's MT5 account instead of his own.

### Root cause
`deploy/includes/mt5_accounts.php` uses two PHP constants:
- `MT5_ACCOUNTS_FILE` — path to the per-user accounts JSON
- `ENCRYPT_SECRET` — key for AES-256-CBC MT5 password encryption

**Neither constant was defined in `deploy/includes/config.php`.**

On PHP 8, referencing an undefined constant is a Fatal Error, crashing the page.  
On PHP 7.x, it evaluates to the string `"MT5_ACCOUNTS_FILE"`, causing `file_exists()` to look for a file named literally "MT5_ACCOUNTS_FILE" in the working directory — this file never existed.

Result: `load_mt5_accounts()` always returned `[]`, `get_mt5_account($username)` always returned `null`, and `has_active_mt5_account()` always returned `false`. No per-user accounts could be stored or retrieved.

### Fix applied
Added to `deploy/includes/config.php`:
```php
define('MT5_ACCOUNTS_FILE', DATA_DIR . 'mt5_accounts.json');
define('ENCRYPT_SECRET',    'fxpulse-mt5-enc-v1-changeme-on-server');
```

**IMPORTANT on server:** The `ENCRYPT_SECRET` value in config.php is a placeholder. On SiteGround the real secret must be set. If the secret changes, all previously encrypted MT5 passwords become unreadable — users must reconnect their MT5 accounts.

### How account scoping works (correct behaviour)
- `mt5_accounts.json` is a flat JSON object keyed by username
- `create_mt5_account($username, ...)` writes to `$all[$username]`
- `get_mt5_account($username)` reads `$all[$username]`
- `$username` always comes from `$_SESSION['user']` via `current_user()`
- Sessions are server-side PHP sessions with httponly + Strict SameSite cookies
- There is NO shared account fallback — if a user has no account, they see the connection form

### How to prevent
See PM WATCHDOG RULES below.

---

## PM WATCHDOG RULES — MANDATORY BEFORE EVERY DEPLOY

The PM agent MUST run ALL of these checks before declaring any deploy approved.  
Failure on any check = block deploy, write escalation brief, trigger builder fix.

### CHECK 1 — Homepage line count
```bash
wc -l deploy/index.php
```
**MUST be ≥ 1200 lines.** If < 1200 → Bloomberg terminal was lost → BLOCK.

### CHECK 2 — Bloomberg terminal present
```bash
grep -c "bloomberg\|BLOOMBERG\|ticker\|TICKER" deploy/index.php
```
**MUST return ≥ 8 matches.** If < 8 → terminal stripped → BLOCK.

### CHECK 3 — MT5_ACCOUNTS_FILE defined
```bash
grep "MT5_ACCOUNTS_FILE" deploy/includes/config.php
```
**MUST return a define() line.** If empty → constant missing → BLOCK.

### CHECK 4 — ENCRYPT_SECRET defined
```bash
grep "ENCRYPT_SECRET" deploy/includes/config.php
```
**MUST return a define() line.** If empty → encryption broken → BLOCK.

### CHECK 5 — Per-user account scoping intact
```bash
grep "get_mt5_account(\$username)" deploy/connect-mt5.php
grep "has_active_mt5_account(\$username)" deploy/connect-mt5.php
```
**MUST match on \$username (not a hardcoded value).** If empty or hardcoded → account leak → BLOCK.

### CHECK 6 — Stash is empty before deploy
```bash
git stash list
```
**MUST be empty.** If any stash exists → there is unsaved work → POP AND REVIEW before deploying.

### CHECK 7 — Page file sizes
```bash
wc -l deploy/index.php deploy/login.php deploy/register.php deploy/connect-mt5.php
```
Expected minimums:
- `index.php`       ≥ 1200
- `login.php`       ≥ 380
- `register.php`    ≥ 440
- `connect-mt5.php` ≥ 750

If any page is below its minimum → design was reverted → BLOCK.

---

## AGENT ROLES — UPDATED

### Builder Agent
- Builds/modifies PHP pages as requested
- **MUST commit changes immediately after building** — do not leave work in working tree or stash
- **MUST NOT use git stash** as a save mechanism — commit or abandon

### PM Agent (fxpulse-deploy skill)
- Runs ALL 7 checks above before every deploy
- If any check fails → write escalation brief → send to Builder → do NOT deploy
- Owns the REGRESSION_LOG.md — adds new entries when regressions are found
- Alerts on stash presence before every session start — not just before deploy
- **Never approves without running actual bash commands** — visual inspection is not a check

### Deploy Agent
- Only deploys AFTER PM approval with written evidence of all 7 checks passing
- Uses paramiko SFTP to SiteGround (never git reset/pull on server)
- Deploys only `deploy/` folder — never touches bot Python files

### Bot files — NEVER touch
`main.py`, `siteground_api.py`, `config.py`, `*.py` in project root  
These are live bot files. Touching them crashes trading.

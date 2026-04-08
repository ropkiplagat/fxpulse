"""
Security Module — protects MT5 credentials and API keys.
Encrypts credentials using Fernet (AES-128-CBC) so they are never stored as plain text.

Usage:
  python security.py --setup    (first time — encrypts your credentials)
  python security.py --verify   (test decryption works)

The bot then loads decrypted credentials at startup instead of reading plain text.
"""
import os
import sys
import json
import getpass
import base64

CREDS_FILE = ".credentials.enc"
KEY_FILE   = ".secret.key"


def _get_fernet():
    try:
        from cryptography.fernet import Fernet
        return Fernet
    except ImportError:
        print("[SEC] Install: pip install cryptography")
        sys.exit(1)


def generate_key() -> bytes:
    """Generate and save an encryption key."""
    Fernet = _get_fernet()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    os.chmod(KEY_FILE, 0o600)  # Owner read-only
    print(f"[SEC] Key saved to {KEY_FILE} — keep this file safe, don't share it.")
    return key


def load_key() -> bytes:
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError(f"Key file {KEY_FILE} not found. Run: python security.py --setup")
    with open(KEY_FILE, "rb") as f:
        return f.read()


def encrypt_credentials(creds: dict) -> None:
    """Encrypt and save credentials dict to disk."""
    Fernet = _get_fernet()
    key    = load_key() if os.path.exists(KEY_FILE) else generate_key()
    f      = Fernet(key)
    token  = f.encrypt(json.dumps(creds).encode())
    with open(CREDS_FILE, "wb") as cf:
        cf.write(token)
    os.chmod(CREDS_FILE, 0o600)
    print(f"[SEC] Credentials encrypted and saved to {CREDS_FILE}")


def load_credentials() -> dict:
    """Decrypt and return credentials dict."""
    if not os.path.exists(CREDS_FILE):
        return {}
    Fernet = _get_fernet()
    key    = load_key()
    f      = Fernet(key)
    with open(CREDS_FILE, "rb") as cf:
        token = cf.read()
    return json.loads(f.decrypt(token).decode())


def setup_credentials():
    """Interactive setup — prompts user for credentials and encrypts them."""
    print("\n=== Forex AI Bot — Secure Credential Setup ===")
    print("Credentials will be encrypted. Never stored as plain text.\n")

    if not os.path.exists(KEY_FILE):
        generate_key()

    creds = {
        "MT5_LOGIN":          input("MT5 Account Number: ").strip(),
        "MT5_PASSWORD":       getpass.getpass("MT5 Password: "),
        "MT5_SERVER":         input("MT5 Server (e.g. Pepperstone-Demo): ").strip(),
        "TELEGRAM_TOKEN":     input("Telegram Token (leave blank to skip): ").strip(),
        "TELEGRAM_CHAT_ID":   input("Telegram Chat ID (leave blank to skip): ").strip(),
        "SITEGROUND_API_URL": input("SiteGround URL (leave blank to skip): ").strip(),
        "SITEGROUND_API_KEY": input("SiteGround API Key (leave blank to skip): ").strip(),
    }

    encrypt_credentials(creds)
    print("\n[SEC] Setup complete. Delete any plain text passwords from config.py now.")
    print(f"[SEC] Files created: {KEY_FILE} (key) + {CREDS_FILE} (encrypted creds)")
    print("[SEC] Add both files to .gitignore — never commit them.")


def apply_to_config():
    """
    Load encrypted credentials and override config module values.
    Call this at the top of main.py BEFORE connecting to MT5.
    """
    creds = load_credentials()
    if not creds:
        return  # No encrypted creds — use plain config.py values

    import config
    for key, value in creds.items():
        if value and hasattr(config, key):
            setattr(config, key, int(value) if key == "MT5_LOGIN" else value)

    print("[SEC] Credentials loaded from encrypted store.")


def ensure_gitignore():
    """Add security files to .gitignore."""
    entries = [".credentials.enc", ".secret.key", "logs/", "models/", "__pycache__/", "*.pyc"]
    gitignore = ".gitignore"
    existing = set()
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            existing = {line.strip() for line in f}

    new_entries = [e for e in entries if e not in existing]
    if new_entries:
        with open(gitignore, "a") as f:
            f.write("\n# Forex AI Bot — sensitive files\n")
            for e in new_entries:
                f.write(e + "\n")
        print(f"[SEC] Added {len(new_entries)} entries to .gitignore")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--setup" in args:
        setup_credentials()
        ensure_gitignore()
    elif "--verify" in args:
        creds = load_credentials()
        if creds:
            safe = {k: ("*" * 6 if "pass" in k.lower() or "token" in k.lower() else v)
                    for k, v in creds.items()}
            print("[SEC] Decryption successful:")
            for k, v in safe.items():
                print(f"  {k}: {v}")
        else:
            print("[SEC] No encrypted credentials found. Run: python security.py --setup")
    else:
        print("Usage: python security.py --setup | --verify")

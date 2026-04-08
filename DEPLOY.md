# Deployment Guide — Forex AI Bot

## Option A: Run on Your PC (Free — for testing)

Just run:
```bash
python main.py --train
```

**Limitation:** Your PC must stay on 24/7 during London + NY sessions (7am-9pm UTC).

---

## Option B: Windows VPS (Recommended for live trading)

MT5 requires Windows. Use a Windows VPS near your broker's servers.

### Recommended VPS Providers (cheapest → most reliable)

| Provider | Price/mo | Location | Best For |
|----------|----------|----------|----------|
| **Vultr** (High Frequency) | ~$12 | NY, London, Singapore | Best value |
| **VPSForexTrader** | ~$30 | NY4 Equinix | Lowest latency to brokers |
| **ForexVPS.net** | ~$35 | NY4/LD4 | Purpose-built for MT5 |
| **Serverspace** | ~$15 | Global | Budget option |

### Setup Steps (Vultr example)

1. **Create Windows Server 2022 VPS** at vultr.com
   - Plan: 2 vCPU, 4GB RAM ($24/mo) — sufficient
   - Location: New York (closest to Pepperstone NY servers)

2. **Connect via RDP** (Remote Desktop)
   - Windows: Start → Remote Desktop Connection → paste VPS IP

3. **Install on the VPS:**
   ```
   a. Download MT5 from Pepperstone website
   b. Download Python 3.11 from python.org (add to PATH)
   c. Copy your forex-bot folder via RDP or GitHub
   ```

4. **Install Python packages:**
   ```cmd
   cd C:\forex-bot
   pip install -r requirements.txt
   ```

5. **Configure MT5 on VPS:**
   - Log in to your Pepperstone demo account in MT5
   - Keep MT5 running (don't close it)

6. **Run the bot:**
   ```cmd
   python main.py --train
   ```

7. **Keep running after RDP disconnect** (use one of):
   ```cmd
   # Option 1: Windows Task Scheduler (recommended)
   # Option 2: Create a .bat file and run as Windows Service
   # Option 3: NSSM (Non-Sucking Service Manager)
   ```

### Auto-start with Task Scheduler

1. Open Task Scheduler → Create Basic Task
2. Trigger: At startup
3. Action: Start a program → `python` → Arguments: `C:\forex-bot\main.py`
4. Check "Run whether user is logged in or not"

---

## Option C: Run Web Dashboard Alongside Bot

On the VPS, open two terminals:

**Terminal 1:**
```cmd
python main.py
```

**Terminal 2:**
```cmd
python web_app.py
```

Access dashboard from your phone/laptop:
```
http://YOUR_VPS_IP:5000
```

To expose securely, add a firewall rule on Vultr:
- Allow TCP port 5000 from your IP only

---

## Option D: Local + Telegram Only (No VPS needed)

If you don't want to pay for VPS:
1. Set up Telegram alerts in config.py
2. Run bot on your PC during London/NY sessions only
3. Monitor via Telegram on your phone

```python
# In config.py:
TELEGRAM_TOKEN   = "your_bot_token_from_BotFather"
TELEGRAM_CHAT_ID = "your_chat_id"
```

---

## Telegram Bot Setup (5 minutes)

1. Message **@BotFather** on Telegram → `/newbot`
2. Copy the token it gives you → paste into `config.py`
3. Message **@userinfobot** → it tells you your chat ID
4. Paste chat ID into `config.py`
5. Bot will now send you alerts for every trade

---

## Running Commands Reference

```bash
# First run (trains AI model)
python main.py --train

# Normal run (model already trained)
python main.py

# Backtest strategy on historical data
python main.py --backtest

# Web dashboard only
python web_app.py
```

---

## Minimum System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| OS | Windows 10/Server 2019 | Windows Server 2022 |
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB (for LSTM) |
| Disk | 10 GB | 20 GB |
| Internet | 10 Mbps | 50 Mbps stable |

---

## What's Running at All Times

```
MT5 Terminal (Pepperstone)  — must be logged in
Python main.py              — trading bot
Python web_app.py           — dashboard (optional)
```

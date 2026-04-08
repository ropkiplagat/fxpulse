# Forex AI Bot — Setup Guide

## 1. Install Python Dependencies

```bash
cd C:\Users\HP\forex-bot
pip install -r requirements.txt
```

## 2. Configure Your Pepperstone Account

Edit `config.py` and fill in your MT5 demo account details:

```python
MT5_LOGIN    = 12345678        # Your account number
MT5_PASSWORD = "yourpassword"  # Your password
MT5_SERVER   = "Pepperstone-Demo"  # Check exact name in MT5 login screen
```

To find your server name: open MT5 → File → Login → check the "Server" dropdown.

## 3. Create Required Folders

```bash
mkdir C:\Users\HP\forex-bot\models
mkdir C:\Users\HP\forex-bot\logs
```

## 4. First Run — Train the AI Model

```bash
python main.py --train
```

This will:
- Connect to your MT5 account
- Pull 500 bars of historical data per symbol
- Train XGBoost on ~3,000-10,000 trade samples
- Save the model to `models/xgb_forex.pkl`
- Start the live trading loop

## 5. Regular Run (after model is trained)

```bash
python main.py
```

## 6. What the Bot Does

Every 60 seconds it:
1. Calculates currency strength (USD, EUR, GBP, JPY, AUD, NZD, CAD, CHF) from M15 + H1
2. Ranks pairs by strongest-vs-weakest gap
3. Checks Renko pullback setup on top 3 pairs
4. Runs AI predictor (XGBoost) — only trades if win probability >= 65%
5. Places order with risk-based lot size (1% account risk per trade)
6. Manages open trades: partial close at 1R, break-even at 1R, Renko trailing stop

## 7. Dashboard Controls

While running:
- `T` — Force immediate scan
- `R` — Retrain AI model now
- `Q` — Quit safely

## 8. Risk Warning

**Always run on DEMO account first.**
Test for at least 2-4 weeks before considering live trading.
Past performance does not guarantee future results.

## 9. File Structure

```
forex-bot/
├── main.py              # Entry point
├── config.py            # All settings — edit this
├── mt5_connector.py     # MT5 connection + order execution
├── currency_strength.py # Strength engine (M15 + H1)
├── renko.py             # Renko simulation from M1 data
├── signals.py           # Signal confluence scoring
├── ai_predictor.py      # XGBoost win probability model
├── trade_manager.py     # Lot sizing, SL/TP, BE, trailing
├── dashboard.py         # Terminal display
├── performance_log.py   # Trade outcome tracking
├── models/              # Trained model files (auto-created)
└── logs/                # Trade + signal logs (auto-created)
```

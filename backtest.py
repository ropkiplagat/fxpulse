"""
Walk-Forward Backtester — tests the full strategy on historical data.
Generates: win rate, profit factor, max drawdown, Sharpe ratio.
Run: python backtest.py
"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timezone
import mt5_connector as mt5c
import config

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 not installed.")
    sys.exit(1)


def simulate_trade(df: pd.DataFrame, entry_idx: int, direction: str,
                   sl_dist: float, tp_dist: float) -> dict:
    """Simulate a trade outcome from historical bars."""
    entry_price = df["close"].iloc[entry_idx]

    if direction == "buy":
        sl_price = entry_price - sl_dist
        tp_price = entry_price + tp_dist
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - tp_dist

    # Walk forward bar-by-bar
    for i in range(entry_idx + 1, min(entry_idx + 100, len(df))):
        h = df["high"].iloc[i]
        l = df["low"].iloc[i]

        if direction == "buy":
            if l <= sl_price:
                return {"outcome": "loss", "r": -1.0, "bars": i - entry_idx}
            if h >= tp_price:
                return {"outcome": "win",  "r": config.TP_R_MULTIPLE, "bars": i - entry_idx}
        else:
            if h >= sl_price:
                return {"outcome": "loss", "r": -1.0, "bars": i - entry_idx}
            if l <= tp_price:
                return {"outcome": "win",  "r": config.TP_R_MULTIPLE, "bars": i - entry_idx}

    return {"outcome": "timeout", "r": 0.0, "bars": 100}


def run_backtest(symbols: list = None, bars: int = 1000):
    """Run full strategy backtest on historical data."""
    from ta.trend import EMAIndicator, MACD, ADXIndicator
    from ta.momentum import RSIIndicator
    from ta.volatility import AverageTrueRange

    if symbols is None:
        symbols = config.MAJOR_CURRENCIES + config.MINOR_CURRENCIES

    print("=" * 60)
    print("  FOREX AI BOT — WALK-FORWARD BACKTEST")
    print("=" * 60)

    mt5c.connect()
    available = mt5c.get_available_symbols()

    all_trades = []

    for symbol in symbols:
        if symbol not in available:
            continue

        df = mt5c.get_bars(symbol, config.TF_FAST, count=bars)
        if df is None or len(df) < 200:
            print(f"  {symbol}: insufficient data, skipping.")
            continue

        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        ema20 = EMAIndicator(close, 20).ema_indicator()
        ema50 = EMAIndicator(close, 50).ema_indicator()
        rsi   = RSIIndicator(close, 14).rsi()
        macd_hist = MACD(close, 26, 12, 9).macd_diff()
        atr   = AverageTrueRange(high, low, close, 14).average_true_range()
        adx   = ADXIndicator(high, low, close, 14).adx()

        sym_trades = 0
        sym_wins   = 0

        for i in range(60, len(df) - 100):
            # Only trade in trending regime
            if adx.iloc[i] < 20:
                continue

            # Determine direction
            if ema20.iloc[i] > ema50.iloc[i] and macd_hist.iloc[i] > 0:
                direction = "buy"
            elif ema20.iloc[i] < ema50.iloc[i] and macd_hist.iloc[i] < 0:
                direction = "sell"
            else:
                continue

            # RSI filter
            if direction == "buy" and rsi.iloc[i] > 70:
                continue
            if direction == "sell" and rsi.iloc[i] < 30:
                continue

            sl_dist = atr.iloc[i] * 2
            tp_dist = sl_dist * config.TP_R_MULTIPLE

            result = simulate_trade(df, i, direction, sl_dist, tp_dist)

            if result["outcome"] != "timeout":
                all_trades.append({
                    "symbol":    symbol,
                    "direction": direction,
                    "outcome":   result["outcome"],
                    "r":         result["r"],
                    "bars":      result["bars"],
                    "idx":       i,
                })
                sym_trades += 1
                if result["outcome"] == "win":
                    sym_wins += 1

            # Avoid over-sampling (skip 5 bars after each signal)
            i += 5

        if sym_trades > 0:
            wr = sym_wins / sym_trades
            print(f"  {symbol:12s}: {sym_trades:4d} trades | WR: {wr:.1%}")

    mt5c.disconnect()

    if not all_trades:
        print("No trades generated.")
        return

    # === Summary Statistics ===
    df_trades = pd.DataFrame(all_trades)
    wins   = df_trades[df_trades["outcome"] == "win"]
    losses = df_trades[df_trades["outcome"] == "loss"]

    total       = len(df_trades)
    win_count   = len(wins)
    loss_count  = len(losses)
    win_rate    = win_count / total if total > 0 else 0

    gross_profit = wins["r"].sum()
    gross_loss   = abs(losses["r"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Equity curve (1% risk per trade)
    equity   = [1000.0]
    for _, row in df_trades.iterrows():
        risk_amt = equity[-1] * (config.RISK_PERCENT / 100)
        equity.append(equity[-1] + risk_amt * row["r"])

    equity_arr  = np.array(equity)
    peak        = np.maximum.accumulate(equity_arr)
    drawdown    = (peak - equity_arr) / peak * 100
    max_dd      = drawdown.max()

    # Sharpe ratio (annualized, assuming 1 trade = 1 bar = 15 min)
    returns     = np.diff(equity_arr) / equity_arr[:-1]
    sharpe      = (returns.mean() / returns.std()) * np.sqrt(252 * 26) if returns.std() > 0 else 0

    print("\n" + "=" * 60)
    print("  BACKTEST RESULTS")
    print("=" * 60)
    print(f"  Total Trades:    {total}")
    print(f"  Win Rate:        {win_rate:.1%}")
    print(f"  Profit Factor:   {profit_factor:.2f}")
    print(f"  Max Drawdown:    {max_dd:.1f}%")
    print(f"  Sharpe Ratio:    {sharpe:.2f}")
    print(f"  Final Equity:    ${equity[-1]:.2f} (from $1,000)")
    print(f"  Return:          {(equity[-1]/1000 - 1)*100:.1f}%")
    print("=" * 60)

    # Save results
    os.makedirs("logs", exist_ok=True)
    df_trades.to_csv("logs/backtest_trades.csv", index=False)
    print("  Trades saved to logs/backtest_trades.csv")

    return {
        "total": total, "win_rate": win_rate,
        "profit_factor": profit_factor, "max_drawdown": max_dd,
        "sharpe": sharpe, "final_equity": equity[-1],
    }


if __name__ == "__main__":
    run_backtest()

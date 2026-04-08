"""
Kelly Criterion Position Sizer — from trading-signals skill risk-management.md

Replaces flat 1% risk with mathematically optimal sizing.
Uses Half Kelly (safer) with regime-based adjustment.

Rules from ThetaRoom v2:
- max_per_trade_risk: 2%
- max_portfolio_risk: 15%
- Regime multipliers: 1.0x trending, 0.75x volatile, 0.5x distribution, 0x crisis
- Drawdown escalation: 3% review, 5% reduce 50%, 8% halt
"""
import mt5_connector as mt5c
import config

# Regime-based position size multipliers
REGIME_MULTIPLIERS = {
    "trending_up":   1.0,
    "trending_down": 1.0,
    "ranging":       0.0,   # Don't trade
    "volatile":      0.5,
    "crisis":        0.0,   # Don't trade
}

# Drawdown-based size reduction
DRAWDOWN_LADDER = [
    (0.08, 0.0),   # 8%+ drawdown → halt
    (0.05, 0.5),   # 5%+ → reduce to 50%
    (0.03, 0.75),  # 3%+ → reduce to 75%
    (0.0,  1.0),   # normal → full size
]

# Max portfolio risk budget (sum of all open positions)
MAX_PORTFOLIO_RISK_PCT = 0.15
MAX_PER_TRADE_RISK_PCT = 0.02  # Hard cap regardless of Kelly


def half_kelly_fraction(win_prob: float, avg_win_r: float, avg_loss_r: float) -> float:
    """
    Calculate Half Kelly fraction of account to risk per trade.

    win_prob: probability of winning (e.g. 0.65)
    avg_win_r: average win in R multiples (e.g. 2.0 for 2R target)
    avg_loss_r: average loss in R multiples (e.g. 1.0 for 1R stop)
    """
    if avg_win_r <= 0 or avg_loss_r <= 0:
        return 0.01

    kelly = (win_prob * avg_win_r - (1 - win_prob) * avg_loss_r) / avg_win_r
    half_kelly = kelly * 0.5

    # Cap at max per-trade risk
    return max(0.005, min(half_kelly, MAX_PER_TRADE_RISK_PCT))


def get_drawdown_multiplier() -> tuple[float, str]:
    """
    Check current drawdown and return (size_multiplier, status).
    Implements the escalation ladder from risk-management.md.
    """
    account = mt5c.get_account_info()
    if not account:
        return 1.0, "normal"

    balance = account.balance
    equity  = account.equity

    if balance <= 0:
        return 1.0, "normal"

    drawdown_pct = (balance - equity) / balance

    for threshold, multiplier in DRAWDOWN_LADDER:
        if drawdown_pct >= threshold:
            if multiplier == 0.0:
                return 0.0, "halt"
            elif multiplier < 1.0:
                return multiplier, f"drawdown_{int(drawdown_pct*100)}pct"
            else:
                return 1.0, "normal"

    return 1.0, "normal"


def get_portfolio_risk_used() -> float:
    """
    Calculate what % of account is currently at risk in open positions.
    """
    account   = mt5c.get_account_info()
    positions = mt5c.get_open_positions()

    if not account or not positions:
        return 0.0

    total_risk = 0.0
    for pos in positions:
        if pos.sl == 0:
            continue
        risk_per_trade = abs(pos.price_open - pos.sl) * pos.volume
        info = mt5c.get_symbol_info(pos.symbol)
        if info:
            risk_per_trade *= info.trade_contract_size
        total_risk += risk_per_trade

    return total_risk / account.balance if account.balance > 0 else 0.0


def calculate_kelly_lot(symbol: str, sl_distance: float,
                        win_prob: float, regime: str) -> tuple[float, dict]:
    """
    Full Kelly-based lot calculation with all safety gates.

    Returns (lot_size, sizing_info_dict).
    Returns (0.0, info) if trade should be blocked.
    """
    account = mt5c.get_account_info()
    info    = mt5c.get_symbol_info(symbol)

    if not account or not info or sl_distance <= 0:
        return 0.01, {"method": "fallback", "blocked": False}

    sizing_info = {}

    # 1. Drawdown gate
    dd_multiplier, dd_status = get_drawdown_multiplier()
    sizing_info["drawdown_status"] = dd_status
    sizing_info["dd_multiplier"]   = dd_multiplier

    if dd_multiplier == 0.0:
        return 0.0, {**sizing_info, "blocked": True, "reason": "drawdown_halt"}

    # 2. Portfolio risk gate
    portfolio_risk = get_portfolio_risk_used()
    sizing_info["portfolio_risk_used"] = round(portfolio_risk, 4)

    if portfolio_risk >= MAX_PORTFOLIO_RISK_PCT:
        return 0.0, {**sizing_info, "blocked": True, "reason": "portfolio_risk_full"}

    # 3. Regime multiplier
    regime_mult = REGIME_MULTIPLIERS.get(regime, 0.5)
    sizing_info["regime_multiplier"] = regime_mult

    if regime_mult == 0.0:
        return 0.0, {**sizing_info, "blocked": True, "reason": f"regime_{regime}"}

    # 4. Kelly fraction
    kelly_frac = half_kelly_fraction(
        win_prob,
        avg_win_r=config.TP_R_MULTIPLE,
        avg_loss_r=1.0
    )
    sizing_info["kelly_fraction"] = round(kelly_frac, 4)

    # 5. Apply all multipliers
    adjusted_frac = kelly_frac * dd_multiplier * regime_mult

    # Cap remaining portfolio budget
    remaining_budget = MAX_PORTFOLIO_RISK_PCT - portfolio_risk
    adjusted_frac    = min(adjusted_frac, remaining_budget)
    adjusted_frac    = min(adjusted_frac, MAX_PER_TRADE_RISK_PCT)

    # 6. Convert fraction to lot size
    risk_amount = account.balance * adjusted_frac

    # Pip value calculation
    point  = info.point
    digits = info.digits
    pip_size = point * 10 if digits in (3, 5) else point
    sl_pips  = sl_distance / pip_size

    tick_value = info.trade_tick_value
    tick_size  = info.trade_tick_size
    pip_val_per_lot = (pip_size / tick_size) * tick_value if tick_size > 0 else 0.01

    if pip_val_per_lot <= 0 or sl_pips <= 0:
        return 0.01, {**sizing_info, "blocked": False, "method": "fallback"}

    lot = risk_amount / (sl_pips * pip_val_per_lot)

    # Round to broker step
    step = info.volume_step or 0.01
    lot  = max(info.volume_min, min(info.volume_max, round(lot / step) * step))

    sizing_info.update({
        "blocked":     False,
        "method":      "half_kelly",
        "risk_amount": round(risk_amount, 2),
        "risk_pct":    round(adjusted_frac * 100, 3),
        "sl_pips":     round(sl_pips, 1),
        "lot":         round(lot, 2),
    })

    return round(lot, 2), sizing_info

"""
AI Predictor — XGBoost model that predicts win probability for each trade setup.
Only trades when P(win) >= MIN_WIN_PROBABILITY (default 65%).

Training data: historical MT5 bars → generate features → label outcomes.
"""
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
import config

FEATURE_COLUMNS = [
    "direction", "strength_gap",
    "rsi_m15", "ema_slope_m15", "macd_hist_m15", "bb_pct_m15", "atr_m15", "ema_aligned_m15",
    "rsi_h1",  "ema_slope_h1",  "macd_hist_h1",  "bb_pct_h1",  "ema_aligned_h1",
    "renko_valid", "renko_trigger", "renko_in_pullback", "renko_pullback_n",
    "in_overlap", "confluence",
]


class AIPredictor:
    def __init__(self):
        self.model  = None
        self.scaler = None
        self._load()

    def _load(self):
        """Load pre-trained model if exists."""
        if os.path.exists(config.MODEL_PATH) and os.path.exists(config.SCALER_PATH):
            with open(config.MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(config.SCALER_PATH, "rb") as f:
                self.scaler = pickle.load(f)
            print(f"[AI] Model loaded from {config.MODEL_PATH}")
        else:
            print("[AI] No pre-trained model found. Will use rule-based scoring until trained.")

    def predict(self, features: dict) -> float:
        """
        Return win probability 0.0-1.0.
        Falls back to confluence score if model not trained.
        """
        if self.model is None or self.scaler is None:
            # Fallback: use confluence score directly
            return features.get("confluence", 0.0)

        try:
            X = pd.DataFrame([{col: features.get(col, 0) for col in FEATURE_COLUMNS}])
            X_scaled = self.scaler.transform(X)
            prob = self.model.predict_proba(X_scaled)[0][1]
            return round(float(prob), 4)
        except Exception as e:
            print(f"[AI] Prediction error: {e}")
            return features.get("confluence", 0.0)

    def is_tradeable(self, features: dict) -> tuple[bool, float]:
        """Returns (should_trade, win_probability)."""
        prob = self.predict(features)
        return prob >= config.MIN_WIN_PROBABILITY, prob

    def save(self):
        """Save current model to disk."""
        os.makedirs(os.path.dirname(config.MODEL_PATH), exist_ok=True)
        with open(config.MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(config.SCALER_PATH, "wb") as f:
            pickle.dump(self.scaler, f)
        print(f"[AI] Model saved to {config.MODEL_PATH}")


def generate_training_data(symbols: list, available_symbols: set) -> pd.DataFrame:
    """
    Generate labeled training data from historical MT5 data.
    Label: 1 if trade would have been profitable at 2R TP, 0 otherwise.
    """
    import mt5_connector as mt5c
    from ta.trend import EMAIndicator, MACD
    from ta.momentum import RSIIndicator
    from ta.volatility import BollingerBands, AverageTrueRange

    all_rows = []

    for symbol in symbols:
        if symbol not in available_symbols:
            continue

        df = mt5c.get_bars(symbol, config.TF_FAST, count=500)
        if df is None or len(df) < 150:
            continue

        close = df["close"]
        high  = df["high"]
        low   = df["low"]

        # Compute indicators
        ema20 = EMAIndicator(close, window=20).ema_indicator()
        ema50 = EMAIndicator(close, window=50).ema_indicator()
        rsi   = RSIIndicator(close, window=14).rsi()
        macd_obj  = MACD(close, window_slow=26, window_fast=12, window_sign=9)
        macd_hist = macd_obj.macd_diff()
        bb    = BollingerBands(close, window=20, window_dev=2)
        bb_pct = bb.bollinger_pband()
        atr   = AverageTrueRange(high, low, close, window=14).average_true_range()

        # Generate sample rows from history
        for i in range(60, len(df) - 30):
            direction = 1 if ema20.iloc[i] > ema50.iloc[i] else 0
            entry_price = close.iloc[i]
            sl_dist = atr.iloc[i] * 2
            tp_dist = sl_dist * config.TP_R_MULTIPLE

            if direction == 1:  # Buy
                sl = entry_price - sl_dist
                tp = entry_price + tp_dist
                future_closes = close.iloc[i+1:i+30].values
                hit_tp = any(c >= tp for c in future_closes)
                hit_sl = any(c <= sl for c in future_closes)
            else:  # Sell
                sl = entry_price + sl_dist
                tp = entry_price - tp_dist
                future_closes = close.iloc[i+1:i+30].values
                hit_tp = any(c <= tp for c in future_closes)
                hit_sl = any(c >= sl for c in future_closes)

            # Label: 1 if TP hit before SL
            if hit_tp and not hit_sl:
                label = 1
            elif hit_sl:
                label = 0
            else:
                continue  # Skip inconclusive

            ema_slope = (ema20.iloc[i] - ema20.iloc[i-5]) / ema20.iloc[i-5] * 100
            ema_aligned = 1 if (direction == 1 and ema20.iloc[i] > ema50.iloc[i]) or \
                               (direction == 0 and ema20.iloc[i] < ema50.iloc[i]) else 0

            row = {
                "direction":         direction,
                "strength_gap":      1.5,  # Placeholder — will be real in live
                "rsi_m15":           rsi.iloc[i],
                "ema_slope_m15":     ema_slope,
                "macd_hist_m15":     macd_hist.iloc[i],
                "bb_pct_m15":        bb_pct.iloc[i],
                "atr_m15":           atr.iloc[i],
                "ema_aligned_m15":   ema_aligned,
                "rsi_h1":            rsi.iloc[i],  # Simplified for training
                "ema_slope_h1":      ema_slope,
                "macd_hist_h1":      macd_hist.iloc[i],
                "bb_pct_h1":         bb_pct.iloc[i],
                "ema_aligned_h1":    ema_aligned,
                "renko_valid":       1,
                "renko_trigger":     1 if abs(macd_hist.iloc[i]) > abs(macd_hist.iloc[i-1]) else 0,
                "renko_in_pullback": 0,
                "renko_pullback_n":  2,
                "in_overlap":        1,
                "confluence":        min(0.6 + abs(ema_slope) * 2, 1.0),
                "label":             label,
            }
            all_rows.append(row)

    return pd.DataFrame(all_rows)


def train_model(symbols: list, available_symbols: set) -> AIPredictor:
    """
    Train XGBoost on historical data and return fitted predictor.
    """
    try:
        from xgboost import XGBClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report, accuracy_score
    except ImportError:
        print("[AI] Install: pip install xgboost scikit-learn")
        return AIPredictor()

    print("[AI] Generating training data...")
    df = generate_training_data(symbols, available_symbols)

    if len(df) < 100:
        print(f"[AI] Not enough training samples ({len(df)}). Need 100+.")
        return AIPredictor()

    X = df[FEATURE_COLUMNS].fillna(0)
    y = df["label"]

    print(f"[AI] Training on {len(df)} samples | Win rate: {y.mean():.1%}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        scale_pos_weight=(y == 0).sum() / (y == 1).sum(),  # Handle imbalance
    )
    model.fit(X_train_s, y_train,
              eval_set=[(X_test_s, y_test)],
              verbose=False)

    preds = model.predict(X_test_s)
    acc   = accuracy_score(y_test, preds)
    print(f"[AI] Model accuracy: {acc:.1%}")
    print(classification_report(y_test, preds, target_names=["Loss", "Win"]))

    predictor = AIPredictor.__new__(AIPredictor)
    predictor.model  = model
    predictor.scaler = scaler
    predictor.save()

    return predictor

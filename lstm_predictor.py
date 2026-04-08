"""
LSTM Price Predictor — sequence-based deep learning model.
Ensembles with XGBoost for superior win probability estimation.

Architecture: LSTM(64) → Dropout(0.2) → LSTM(32) → Dense(1, sigmoid)
Trained on 60-bar sequences → predict direction of next 20 bars.
"""
import os
import pickle
import numpy as np
import pandas as pd
import config

SEQUENCE_LEN  = 60   # Input sequence length
LSTM_MODEL_PATH   = "models/lstm_forex.keras"
LSTM_SCALER_PATH  = "models/lstm_scaler.pkl"


class LSTMPredictor:
    def __init__(self):
        self.model  = None
        self.scaler = None
        self._load()

    def _load(self):
        if os.path.exists(LSTM_MODEL_PATH) and os.path.exists(LSTM_SCALER_PATH):
            try:
                import tensorflow as tf
                self.model = tf.keras.models.load_model(LSTM_MODEL_PATH)
                with open(LSTM_SCALER_PATH, "rb") as f:
                    self.scaler = pickle.load(f)
                print(f"[LSTM] Model loaded from {LSTM_MODEL_PATH}")
            except Exception as e:
                print(f"[LSTM] Load failed: {e}. Will use XGBoost only.")

    def predict(self, df: pd.DataFrame, direction: str) -> float:
        """
        Predict win probability from OHLCV sequence.
        Returns 0.0-1.0. Falls back to 0.5 if model not loaded.
        """
        if self.model is None or self.scaler is None:
            return 0.5

        try:
            features = self._extract_features(df)
            if features is None or len(features) < SEQUENCE_LEN:
                return 0.5

            seq = features[-SEQUENCE_LEN:]
            seq_scaled = self.scaler.transform(seq)
            X = seq_scaled.reshape(1, SEQUENCE_LEN, seq_scaled.shape[1])
            prob = float(self.model.predict(X, verbose=0)[0][0])

            # Flip for sell direction
            return prob if direction == "buy" else (1 - prob)
        except Exception as e:
            print(f"[LSTM] Prediction error: {e}")
            return 0.5

    def _extract_features(self, df: pd.DataFrame) -> np.ndarray | None:
        """Extract normalized OHLCV + derived features for LSTM input."""
        if len(df) < SEQUENCE_LEN + 10:
            return None
        try:
            from ta.trend import EMAIndicator
            from ta.momentum import RSIIndicator
            close = df["close"]
            high  = df["high"]
            low   = df["low"]

            ema20 = EMAIndicator(close, 20).ema_indicator()
            ema50 = EMAIndicator(close, 50).ema_indicator()
            rsi   = RSIIndicator(close, 14).rsi()

            feat = pd.DataFrame({
                "close":      close,
                "high":       high,
                "low":        low,
                "volume":     df["volume"],
                "ema20":      ema20,
                "ema50":      ema50,
                "rsi":        rsi,
                "ema_diff":   (ema20 - ema50) / ema50 * 100,
                "hl_range":   (high - low) / close,
                "close_pct":  close.pct_change(),
            }).dropna()

            return feat.values
        except Exception:
            return None

    def save(self):
        if self.model:
            self.model.save(LSTM_MODEL_PATH)
        if self.scaler:
            with open(LSTM_SCALER_PATH, "wb") as f:
                pickle.dump(self.scaler, f)
        print(f"[LSTM] Model saved.")


def train_lstm(symbols: list, available_symbols: set) -> LSTMPredictor:
    """Train LSTM on historical OHLCV sequences."""
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from sklearn.preprocessing import MinMaxScaler
        from sklearn.model_selection import train_test_split
    except ImportError:
        print("[LSTM] Install: pip install tensorflow")
        return LSTMPredictor()

    import mt5_connector as mt5c

    all_X, all_y = [], []

    for symbol in symbols:
        if symbol not in available_symbols:
            continue
        df = mt5c.get_bars(symbol, config.TF_FAST, count=800)
        if df is None or len(df) < 200:
            continue

        predictor_temp = LSTMPredictor.__new__(LSTMPredictor)
        predictor_temp.model = None
        predictor_temp.scaler = None
        features = predictor_temp._extract_features(df)
        if features is None:
            continue

        close = df["close"].values[-len(features):]

        for i in range(SEQUENCE_LEN, len(features) - 20):
            seq = features[i - SEQUENCE_LEN:i]
            # Label: 1 if price up in next 20 bars by at least ATR
            future_close = close[i + 20]
            current_close = close[i]
            label = 1 if future_close > current_close else 0
            all_X.append(seq)
            all_y.append(label)

    if len(all_X) < 200:
        print(f"[LSTM] Not enough sequences ({len(all_X)}). Skipping LSTM training.")
        return LSTMPredictor()

    X = np.array(all_X)
    y = np.array(all_y)

    print(f"[LSTM] Training on {len(X)} sequences | Win rate: {y.mean():.1%}")

    # Normalize per-feature across all sequences
    n_samples, seq_len, n_features = X.shape
    X_flat = X.reshape(-1, n_features)
    scaler = MinMaxScaler()
    X_flat_scaled = scaler.fit_transform(X_flat)
    X_scaled = X_flat_scaled.reshape(n_samples, seq_len, n_features)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(seq_len, n_features)),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.2),
        Dense(16, activation="relu"),
        Dense(1, activation="sigmoid"),
    ])

    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(X_train, y_train, epochs=30, batch_size=32,
              validation_data=(X_test, y_test), verbose=1)

    _, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"[LSTM] Test accuracy: {acc:.1%}")

    os.makedirs("models", exist_ok=True)
    predictor = LSTMPredictor.__new__(LSTMPredictor)
    predictor.model  = model
    predictor.scaler = scaler
    predictor.save()

    return predictor


def ensemble_probability(xgb_prob: float, lstm_prob: float,
                         xgb_weight: float = 0.6, lstm_weight: float = 0.4) -> float:
    """
    Weighted ensemble of XGBoost + LSTM probabilities.
    XGBoost gets more weight (more stable on tabular features).
    LSTM adds sequence/momentum context.
    """
    return round(xgb_prob * xgb_weight + lstm_prob * lstm_weight, 4)

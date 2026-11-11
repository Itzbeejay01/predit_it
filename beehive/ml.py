"""Experimental ML direction estimator with chronological, purged holdout tests.

Probability is a model estimate, not a calibrated success rate or trading edge.
Never make demo execution contingent on an unvalidated accuracy percentage.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ResearchResult:
    probability_up: float
    holdout_accuracy: float
    holdout_brier: float
    baseline_brier: float
    test_samples: int
    label: str = "experimental / uncalibrated"


def feature_frame(df):
    c = df["close"].astype(float)
    ret = c.pct_change()
    ema20 = c.ewm(span=20, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    tr = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - c.shift(1)).abs(),
        (df["low"] - c.shift(1)).abs()
    ], axis=1).max(axis=1)
    return pd.DataFrame({
        "ret1": ret,
        "ret4": c.pct_change(4),
        "ret12": c.pct_change(12),
        "vol12": ret.rolling(12).std(),
        "vol36": ret.rolling(36).std(),
        "ema_gap": (ema20 - ema50) / c,
        "ema20_gap": (c - ema20) / c,
        "atr_norm": tr.ewm(alpha=1/14, adjust=False).mean() / c,
        "range_norm": (df["high"] - df["low"]) / c,
    }).replace([np.inf, -np.inf], np.nan)


def research(df, horizon=4):
    """Next-horizon direction research, NOT actual SL/TP trading performance."""
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, brier_score_loss
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for ML research.") from exc
    if horizon < 1:
        raise ValueError("horizon must be positive.")
    feats = feature_frame(df)
    forward = df["close"].shift(-horizon) - df["close"]
    # Drop the last horizon rows (their future outcomes are not known).
    valid = feats.notna().all(axis=1) & forward.notna()
    x = feats.loc[valid]
    y = (forward.loc[valid] > 0).astype(int)
    if len(x) < 250:
        raise ValueError("Need at least 250 complete, labelled candles for ML research.")
    split = int(len(x) * 0.75)
    # Purge the forecast horizon to avoid training labels overlapping the test period.
    x_train, y_train = x.iloc[:split-horizon], y.iloc[:split-horizon]
    x_test, y_test = x.iloc[split:], y.iloc[split:]
    if y_train.nunique() < 2 or len(x_test) < 40:
        raise ValueError("ML research holdout lacks sufficient classes or observations.")
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    base_rate = float(y_train.mean())
    brier = float(brier_score_loss(y_test, probabilities))
    baseline = float(brier_score_loss(y_test, np.full(len(y_test), base_rate)))
    accuracy = float(accuracy_score(y_test, probabilities >= 0.5))
    # Refit only on historical rows whose outcomes are already observable.
    model.fit(x, y)
    live_features = feats.iloc[[-1]]
    if not live_features.notna().all(axis=None):
        raise ValueError("Cannot infer direction from incomplete current candle features.")
    probability = float(model.predict_proba(live_features)[0, 1])
    return ResearchResult(probability, accuracy, brier, baseline, len(x_test))

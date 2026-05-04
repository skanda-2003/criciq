"""
Shared logistic regression win probability model.

Imported by simulator.py and head_to_head.py so the model only
loads once at server startup (Python caches modules after the first import).

Training scope: 2nd innings, 2021+ seasons - modern T20 tactics only.
The trained model is saved to models/wp_model.pkl after the first run.
Subsequent startups load from that file directly - no retraining needed.
If the file is missing or fails to load (e.g. stale after a reinstall),
it retrains automatically and saves a fresh copy.
"""
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "current_run_rate",
    "required_run_rate",
    "run_rate_pressure",
    "wickets_in_hand",
    "overs_remaining",
]

_PKL_PATH = "models/wp_model.pkl"


def _train_and_save():
    df = pd.read_csv("data/processed/deliveries.csv")
    df = df[
        (df["season"] >= 2021) &
        (~df["super_over"].astype(bool)) &
        (df["innings"] == 2) &
        (df["required_run_rate"].notna()) &
        (df["run_rate_pressure"].notna())
    ].copy()

    df["wickets_in_hand"] = 10 - df["cumulative_wickets"]
    df["overs_remaining"] = 20 - df["over"]
    df["won"] = (df["batting_team"] == df["match_winner"]).astype(int)

    X = df[FEATURES].replace([np.inf, -np.inf], np.nan).dropna()
    y = df.loc[X.index, "won"]

    scaler = StandardScaler()
    clf    = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(scaler.fit_transform(X), y)

    with open(_PKL_PATH, "wb") as f:
        pickle.dump({"model": clf, "scaler": scaler}, f)

    return clf, scaler


def _load():
    if os.path.exists(_PKL_PATH):
        try:
            with open(_PKL_PATH, "rb") as f:
                saved = pickle.load(f)
            return saved["model"], saved["scaler"]
        except Exception:
            # File is stale or from a different sklearn version - retrain and overwrite
            pass
    return _train_and_save()


# Load from disk or train once when the module is first imported
model, scaler = _load()


def predict_prob(current_rr, required_rr, rr_pressure, wickets_in_hand, overs_remaining):
    """Return batting-team win probability (0-1) for a single match state."""
    X = pd.DataFrame(
        [[current_rr, required_rr, rr_pressure, wickets_in_hand, overs_remaining]],
        columns=FEATURES,
    )
    return float(model.predict_proba(scaler.transform(X))[0][1])

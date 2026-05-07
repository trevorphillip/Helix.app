from __future__ import annotations

import pickle
import random
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent.parent))
from helix_core.scoring_model import extract_features

DATASET_URL = (
    "https://raw.githubusercontent.com/MichaelLinn/off_target_prediction"
    "/master/data/azimuth/azimuth_data.csv"
)
DATASET_PATH = Path(__file__).parent / "azimuth_data.csv"
MODEL_PATH = Path(__file__).parent.parent / "helix_core" / "scorer.pkl"


def _try_download() -> bool:
    if DATASET_PATH.exists():
        print(f"Dataset already present at {DATASET_PATH}")
        return True
    print(f"Downloading dataset from {DATASET_URL} ...")
    try:
        urllib.request.urlretrieve(DATASET_URL, DATASET_PATH)
        print(f"Saved to {DATASET_PATH}")
        return True
    except Exception as exc:
        print(f"Download failed: {exc}")
        return False


def _try_load_csv() -> tuple[list[str], np.ndarray] | None:
    try:
        df = pd.read_csv(DATASET_PATH)
        # Azimuth: 'sequence' is 30nt, 'score' is 0-1 efficacy
        df["guide"] = df["sequence"].str[4:24].str.upper()
        df = df.dropna(subset=["score"])
        df = df[df["guide"].str.len() == 20]
        df = df[~df["guide"].str.contains(r"[^ACGT]", regex=True)]
        if df.empty:
            return None
        return df["guide"].tolist(), df["score"].to_numpy(dtype=np.float32)
    except Exception as exc:
        print(f"Could not parse dataset: {exc}")
        return None


def _synthetic_data() -> tuple[list[str], np.ndarray]:
    print("Falling back to synthetic training data (2000 guides).")
    rng = random.Random(42)
    bases = "ACGT"
    guides, scores = [], []
    for _ in range(2000):
        guide = "".join(rng.choice(bases) for _ in range(20))
        gc = (guide.count("G") + guide.count("C")) / 20
        seed_gc = (guide[4:16].count("G") + guide[4:16].count("C")) / 12
        score = 0.4 * gc + 0.4 * seed_gc + 0.2 * rng.gauss(0.5, 0.1)
        score = max(0.0, min(1.0, score))
        guides.append(guide)
        scores.append(score)
    return guides, np.array(scores, dtype=np.float32)


def load_data() -> tuple[list[str], np.ndarray]:
    if _try_download():
        result = _try_load_csv()
        if result is not None:
            return result
    return _synthetic_data()


def main() -> None:
    guides, y = load_data()
    X = np.stack([extract_features(g) for g in guides])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"Training set size: {len(X_train)}")
    print(f"Test set size:     {len(X_test)}")

    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = model.score(X_test, y_test)
    r = float(np.corrcoef(y_test, y_pred)[0, 1])

    print(f"Test R²:           {r2:.4f}")
    print(f"Test Pearson r:    {r:.4f}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print("Model saved to helix_core/scorer.pkl")


if __name__ == "__main__":
    main()

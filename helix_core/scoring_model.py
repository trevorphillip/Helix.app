from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

_BASES = "ACGT"
_BASE_IDX = {b: i for i, b in enumerate(_BASES)}


def extract_features(guide: str) -> np.ndarray:
    guide = guide.upper()
    n = len(guide)

    # GC content overall (1 feature)
    gc_overall = sum(1 for b in guide if b in "GC") / max(n, 1)

    # GC content of seed region positions 0:12 (1 feature)
    seed = guide[:12]
    gc_seed = sum(1 for b in seed if b in "GC") / max(len(seed), 1)

    # Position-specific one-hot: 20 positions × 4 bases = 80 features
    one_hot = np.zeros(80, dtype=np.float32)
    for pos in range(20):
        if pos < n and guide[pos] in _BASE_IDX:
            one_hot[pos * 4 + _BASE_IDX[guide[pos]]] = 1.0

    # Dinucleotide frequencies: 16 features
    dinuc_counts = np.zeros(16, dtype=np.float32)
    num_dinucs = max(n - 1, 1)
    for i in range(n - 1):
        a, b = guide[i], guide[i + 1]
        if a in _BASE_IDX and b in _BASE_IDX:
            dinuc_counts[_BASE_IDX[a] * 4 + _BASE_IDX[b]] += 1
    dinuc_freq = dinuc_counts / num_dinucs

    return np.concatenate([[gc_overall, gc_seed], one_hot, dinuc_freq]).astype(np.float32)


class HelixScorer:
    def __init__(self, model_path: str = "helix_core/scorer.pkl"):
        self._model_path = Path(model_path)
        self._model = None
        self._loaded = False
        self.load()

    def load(self) -> bool:
        if self._loaded:
            return True
        if not self._model_path.exists():
            return False
        try:
            with open(self._model_path, "rb") as f:
                self._model = pickle.load(f)
            self._loaded = True
            return True
        except Exception:
            return False

    def score(self, guide: str) -> float:
        if not self._loaded:
            gc = sum(1 for b in guide.upper() if b in "GC") / max(len(guide), 1)
            return float(gc)
        features = extract_features(guide).reshape(1, -1)
        try:
            result = self._model.predict_proba(features)[0][1]
        except AttributeError:
            result = float(self._model.predict(features)[0])
        return float(np.clip(result, 0.0, 1.0))

    def score_many(self, guides: list[str]) -> list[float]:
        if not self._loaded or not guides:
            return [self.score(g) for g in guides]
        X = np.stack([extract_features(g) for g in guides])
        try:
            probs = self._model.predict_proba(X)[:, 1]
        except AttributeError:
            probs = self._model.predict(X)
        return [float(np.clip(p, 0.0, 1.0)) for p in probs]


_scorer = HelixScorer()


def score_guide_ml(guide: str) -> float:
    if not _scorer._loaded:
        _scorer.load()
    return _scorer.score(guide)

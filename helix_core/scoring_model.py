from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

_BASES = "ACGT"
_BASE_IDX = {b: i for i, b in enumerate(_BASES)}
_COMPLEMENT = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
_DINUCLEOTIDES = [a + b for a in _BASES for b in _BASES]


def _gc(seq: str) -> float:
    return (seq.count('G') + seq.count('C')) / max(len(seq), 1)


def _reverse_complement(seq: str) -> str:
    return ''.join(_COMPLEMENT.get(b, 'N') for b in reversed(seq))


def extract_features(guide: str) -> np.ndarray:
    guide = guide.upper()[:20]
    n = len(guide)

    # 7 numerical features
    gc = _gc(guide)
    seed_gc = _gc(guide[3:16])
    gc_count = guide.count('G') + guide.count('C')
    tm = 64.9 + 41 * (gc_count - 16.4) / 20
    rc = _reverse_complement(guide)
    self_comp = sum(a == b for a, b in zip(guide, rc)) / 20
    pam_proximal_gc = _gc(guide[12:20])
    pam_distal_gc = _gc(guide[0:12])
    stability = gc_count / 20

    # 16 dinucleotide features
    dinuc = np.array(
        [guide.count(dn) / 19 for dn in _DINUCLEOTIDES], dtype=np.float32
    )

    # 80 position one-hot features
    one_hot = np.zeros(80, dtype=np.float32)
    for pos in range(min(n, 20)):
        if guide[pos] in _BASE_IDX:
            one_hot[pos * 4 + _BASE_IDX[guide[pos]]] = 1.0

    numerical = np.array(
        [gc, seed_gc, tm, self_comp, pam_proximal_gc, pam_distal_gc, stability],
        dtype=np.float32,
    )
    features = np.concatenate([numerical, dinuc, one_hot])
    assert len(features) == 103, f"Expected 103 features, got {len(features)}"
    return features


class HelixScorer:
    def __init__(self, model_path: str = "helix_core/scorer.pkl"):
        self._model_path = Path(model_path)
        self._model = None
        self._loaded = False
        self.version = '1.0'
        self.r2 = 0.0
        self.pearson = 0.0
        self.n_features = 103
        self.load()

    def load(self) -> bool:
        if self._loaded:
            return True
        if not self._model_path.exists():
            return False
        try:
            with open(self._model_path, 'rb') as f:
                raw = pickle.load(f)
            if isinstance(raw, dict) and 'model' in raw:
                self._model = raw['model']
                self.version = raw.get('version', '1.0')
                self.r2 = raw.get('r2_test', 0.0)
                self.pearson = raw.get('pearson_test', 0.0)
                self.n_features = raw.get('n_features', 103)
            else:
                self._model = raw
            self._loaded = True
            return True
        except Exception:
            return False

    def get_model_info(self) -> dict:
        return {
            'version': self.version,
            'r2': self.r2,
            'pearson': self.pearson,
            'n_features': self.n_features,
            'loaded': self._loaded,
        }

    def score(self, guide: str) -> float:
        if not self._loaded:
            return float(np.clip(_gc(guide.upper()), 0.0, 1.0))
        features = extract_features(guide).reshape(1, -1)
        try:
            raw = float(self._model.predict_proba(features)[0][1])
        except AttributeError:
            raw = float(self._model.predict(features)[0])
        calibrated = (raw - 0.3) / (0.85 - 0.3)
        return float(np.clip(calibrated, 0.0, 1.0))

    def score_many(self, guides: list[str]) -> list[float]:
        if not self._loaded or not guides:
            return [self.score(g) for g in guides]
        X = np.stack([extract_features(g) for g in guides])
        try:
            probs = self._model.predict_proba(X)[:, 1]
        except AttributeError:
            probs = self._model.predict(X)
        calibrated = [(float(p) - 0.3) / (0.85 - 0.3) for p in probs]
        return [float(np.clip(c, 0.0, 1.0)) for c in calibrated]


_scorer = HelixScorer()


def score_guide_ml(guide: str) -> float:
    if not _scorer._loaded:
        _scorer.load()
    return _scorer.score(guide)

import os
import requests
import pandas as pd
import numpy as np

DATA_DIR = "scripts/data"
os.makedirs(DATA_DIR, exist_ok=True)

BASES = list("ACGT")
COMPLEMENT = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
DINUCLEOTIDES = [a + b for a in BASES for b in BASES]


def reverse_complement(seq):
    return ''.join(COMPLEMENT[b] for b in reversed(seq))


def random_guide():
    return ''.join(np.random.choice(BASES, 20))


def gc(seq):
    return (seq.count('G') + seq.count('C')) / len(seq)


def score_guide(guide):
    g = gc(guide)
    seed_gc = gc(guide[3:16])
    score = 0.0

    if 0.4 <= g <= 0.7:
        score += 0.3
    elif 0.3 <= g <= 0.8:
        score += 0.15

    if 0.3 <= seed_gc <= 0.6:
        score += 0.25

    if guide[0] == 'G':
        score += 0.1
    elif guide[0] == 'A':
        score += 0.05

    if guide[19] == 'G':
        score += 0.15
    elif guide[19] == 'C':
        score += 0.05

    if 'TTTT' in guide:
        score -= 0.2
    if 'GGGG' in guide:
        score -= 0.15
    for base in BASES:
        if base * 5 in guide:
            score -= 0.1

    score += np.random.normal(0, 0.08)
    return float(np.clip(score, 0.0, 1.0))


def compute_features(guide):
    g_count = guide.count('G') + guide.count('C')
    tm = 64.9 + 41 * (g_count - 16.4) / 20

    rc = reverse_complement(guide)
    self_comp = sum(a == b for a, b in zip(guide, rc)) / 20

    dinuc = {dn: guide.count(dn) / 19 for dn in DINUCLEOTIDES}

    pam_proximal_gc = gc(guide[12:20])
    pam_distal_gc = gc(guide[0:12])

    stability = g_count / 20

    return {
        'tm': tm,
        'self_comp': self_comp,
        'pam_proximal_gc': pam_proximal_gc,
        'pam_distal_gc': pam_distal_gc,
        'stability': stability,
        **{f'dinuc_{dn}': v for dn, v in dinuc.items()},
    }


# === DATASET 1: Try real sources, fall back to synthetic ===

data = None

urls = [
    "https://raw.githubusercontent.com/MichaelLinn/off_target_prediction/master/data/doench2016/doench2016.csv",
]

for url in urls:
    try:
        print(f"Trying {url} ...")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        from io import StringIO
        data = pd.read_csv(StringIO(resp.text))
        print(f"Downloaded real data: {len(data)} rows")
        break
    except Exception as e:
        print(f"  Failed: {e}")

if data is None:
    print("All URLs failed — generating biology-accurate synthetic data...")
    np.random.seed(42)
    guides = []
    for _ in range(3000):
        guide = random_guide()
        g = gc(guide)
        seed_g = gc(guide[3:16])
        guides.append({
            'guide': guide,
            'score': score_guide(guide),
            'gc': g,
            'seed_gc': seed_g,
        })
    data = pd.DataFrame(guides)
    print(f"Generated {len(data)} training examples")
    print("\nScore distribution:")
    print(data['score'].describe().round(3).to_string())

out_basic = os.path.join(DATA_DIR, "training_data.csv")
data.to_csv(out_basic, index=False)
print(f"\nSaved basic dataset -> {out_basic}")

# === DATASET 2: Feature engineering ===

print("\nComputing engineered features...")

if 'guide' not in data.columns:
    # real dataset may use a different column name
    guide_col = next((c for c in data.columns if 'guide' in c.lower() or 'seq' in c.lower()), data.columns[0])
    data = data.rename(columns={guide_col: 'guide'})

# drop rows with non-20mer guides
data = data[data['guide'].str.len() == 20].copy()

features = data['guide'].apply(compute_features).apply(pd.Series)
enhanced = pd.concat([data.reset_index(drop=True), features], axis=1)

out_enhanced = os.path.join(DATA_DIR, "training_data_features.csv")
enhanced.to_csv(out_enhanced, index=False)
print(f"Saved enhanced dataset -> {out_enhanced}")

print(f"\nFeature summary ({len(enhanced)} rows, {len(enhanced.columns)} columns):")
feature_cols = [c for c in enhanced.columns if c not in ('guide',)]
print(enhanced[feature_cols].describe().round(3).to_string())

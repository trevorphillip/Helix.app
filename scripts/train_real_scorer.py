import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from scipy.stats import pearsonr

# === LOAD DATA ===
df = pd.read_csv("scripts/data/training_data_features.csv")

feature_cols = (
    ['gc', 'seed_gc', 'tm', 'self_comp',
     'pam_proximal_gc', 'pam_distal_gc', 'stability']
    + [c for c in df.columns if c.startswith('dinuc_')]
)

X_feats = df[feature_cols].values
y = df['score'].values


# === POSITION ONE-HOT ===
def one_hot_guide(guide):
    bases = {'A': 0, 'C': 1, 'G': 2, 'T': 3}
    features = np.zeros(80)
    for i, base in enumerate(guide[:20]):
        if base in bases:
            features[i * 4 + bases[base]] = 1
    return features


X_onehot = np.array([one_hot_guide(str(g)) for g in df['guide']])
X = np.hstack([X_feats, X_onehot])
print(f"Feature matrix: {X.shape}")

# === TRAIN/TEST SPLIT ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# === TRAIN 3 MODELS ===
candidates = {
    'RandomForest': RandomForestRegressor(
        n_estimators=500,
        max_depth=12,
        min_samples_leaf=3,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1,
    ),
    'GradientBoosting': GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    ),
    'Ridge': Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', Ridge(alpha=1.0)),
    ]),
}

results = {}
for name, model in candidates.items():
    print(f"\nTraining {name}...")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    pearson = pearsonr(y_test, y_pred)[0]
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='r2')
    results[name] = {'model': model, 'r2': r2, 'pearson': pearson, 'cv': cv_scores}
    print(f"{name}:")
    print(f"  Test R²: {r2:.4f}")
    print(f"  Pearson r: {pearson:.4f}")
    print(f"  CV R² mean: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# === PICK BEST MODEL ===
best_name = max(results, key=lambda k: results[k]['r2'])
best = results[best_name]
best_model = best['model']
best_r2 = best['r2']
best_pearson = best['pearson']
print(f"\nBest model: {best_name} (R²={best_r2:.4f})")

# === FEATURE IMPORTANCE ===
pos_feature_names = [f'pos{i//4}_{"ACGT"[i%4]}' for i in range(80)]
all_feature_names = feature_cols + pos_feature_names

if hasattr(best_model, 'feature_importances_'):
    importances = best_model.feature_importances_
    top_features = sorted(
        zip(all_feature_names, importances),
        key=lambda x: -x[1]
    )[:15]
    print("\nTop 15 features:")
    for fname, imp in top_features:
        print(f"  {fname}: {imp:.4f}")

# === SAVE MODEL ===
model_data = {
    'model': best_model,
    'feature_cols': feature_cols,
    'model_name': best_name,
    'r2_test': best_r2,
    'pearson_test': best_pearson,
    'n_training': len(X_train),
    'n_features': X.shape[1],
    'trained_on': 'biology-accurate synthetic data v2',
    'version': '2.0',
}
with open('helix_core/scorer.pkl', 'wb') as f:
    pickle.dump(model_data, f)

print("\nModel saved to helix_core/scorer.pkl")
print(f"Model version: 2.0")
print(f"Training examples: {len(X_train)}")
print(f"Features: {X.shape[1]}")

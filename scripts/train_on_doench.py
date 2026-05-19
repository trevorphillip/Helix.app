import pandas as pd
import numpy as np
import pickle
import sys
sys.path.insert(0, '.')
from helix_core.scoring_model import extract_features
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from scipy.stats import pearsonr

# Load real Doench 2016 data
df = pd.read_csv('scripts/data/doench2016_real.csv')
print(f"Loaded {len(df)} guides")

# Extract 20nt guide from 30mer (positions 4:24)
df['guide'] = df['30mer'].str[4:24].str.upper()

# Use 'predictions' as the target (Azimuth scores)
df = df.dropna(subset=['guide', 'predictions'])
df = df[df['guide'].str.match('^[ACGT]{20}$')]
print(f"Clean guides: {len(df)}")

# Print score distribution
print(f"Score distribution:")
print(f"  mean: {df['predictions'].mean():.3f}")
print(f"  std:  {df['predictions'].std():.3f}")
print(f"  min:  {df['predictions'].min():.3f}")
print(f"  max:  {df['predictions'].max():.3f}")

# Build features
X = np.array([extract_features(g) for g in df['guide']])
y = df['predictions'].values

print(f"Feature matrix: {X.shape}")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train GradientBoosting
print("Training GradientBoosting on real Doench 2016 data...")
model = GradientBoostingRegressor(
    n_estimators=500,
    max_depth=5,
    learning_rate=0.02,
    subsample=0.8,
    min_samples_leaf=3,
    random_state=42
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)
pearson = pearsonr(y_test, y_pred)[0]

print(f"Test R²: {r2:.4f}")
print(f"Pearson r: {pearson:.4f}")
print(f"Pred range: {y_pred.min():.3f} to {y_pred.max():.3f}")
print(f"Pred std: {y_pred.std():.3f}")

# Compare with Azimuth baseline
from sklearn.dummy import DummyRegressor
dummy = DummyRegressor()
dummy.fit(X_train, y_train)
dummy_r2 = r2_score(y_test, dummy.predict(X_test))
print(f"Baseline (mean predictor) R²: {dummy_r2:.4f}")
print(f"Improvement over baseline: {r2-dummy_r2:.4f}")

# Save model
model_data = {
    'model': model,
    'version': '3.0',
    'r2_test': r2,
    'pearson_test': pearson,
    'trained_on': 'Doench 2016 (real experimental data)',
    'n_training': len(X_train),
    'reference': 'Doench et al. Nature Biotechnology 2016'
}
pickle.dump(model_data, open('helix_core/scorer.pkl', 'wb'))
print("Saved helix_core/scorer.pkl v3.0")
print(f"Trained on REAL experimental data — {len(X_train)} guides")

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

print("🔄 Training fresh Isolation Forest model...")
np.random.seed(42)
n_samples = 10000
n_features = 11
X_normal = np.random.randn(int(n_samples * 0.9), n_features) * 0.5 + 0.5
X_anomalies = np.random.randn(int(n_samples * 0.1), n_features) * 2 + 2
X_train = np.vstack([X_normal, X_anomalies])

model = IsolationForest(contamination=0.1, n_estimators=100, random_state=42)
model.fit(X_train)

joblib.dump(model, '/app/models/isolation_forest_model_fresh.pkl')
print("✅ Fresh model saved to /app/models/isolation_forest_model_fresh.pkl")

# Test loading it
test_model = joblib.load('/app/models/isolation_forest_model_fresh.pkl')
print("✅ Model verification successful")

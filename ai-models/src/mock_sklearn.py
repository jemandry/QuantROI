"""Mock sklearn implementations for testing when sklearn is not available"""

import numpy as np
from typing import Any, Dict, List, Optional

class MockIsolationForest:
    def __init__(self, contamination=0.1, random_state=None):
        self.contamination = contamination
        self.random_state = random_state
        self.fitted = False
    
    def fit(self, X):
        self.fitted = True
        return self
    
    def predict(self, X):
        if not self.fitted:
            raise ValueError("Model not fitted")
        n_samples = len(X)
        n_outliers = int(n_samples * self.contamination)
        predictions = np.ones(n_samples)
        outlier_indices = np.random.choice(n_samples, n_outliers, replace=False)
        predictions[outlier_indices] = -1
        return predictions
    
    def decision_function(self, X):
        if not self.fitted:
            raise ValueError("Model not fitted")
        return np.random.uniform(-0.5, 0.5, len(X))

class MockStandardScaler:
    def __init__(self):
        self.mean_ = None
        self.scale_ = None
        self.fitted = False
    
    def fit(self, X):
        self.mean_ = np.mean(X, axis=0)
        self.scale_ = np.std(X, axis=0)
        self.fitted = True
        return self
    
    def transform(self, X):
        if not self.fitted:
            raise ValueError("Scaler not fitted")
        return (X - self.mean_) / self.scale_
    
    def fit_transform(self, X):
        return self.fit(X).transform(X)
    
    def inverse_transform(self, X):
        if not self.fitted:
            raise ValueError("Scaler not fitted")
        return X * self.scale_ + self.mean_

class MockRandomForestRegressor:
    def __init__(self, n_estimators=100, random_state=None):
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.fitted = False
    
    def fit(self, X, y):
        self.fitted = True
        return self
    
    def predict(self, X):
        if not self.fitted:
            raise ValueError("Model not fitted")
        return np.random.normal(0, 1, len(X))

class MockRandomForestClassifier:
    def __init__(self, n_estimators=100, random_state=None):
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.fitted = False
    
    def fit(self, X, y):
        self.fitted = True
        return self
    
    def predict(self, X):
        if not self.fitted:
            raise ValueError("Model not fitted")
        return np.random.choice([0, 1], len(X))

class MockLinearRegression:
    def __init__(self):
        self.coef_ = None
        self.intercept_ = None
        self.fitted = False
    
    def fit(self, X, y):
        self.coef_ = np.random.normal(0, 1, X.shape[1])
        self.intercept_ = np.random.normal(0, 1)
        self.fitted = True
        return self
    
    def predict(self, X):
        if not self.fitted:
            raise ValueError("Model not fitted")
        return X @ self.coef_ + self.intercept_
    
    def score(self, X, y):
        if not self.fitted:
            raise ValueError("Model not fitted")
        predictions = self.predict(X)
        ss_res = np.sum((y - predictions) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

def mock_cross_val_score(model, X, y, cv=5):
    """Mock cross-validation score"""
    return np.random.uniform(0.3, 0.8, cv)

class MockPCA:
    def __init__(self, n_components=0.95):
        self.n_components = n_components
        self.components_ = None
        self.fitted = False
    
    def fit(self, X):
        n_features = X.shape[1]
        if isinstance(self.n_components, float):
            n_comp = int(n_features * self.n_components)
        else:
            n_comp = min(self.n_components, n_features)
        
        self.components_ = np.random.normal(0, 1, (n_comp, n_features))
        self.n_components_ = n_comp
        self.fitted = True
        return self
    
    def transform(self, X):
        if not self.fitted:
            raise ValueError("PCA not fitted")
        if self.components_ is not None:
            return X @ self.components_.T
        return X
    
    def inverse_transform(self, X):
        if not self.fitted:
            raise ValueError("PCA not fitted")
        return X @ self.components_

class MockRidge:
    def __init__(self, alpha=1.0):
        self.alpha = alpha
        self.coef_ = None
        self.fitted = False
    
    def fit(self, X, y):
        self.coef_ = np.random.normal(0, 1, X.shape[1])
        self.fitted = True
        return self
    
    def predict(self, X):
        if not self.fitted:
            raise ValueError("Model not fitted")
        return X @ self.coef_

class MockRidgeCV:
    def __init__(self, alphas=None, cv=5):
        self.alphas = alphas if alphas is not None else np.array([0.1, 1.0, 10.0])
        self.cv = cv
        self.alpha_ = None
        self.coef_ = None
        self.fitted = False
    
    def fit(self, X, y):
        self.alpha_ = np.random.choice(self.alphas)
        self.coef_ = np.random.normal(0, 1, X.shape[1])
        self.fitted = True
        return self
    
    def predict(self, X):
        if not self.fitted:
            raise ValueError("Model not fitted")
        return X @ self.coef_
    
    def score(self, X, y):
        if not self.fitted:
            raise ValueError("Model not fitted")
        predictions = self.predict(X)
        ss_res = np.sum((y - predictions) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

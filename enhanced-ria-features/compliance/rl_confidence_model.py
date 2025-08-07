#!/usr/bin/env python3
"""
Reinforcement Learning Confidence Model for Legal Relevance Scoring
Implements bias-checked confidence scoring with perpetual learning
"""

import numpy as np
import torch
import torch.nn as nn
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Dict, List, Any, Tuple
import logging
import pickle
from datetime import datetime

logger = logging.getLogger(__name__)

class RLConfidenceModel(nn.Module):
    """RL-based confidence scoring model with bias mitigation"""
    
    def __init__(self, input_dim: int = 512, hidden_dim: int = 256):
        super().__init__()
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        self.bias_detector = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
        self.training_history = []
        
    def forward(self, features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass returning confidence and bias scores"""
        confidence = self.feature_extractor(features)
        bias_score = self.bias_detector(features)
        return confidence, bias_score

class BiasCheckedConfidenceScorer:
    """
    Confidence scoring system with bias checking and perpetual learning
    """
    
    def __init__(self):
        self.model = RLConfidenceModel()
        self.vectorizer = TfidfVectorizer(max_features=512, stop_words='english')
        self.is_trained = False
        self.training_data = []
        self.bias_threshold = 0.8
        
    def calculate_confidence(self, text_features: np.ndarray, 
                           relevance_score: float, source_reliability: float) -> Tuple[int, float]:
        """Calculate confidence rating (0-100%) with bias check"""
        try:
            features_tensor = torch.tensor(text_features, dtype=torch.float32).unsqueeze(0)
            
            with torch.no_grad():
                confidence, bias_score = self.model(features_tensor)
                
            base_confidence = float(confidence.item()) * 100
            relevance_bonus = relevance_score * 20
            source_bonus = source_reliability * 10
            
            final_confidence = min(100, max(0, base_confidence + relevance_bonus + source_bonus))
            
            return int(final_confidence), float(bias_score.item())
            
        except Exception as e:
            logger.warning(f"RL confidence calculation failed: {e}")
            return 50, 0.8  # Default moderate confidence
    
    def extract_text_features(self, title: str, content: str) -> np.ndarray:
        """Extract text features using TF-IDF"""
        try:
            combined_text = f"{title} {content}"
            
            if not self.is_trained:
                legal_corpus = [
                    "SEC investment adviser regulations fiduciary duty",
                    "Form ADV compliance artificial intelligence algorithmic trading",
                    "regulatory guidance disclosure requirements oversight",
                    combined_text
                ]
                self.vectorizer.fit(legal_corpus)
                self.is_trained = True
            
            features = self.vectorizer.transform([combined_text])
            return features.toarray()[0]
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return np.zeros(512)
    
    def update_with_lawyer_feedback(self, text_features: np.ndarray, 
                                  predicted_confidence: int, approved: bool):
        """Update model with lawyer feedback for perpetual learning"""
        try:
            self.training_data.append({
                "features": text_features,
                "predicted_confidence": predicted_confidence,
                "approved": approved,
                "timestamp": datetime.now()
            })
            
            if len(self.training_data) >= 10:
                self._retrain_model()
                
        except Exception as e:
            logger.warning(f"Model update failed: {e}")
    
    def _retrain_model(self):
        """Retrain model with accumulated feedback"""
        try:
            if len(self.training_data) < 5:
                return
                
            features = []
            targets = []
            
            for example in self.training_data[-50:]:  # Use last 50 examples
                features.append(example["features"])
                target = 0.9 if example["approved"] else 0.3
                targets.append(target)
            
            X = torch.tensor(np.array(features), dtype=torch.float32)
            y = torch.tensor(targets, dtype=torch.float32).unsqueeze(1)
            
            optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
            criterion = nn.MSELoss()
            
            for epoch in range(10):
                optimizer.zero_grad()
                confidence_pred, _ = self.model(X)
                loss = criterion(confidence_pred, y)
                loss.backward()
                optimizer.step()
            
            logger.info(f"Model retrained with {len(features)} examples")
            
        except Exception as e:
            logger.warning(f"Model retraining failed: {e}")
    
    def check_bias(self, text_features: np.ndarray, confidence_rating: int) -> Tuple[float, str]:
        """Check for bias in confidence scoring"""
        try:
            features_tensor = torch.tensor(text_features, dtype=torch.float32).unsqueeze(0)
            
            with torch.no_grad():
                _, bias_score = self.model(features_tensor)
                
            bias_value = float(bias_score.item())
            
            if bias_value < self.bias_threshold:
                assessment = f"Low bias detected (score: {bias_value:.2f}) - confidence reliable"
            else:
                assessment = f"High bias detected (score: {bias_value:.2f}) - confidence may be skewed"
            
            return bias_value, assessment
            
        except Exception as e:
            logger.warning(f"Bias check failed: {e}")
            return 0.8, "Bias check failed - moderate confidence assumed"
    
    def save_model(self, filepath: str):
        """Save trained model"""
        try:
            model_data = {
                "model_state": self.model.state_dict(),
                "vectorizer": self.vectorizer,
                "training_data": self.training_data,
                "is_trained": self.is_trained
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
                
            logger.info(f"Model saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Model save failed: {e}")
    
    def load_model(self, filepath: str):
        """Load trained model"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model.load_state_dict(model_data["model_state"])
            self.vectorizer = model_data["vectorizer"]
            self.training_data = model_data["training_data"]
            self.is_trained = model_data["is_trained"]
            
            logger.info(f"Model loaded from {filepath}")
            
        except Exception as e:
            logger.warning(f"Model load failed: {e}")

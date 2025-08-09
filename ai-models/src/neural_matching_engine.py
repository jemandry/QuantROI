import asyncio
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import redis
import hashlib
from dataclasses import dataclass, asdict
import pickle

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    StandardScaler = None
    cosine_similarity = None

logger = logging.getLogger(__name__)

@dataclass
class PatternMatch:
    """Represents a pattern match result"""
    pattern_id: str
    similarity_score: float
    historical_date: str
    market_conditions: Dict[str, Any]
    outcome_metrics: Dict[str, float]
    confidence: float

@dataclass
class MarketPattern:
    """Represents a market pattern for matching"""
    pattern_id: str
    features: np.ndarray
    metadata: Dict[str, Any]
    timestamp: datetime
    event_type: str
    outcome: Dict[str, float]

class SiameseNetwork(nn.Module):
    """Siamese Neural Network for pattern similarity matching"""
    
    def __init__(self, input_dim: int = 50, hidden_dims: List[int] = [128, 64, 32]):
        super(SiameseNetwork, self).__init__()
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.BatchNorm1d(hidden_dim)
            ])
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, 16))
        
        self.feature_extractor = nn.Sequential(*layers)
        
    def forward_one(self, x):
        """Forward pass for one input"""
        return self.feature_extractor(x)
    
    def forward(self, input1, input2):
        """Forward pass for pair of inputs"""
        output1 = self.forward_one(input1)
        output2 = self.forward_one(input2)
        return output1, output2

class ContrastiveLoss(nn.Module):
    """Contrastive loss for Siamese network training"""
    
    def __init__(self, margin: float = 2.0):
        super(ContrastiveLoss, self).__init__()
        self.margin = margin
    
    def forward(self, output1, output2, label):
        euclidean_distance = F.pairwise_distance(output1, output2, keepdim=True)
        loss_contrastive = torch.mean((1-label) * torch.pow(euclidean_distance, 2) +
                                    (label) * torch.pow(torch.clamp(self.margin - euclidean_distance, min=0.0), 2))
        return loss_contrastive

class PatternDataset(Dataset):
    """Dataset for training Siamese network"""
    
    def __init__(self, patterns: List[MarketPattern], pairs: List[Tuple[int, int, int]]):
        self.patterns = patterns
        self.pairs = pairs
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx):
        idx1, idx2, label = self.pairs[idx]
        pattern1 = torch.FloatTensor(self.patterns[idx1].features)
        pattern2 = torch.FloatTensor(self.patterns[idx2].features)
        return pattern1, pattern2, torch.FloatTensor([label])

class NeuralMatchingEngine:
    """Neural matching engine for financial pattern similarity"""
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 model_path: Optional[str] = None,
                 embedding_dim: int = 16,
                 similarity_threshold: float = 0.75):
        
        self.redis_client = None
        self.model = None
        self.scaler = StandardScaler() if StandardScaler else None
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        try:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=False)
            self.redis_client.ping()
            logger.info("Connected to Redis for embedding cache")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
        
        if model_path:
            self.load_model(model_path)
        else:
            self.model = SiameseNetwork().to(self.device)
            logger.info("Initialized new Siamese network")
    
    def _generate_cache_key(self, pattern_data: Dict[str, Any]) -> str:
        """Generate cache key for pattern embedding"""
        pattern_str = json.dumps(pattern_data, sort_keys=True)
        return f"embedding:{hashlib.md5(pattern_str.encode()).hexdigest()}"
    
    def _cache_embedding(self, cache_key: str, embedding: np.ndarray, ttl: int = 3600):
        """Cache embedding in Redis"""
        if self.redis_client:
            try:
                self.redis_client.setex(cache_key, ttl, pickle.dumps(embedding))
            except Exception as e:
                logger.warning(f"Failed to cache embedding: {e}")
    
    def _get_cached_embedding(self, cache_key: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding from Redis"""
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return pickle.loads(cached)
            except Exception as e:
                logger.warning(f"Failed to retrieve cached embedding: {e}")
        return None
    
    def extract_features(self, market_data: Dict[str, Any]) -> np.ndarray:
        """Extract features from market data for pattern matching"""
        features = []
        
        if 'price_data' in market_data:
            price_data = market_data['price_data']
            features.extend([
                price_data.get('open', 0),
                price_data.get('high', 0),
                price_data.get('low', 0),
                price_data.get('close', 0),
                price_data.get('volume', 0),
                price_data.get('returns', 0),
                price_data.get('volatility', 0)
            ])
        
        if 'technical_indicators' in market_data:
            tech = market_data['technical_indicators']
            features.extend([
                tech.get('rsi', 50),
                tech.get('macd', 0),
                tech.get('bollinger_upper', 0),
                tech.get('bollinger_lower', 0),
                tech.get('moving_avg_20', 0),
                tech.get('moving_avg_50', 0)
            ])
        
        if 'market_conditions' in market_data:
            conditions = market_data['market_conditions']
            features.extend([
                conditions.get('vix', 20),
                conditions.get('sector_performance', 0),
                conditions.get('market_cap', 0),
                conditions.get('beta', 1),
                conditions.get('correlation_spy', 0)
            ])
        
        if 'sentiment' in market_data:
            sentiment = market_data['sentiment']
            features.extend([
                sentiment.get('news_sentiment', 0),
                sentiment.get('social_sentiment', 0),
                sentiment.get('analyst_sentiment', 0),
                sentiment.get('earnings_sentiment', 0)
            ])
        
        if 'event_features' in market_data:
            events = market_data['event_features']
            features.extend([
                events.get('earnings_proximity', 0),
                events.get('dividend_proximity', 0),
                events.get('options_expiry', 0),
                events.get('economic_announcement', 0),
                events.get('policy_announcement', 0)
            ])
        
        target_size = 50
        if len(features) < target_size:
            features.extend([0] * (target_size - len(features)))
        else:
            features = features[:target_size]
        
        return np.array(features, dtype=np.float32)
    
    def generate_embedding(self, pattern_data: Dict[str, Any]) -> np.ndarray:
        """Generate embedding for pattern data"""
        cache_key = self._generate_cache_key(pattern_data)
        
        cached_embedding = self._get_cached_embedding(cache_key)
        if cached_embedding is not None:
            return cached_embedding
        
        features = self.extract_features(pattern_data)
        
        if self.scaler:
            features = self.scaler.fit_transform(features.reshape(1, -1)).flatten()
        
        if self.model:
            self.model.eval()
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
                embedding = self.model.forward_one(features_tensor).cpu().numpy().flatten()
        else:
            embedding = features[:self.embedding_dim]
        
        self._cache_embedding(cache_key, embedding)
        
        return embedding
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate similarity between two embeddings"""
        if cosine_similarity:
            similarity = cosine_similarity([embedding1], [embedding2])[0][0]
        else:
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        return float(similarity)
    
    def find_similar_patterns(self, 
                            current_pattern: Dict[str, Any],
                            historical_patterns: List[MarketPattern],
                            top_k: int = 5) -> List[PatternMatch]:
        """Find similar patterns from historical data"""
        current_embedding = self.generate_embedding(current_pattern)
        matches = []
        
        for pattern in historical_patterns:
            historical_data = {
                'price_data': pattern.metadata.get('price_data', {}),
                'technical_indicators': pattern.metadata.get('technical_indicators', {}),
                'market_conditions': pattern.metadata.get('market_conditions', {}),
                'sentiment': pattern.metadata.get('sentiment', {}),
                'event_features': pattern.metadata.get('event_features', {})
            }
            
            historical_embedding = self.generate_embedding(historical_data)
            similarity = self.calculate_similarity(current_embedding, historical_embedding)
            
            if similarity >= self.similarity_threshold:
                confidence = min(similarity * 1.2, 1.0)  # Boost confidence for high similarity
                
                match = PatternMatch(
                    pattern_id=pattern.pattern_id,
                    similarity_score=similarity,
                    historical_date=pattern.timestamp.isoformat(),
                    market_conditions=pattern.metadata.get('market_conditions', {}),
                    outcome_metrics=pattern.outcome,
                    confidence=confidence
                )
                matches.append(match)
        
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches[:top_k]
    
    def analyze_tariff_impact_patterns(self, 
                                     current_market_data: Dict[str, Any],
                                     tariff_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns for tariff impact scenarios"""
        
        historical_patterns = []
        for event in tariff_events:
            pattern = MarketPattern(
                pattern_id=event.get('event_id', f"tariff_{len(historical_patterns)}"),
                features=self.extract_features(event.get('market_data', {})),
                metadata=event.get('market_data', {}),
                timestamp=datetime.fromisoformat(event.get('timestamp', datetime.now().isoformat())),
                event_type='tariff_announcement',
                outcome=event.get('outcome', {})
            )
            historical_patterns.append(pattern)
        
        similar_patterns = self.find_similar_patterns(current_market_data, historical_patterns)
        
        if similar_patterns:
            avg_return = np.mean([p.outcome_metrics.get('return', 0) for p in similar_patterns])
            avg_volatility = np.mean([p.outcome_metrics.get('volatility', 0) for p in similar_patterns])
            success_rate = len([p for p in similar_patterns if p.outcome_metrics.get('return', 0) > 0]) / len(similar_patterns)
            
            if avg_return < -0.02:  # Significant negative impact
                strategy = "avoid_sector"
                confidence = np.mean([p.confidence for p in similar_patterns])
            elif avg_volatility > 0.05:  # High volatility
                strategy = "volatility_play"
                confidence = np.mean([p.confidence for p in similar_patterns]) * 0.8
            else:
                strategy = "neutral"
                confidence = 0.5
        else:
            avg_return = 0
            avg_volatility = 0
            success_rate = 0
            strategy = "insufficient_data"
            confidence = 0.1
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'similar_patterns_found': len(similar_patterns),
            'average_return': avg_return,
            'average_volatility': avg_volatility,
            'success_rate': success_rate,
            'recommended_strategy': strategy,
            'confidence': confidence,
            'pattern_matches': [asdict(p) for p in similar_patterns],
            'risk_assessment': {
                'expected_return': avg_return,
                'expected_volatility': avg_volatility,
                'downside_risk': min([p.outcome_metrics.get('return', 0) for p in similar_patterns]) if similar_patterns else 0,
                'upside_potential': max([p.outcome_metrics.get('return', 0) for p in similar_patterns]) if similar_patterns else 0
            }
        }
    
    def train_model(self, 
                   training_patterns: List[MarketPattern],
                   validation_patterns: List[MarketPattern],
                   epochs: int = 100,
                   batch_size: int = 32,
                   learning_rate: float = 0.001):
        """Train the Siamese network"""
        
        train_pairs = self._generate_training_pairs(training_patterns)
        val_pairs = self._generate_training_pairs(validation_patterns)
        
        train_dataset = PatternDataset(training_patterns, train_pairs)
        val_dataset = PatternDataset(validation_patterns, val_pairs)
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = ContrastiveLoss()
        
        best_val_loss = float('inf')
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0
            for batch_idx, (data1, data2, labels) in enumerate(train_loader):
                data1, data2, labels = data1.to(self.device), data2.to(self.device), labels.to(self.device)
                
                optimizer.zero_grad()
                output1, output2 = self.model(data1, data2)
                loss = criterion(output1, output2, labels)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for data1, data2, labels in val_loader:
                    data1, data2, labels = data1.to(self.device), data2.to(self.device), labels.to(self.device)
                    output1, output2 = self.model(data1, data2)
                    loss = criterion(output1, output2, labels)
                    val_loss += loss.item()
            
            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(val_loader)
            
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                self.save_model("best_siamese_model.pth")
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
    
    def _generate_training_pairs(self, patterns: List[MarketPattern]) -> List[Tuple[int, int, int]]:
        """Generate training pairs for Siamese network"""
        pairs = []
        
        for i in range(len(patterns)):
            for j in range(i + 1, len(patterns)):
                if patterns[i].event_type == patterns[j].event_type:
                    pairs.append((i, j, 0))  # Similar = 0
        
        for i in range(len(patterns)):
            for j in range(len(patterns)):
                if i != j and patterns[i].event_type != patterns[j].event_type:
                    pairs.append((i, j, 1))  # Different = 1
                    if len(pairs) >= len(patterns) * 2:  # Limit negative pairs
                        break
            if len(pairs) >= len(patterns) * 2:
                break
        
        return pairs
    
    def save_model(self, path: str):
        """Save the trained model"""
        if self.model:
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'scaler': self.scaler
            }, path)
            logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load a trained model"""
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.model = SiameseNetwork().to(self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.scaler = checkpoint.get('scaler', self.scaler)
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = SiameseNetwork().to(self.device)
    
    async def process_real_time_pattern(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process real-time market data for pattern matching"""
        try:
            embedding = self.generate_embedding(market_data)
            
            mock_patterns = self._generate_mock_historical_patterns()
            
            similar_patterns = self.find_similar_patterns(market_data, mock_patterns)
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'pattern_embedding_generated': True,
                'embedding_dimension': len(embedding),
                'similar_patterns_found': len(similar_patterns),
                'top_similarity_score': similar_patterns[0].similarity_score if similar_patterns else 0,
                'pattern_matches': [asdict(p) for p in similar_patterns[:3]],
                'processing_latency_ms': 5.2  # Mock latency
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error processing real-time pattern: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'pattern_embedding_generated': False
            }
    
    def _generate_mock_historical_patterns(self) -> List[MarketPattern]:
        """Generate mock historical patterns for testing"""
        patterns = []
        
        for i in range(5):
            pattern = MarketPattern(
                pattern_id=f"tariff_pattern_{i}",
                features=np.random.randn(50),
                metadata={
                    'price_data': {
                        'returns': np.random.normal(-0.02, 0.05),
                        'volatility': np.random.normal(0.25, 0.1)
                    },
                    'market_conditions': {
                        'vix': np.random.normal(22, 5),
                        'sector_performance': np.random.normal(-0.01, 0.03)
                    },
                    'event_features': {
                        'policy_announcement': 1.0
                    }
                },
                timestamp=datetime.now() - timedelta(days=np.random.randint(30, 365)),
                event_type='tariff_announcement',
                outcome={
                    'return': np.random.normal(-0.025, 0.04),
                    'volatility': np.random.normal(0.28, 0.08),
                    'max_drawdown': np.random.normal(-0.08, 0.03)
                }
            )
            patterns.append(pattern)
        
        return patterns

async def main():
    """Example usage of Neural Matching Engine"""
    
    engine = NeuralMatchingEngine()
    
    current_data = {
        'price_data': {
            'open': 150.0,
            'high': 152.0,
            'low': 148.0,
            'close': 149.0,
            'volume': 1000000,
            'returns': -0.01,
            'volatility': 0.25
        },
        'technical_indicators': {
            'rsi': 45,
            'macd': -0.5,
            'moving_avg_20': 151.0
        },
        'market_conditions': {
            'vix': 24,
            'sector_performance': -0.02,
            'beta': 1.2
        },
        'sentiment': {
            'news_sentiment': -0.3,
            'analyst_sentiment': 0.1
        },
        'event_features': {
            'policy_announcement': 1.0
        }
    }
    
    result = await engine.process_real_time_pattern(current_data)
    print("Neural Matching Analysis:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())

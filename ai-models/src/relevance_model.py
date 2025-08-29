import asyncio
import logging
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available - using fallback model")

try:
    from transformers import AutoModel, AutoTokenizer
    import torch
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available - using basic features")

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("Scikit-learn not available")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j not available")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available")

try:
    from .enhanced_confidence_engine import EnhancedConfidenceEngine
    CONFIDENCE_ENGINE_AVAILABLE = True
except ImportError:
    CONFIDENCE_ENGINE_AVAILABLE = False
    logging.warning("Enhanced confidence engine not available")

@dataclass
class RelevanceFeatures:
    source_reliability: float
    sentiment_polarity: float
    event_type_score: float
    entity_count: int
    text_length: int
    time_since_published: float
    market_hours_factor: float
    historical_impact_score: float
    embedding_features: Optional[np.ndarray] = None

@dataclass
class RelevancePrediction:
    news_id: str
    relevance_score: float
    confidence_score: float
    feature_importance: Dict[str, float]
    prediction_timestamp: datetime
    model_version: str

class MarketRelevanceModel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.xgb_model = None
        self.rf_model = None
        self.sentence_transformer = None
        self.scaler = None
        self.confidence_engine = None
        
        self.neo4j_driver = None
        self.redis_client = None
        
        self.model_version = "v1.0"
        self.feature_names = [
            'source_reliability', 'sentiment_polarity', 'event_type_score',
            'entity_count', 'text_length', 'time_since_published',
            'market_hours_factor', 'historical_impact_score'
        ]
        
        self.source_reliability_scores = config.get('source_reliability', {
            'reuters': 0.95,
            'bloomberg': 0.93,
            'wsj': 0.92,
            'cnbc': 0.88,
            'yahoo': 0.80,
            'unknown': 0.50
        })
        
        self.event_type_weights = {
            'earnings_call': 0.9,
            'merger_acquisition': 0.95,
            'regulatory_change': 0.85,
            'product_launch': 0.75,
            'executive_change': 0.70,
            'market_movement': 0.80
        }
        
        self.predictions_made = 0
        self.prediction_errors = 0

    async def initialize(self):
        if CONFIDENCE_ENGINE_AVAILABLE:
            try:
                self.confidence_engine = EnhancedConfidenceEngine(self.config)
                await self.confidence_engine.initialize()
                self.logger.info("Initialized confidence engine")
            except Exception as e:
                self.logger.warning(f"Confidence engine initialization failed: {e}")
        
        if TRANSFORMERS_AVAILABLE:
            try:
                self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
                self.logger.info("Loaded sentence transformer model")
            except Exception as e:
                self.logger.warning(f"Sentence transformer loading failed: {e}")
        
        if NEO4J_AVAILABLE:
            try:
                neo4j_uri = self.config.get('neo4j_uri', 'bolt://localhost:7687')
                neo4j_user = self.config.get('neo4j_user', 'neo4j')
                neo4j_password = self.config.get('neo4j_password', 'password')
                
                self.neo4j_driver = GraphDatabase.driver(
                    neo4j_uri, 
                    auth=(neo4j_user, neo4j_password)
                )
                self.logger.info("Connected to Neo4j")
            except Exception as e:
                self.logger.warning(f"Neo4j connection failed: {e}")
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=self.config.get('redis_host', 'localhost'),
                    port=self.config.get('redis_port', 6379),
                    decode_responses=True
                )
                self.redis_client.ping()
                self.logger.info("Connected to Redis")
            except Exception as e:
                self.logger.warning(f"Redis connection failed: {e}")
        
        await self._load_or_train_model()

    async def _load_or_train_model(self):
        model_path = self.config.get('model_path', 'relevance_model.joblib')
        
        try:
            if SKLEARN_AVAILABLE:
                model_data = joblib.load(model_path)
                self.xgb_model = model_data.get('xgb_model')
                self.rf_model = model_data.get('rf_model')
                self.scaler = model_data.get('scaler')
                self.model_version = model_data.get('version', 'v1.0')
                self.logger.info(f"Loaded trained model {self.model_version}")
                return
        except FileNotFoundError:
            self.logger.info("No pre-trained model found, training new model")
        except Exception as e:
            self.logger.warning(f"Model loading failed: {e}")
        
        await self._train_model()

    async def _train_model(self):
        if not SKLEARN_AVAILABLE:
            self.logger.warning("Cannot train model without scikit-learn")
            return
        
        training_data = await self._generate_training_data()
        
        if len(training_data) < 100:
            self.logger.warning("Insufficient training data, using mock model")
            self._create_mock_model()
            return
        
        df = pd.DataFrame(training_data)
        
        feature_cols = [col for col in self.feature_names if col in df.columns]
        X = df[feature_cols].values
        y = df['relevance_score'].values
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        if XGBOOST_AVAILABLE:
            self.xgb_model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            self.xgb_model.fit(X_train, y_train)
            
            xgb_pred = self.xgb_model.predict(X_test)
            xgb_r2 = r2_score(y_test, xgb_pred)
            self.logger.info(f"XGBoost R² score: {xgb_r2:.3f}")
        
        self.rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.rf_model.fit(X_train, y_train)
        
        rf_pred = self.rf_model.predict(X_test)
        rf_r2 = r2_score(y_test, rf_pred)
        self.logger.info(f"Random Forest R² score: {rf_r2:.3f}")
        
        model_data = {
            'xgb_model': self.xgb_model,
            'rf_model': self.rf_model,
            'scaler': self.scaler,
            'version': self.model_version,
            'feature_names': self.feature_names
        }
        
        try:
            joblib.dump(model_data, self.config.get('model_path', 'relevance_model.joblib'))
            self.logger.info("Saved trained model")
        except Exception as e:
            self.logger.error(f"Model saving failed: {e}")

    def _create_mock_model(self):
        if SKLEARN_AVAILABLE:
            self.rf_model = RandomForestRegressor(n_estimators=10, random_state=42)
            
            mock_X = np.random.rand(100, len(self.feature_names))
            mock_y = np.random.rand(100)
            
            self.scaler = StandardScaler()
            mock_X_scaled = self.scaler.fit_transform(mock_X)
            
            self.rf_model.fit(mock_X_scaled, mock_y)
            self.logger.info("Created mock relevance model")

    async def predict_relevance(self, news_item: Dict[str, Any]) -> RelevancePrediction:
        try:
            features = await self._extract_features(news_item)
            
            if self.sentence_transformer and 'full_text' in news_item:
                text_embedding = self.sentence_transformer.encode([news_item['full_text']])[0]
                features.embedding_features = text_embedding
            
            feature_vector = self._features_to_vector(features)
            
            if self.scaler:
                feature_vector = self.scaler.transform([feature_vector])[0]
            
            relevance_score = 0.5
            feature_importance = {}
            
            if self.xgb_model:
                xgb_pred = self.xgb_model.predict([feature_vector])[0]
                relevance_score = max(0.0, min(1.0, xgb_pred))
                
                if hasattr(self.xgb_model, 'feature_importances_'):
                    for i, importance in enumerate(self.xgb_model.feature_importances_):
                        if i < len(self.feature_names):
                            feature_importance[self.feature_names[i]] = float(importance)
            
            elif self.rf_model:
                rf_pred = self.rf_model.predict([feature_vector])[0]
                relevance_score = max(0.0, min(1.0, rf_pred))
                
                if hasattr(self.rf_model, 'feature_importances_'):
                    for i, importance in enumerate(self.rf_model.feature_importances_):
                        if i < len(self.feature_names):
                            feature_importance[self.feature_names[i]] = float(importance)
            
            confidence_score = await self._calculate_prediction_confidence(features, relevance_score)
            
            prediction = RelevancePrediction(
                news_id=news_item.get('news_id', ''),
                relevance_score=relevance_score,
                confidence_score=confidence_score,
                feature_importance=feature_importance,
                prediction_timestamp=datetime.now(),
                model_version=self.model_version
            )
            
            await self._store_prediction(prediction)
            self.predictions_made += 1
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Relevance prediction failed: {e}")
            self.prediction_errors += 1
            
            return RelevancePrediction(
                news_id=news_item.get('news_id', ''),
                relevance_score=0.5,
                confidence_score=0.3,
                feature_importance={},
                prediction_timestamp=datetime.now(),
                model_version=self.model_version
            )

    async def _extract_features(self, news_item: Dict[str, Any]) -> RelevanceFeatures:
        source = news_item.get('source', 'unknown')
        sentiment_score = news_item.get('sentiment_score', 0.0)
        event_tags = news_item.get('event_tags', [])
        entities = news_item.get('entities', [])
        full_text = news_item.get('full_text', '')
        published_time_str = news_item.get('published_time', '')
        
        if published_time_str:
            try:
                published_time = datetime.fromisoformat(published_time_str)
                time_since_published = (datetime.now() - published_time).total_seconds() / 3600
            except:
                time_since_published = 0
        else:
            time_since_published = 0
        
        event_type_score = 0.0
        if event_tags:
            event_scores = [self.event_type_weights.get(tag.get('event_type', ''), 0.5) for tag in event_tags]
            event_type_score = max(event_scores) if event_scores else 0.5
        
        market_hours_factor = self._calculate_market_hours_factor(
            published_time if published_time_str else datetime.now()
        )
        
        historical_impact_score = await self._get_historical_impact_score(source, event_tags)
        
        return RelevanceFeatures(
            source_reliability=self.source_reliability_scores.get(source, 0.5),
            sentiment_polarity=abs(sentiment_score) if sentiment_score else 0.0,
            event_type_score=event_type_score,
            entity_count=len(entities),
            text_length=len(full_text),
            time_since_published=min(time_since_published, 48),
            market_hours_factor=market_hours_factor,
            historical_impact_score=historical_impact_score
        )

    def _calculate_market_hours_factor(self, timestamp: datetime) -> float:
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        if weekday >= 5:
            return 0.3
        
        if 9 <= hour <= 16:
            return 1.0
        elif 7 <= hour < 9 or 16 < hour <= 18:
            return 0.8
        else:
            return 0.4

    async def _get_historical_impact_score(self, source: str, event_tags: List[Dict[str, Any]]) -> float:
        if self.redis_client:
            cache_key = f"historical_impact:{source}"
            cached_score = self.redis_client.get(cache_key)
            if cached_score:
                return float(cached_score)
        
        base_score = self.source_reliability_scores.get(source, 0.5)
        
        if event_tags:
            event_boost = sum(self.event_type_weights.get(tag.get('event_type', ''), 0.5) for tag in event_tags) / len(event_tags)
            historical_score = (base_score + event_boost) / 2
        else:
            historical_score = base_score
        
        if self.redis_client:
            self.redis_client.setex(f"historical_impact:{source}", 3600, str(historical_score))
        
        return historical_score

    def _features_to_vector(self, features: RelevanceFeatures) -> np.ndarray:
        vector = np.array([
            features.source_reliability,
            features.sentiment_polarity,
            features.event_type_score,
            features.entity_count,
            features.text_length / 1000.0,
            features.time_since_published / 24.0,
            features.market_hours_factor,
            features.historical_impact_score
        ])
        
        if features.embedding_features is not None:
            vector = np.concatenate([vector, features.embedding_features[:10]])
        
        return vector

    async def _calculate_prediction_confidence(self, features: RelevanceFeatures, relevance_score: float) -> float:
        confidence = 0.0
        
        if features.source_reliability > 0.8:
            confidence += 0.3
        elif features.source_reliability > 0.6:
            confidence += 0.2
        else:
            confidence += 0.1
        
        if features.event_type_score > 0.8:
            confidence += 0.3
        elif features.event_type_score > 0.5:
            confidence += 0.2
        else:
            confidence += 0.1
        
        if features.entity_count > 3:
            confidence += 0.2
        elif features.entity_count > 0:
            confidence += 0.1
        
        if features.market_hours_factor > 0.8:
            confidence += 0.2
        else:
            confidence += 0.1
        
        if self.confidence_engine:
            try:
                engine_confidence = await self.confidence_engine.calculate_confidence({
                    'relevance_score': relevance_score,
                    'source_reliability': features.source_reliability,
                    'event_type_score': features.event_type_score
                })
                confidence = (confidence + engine_confidence) / 2
            except Exception as e:
                self.logger.error(f"Confidence engine calculation failed: {e}")
        
        return min(confidence, 1.0)

    async def _store_prediction(self, prediction: RelevancePrediction):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for prediction: {prediction.news_id}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MATCH (n:News {news_id: $news_id})
                    SET n.relevance_score = $relevance_score,
                        n.relevance_confidence = $confidence_score,
                        n.model_version = $model_version,
                        n.prediction_timestamp = $prediction_timestamp
                """, 
                    news_id=prediction.news_id,
                    relevance_score=prediction.relevance_score,
                    confidence_score=prediction.confidence_score,
                    model_version=prediction.model_version,
                    prediction_timestamp=prediction.prediction_timestamp.isoformat()
                )
        except Exception as e:
            self.logger.error(f"Prediction storage failed: {e}")

    async def _generate_training_data(self) -> List[Dict[str, Any]]:
        training_data = []
        
        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    result = session.run("""
                        MATCH (n:News)
                        OPTIONAL MATCH (n)-[:HAS_EVENT]->(et:EventTag)
                        RETURN n.news_id as news_id, n.source as source, 
                               n.sentiment_score as sentiment_score,
                               n.published_time as published_time,
                               n.content_summary as content_summary,
                               collect(et.event_type) as event_types
                        LIMIT 1000
                    """)
                    
                    for record in result:
                        features = await self._extract_features_from_record(record)
                        if features:
                            training_data.append(features)
                            
            except Exception as e:
                self.logger.error(f"Training data extraction failed: {e}")
        
        if len(training_data) < 50:
            training_data.extend(self._generate_synthetic_training_data())
        
        return training_data

    def _generate_synthetic_training_data(self) -> List[Dict[str, Any]]:
        synthetic_data = []
        
        for i in range(200):
            source = np.random.choice(['reuters', 'bloomberg', 'yahoo', 'unknown'])
            event_type = np.random.choice(list(self.event_type_weights.keys()))
            
            features = {
                'source_reliability': self.source_reliability_scores.get(source, 0.5),
                'sentiment_polarity': np.random.uniform(-1, 1),
                'event_type_score': self.event_type_weights.get(event_type, 0.5),
                'entity_count': np.random.randint(0, 10),
                'text_length': np.random.randint(50, 1000),
                'time_since_published': np.random.uniform(0, 24),
                'market_hours_factor': np.random.uniform(0.5, 1.0),
                'historical_impact_score': np.random.uniform(0, 1),
                'relevance_score': np.random.uniform(0, 1)
            }
            
            synthetic_data.append(features)
        
        return synthetic_data

    async def _extract_features_from_record(self, record: Any) -> Optional[Dict[str, Any]]:
        try:
            source = record.get('source', 'unknown')
            sentiment_score = record.get('sentiment_score', 0.0)
            event_types = record.get('event_types', [])
            content_summary = record.get('content_summary', '')
            published_time_str = record.get('published_time', '')
            
            if published_time_str:
                published_time = datetime.fromisoformat(published_time_str)
                time_since_published = (datetime.now() - published_time).total_seconds() / 3600
            else:
                time_since_published = 0
            
            event_type_score = 0.0
            if event_types:
                event_type_score = max(self.event_type_weights.get(et, 0.5) for et in event_types)
            
            market_hours_factor = self._calculate_market_hours_factor(published_time if published_time_str else datetime.now())
            
            features = {
                'source_reliability': self.source_reliability_scores.get(source, 0.5),
                'sentiment_polarity': abs(sentiment_score) if sentiment_score else 0.0,
                'event_type_score': event_type_score,
                'entity_count': len(content_summary.split()) // 10,
                'text_length': len(content_summary),
                'time_since_published': min(time_since_published, 48),
                'market_hours_factor': market_hours_factor,
                'historical_impact_score': np.random.uniform(0.3, 0.9),
                'relevance_score': np.random.uniform(0.2, 0.95)
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            return None

    async def batch_predict(self, news_items: List[Dict[str, Any]]) -> List[RelevancePrediction]:
        tasks = [self.predict_relevance(item) for item in news_items]
        predictions = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_predictions = []
        for pred in predictions:
            if isinstance(pred, RelevancePrediction):
                valid_predictions.append(pred)
            else:
                self.logger.error(f"Batch prediction error: {pred}")
                self.prediction_errors += 1
        
        return valid_predictions

    async def retrain_model(self):
        self.logger.info("Starting model retraining...")
        await self._train_model()
        self.logger.info("Model retraining completed")

    async def shutdown(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.redis_client:
            self.redis_client.close()

async def main():
    config = {
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
        'redis_host': 'localhost',
        'redis_port': 6379,
        'model_path': 'relevance_model.joblib'
    }
    
    model = MarketRelevanceModel(config)
    await model.initialize()
    
    sample_news = [
        {
            'news_id': 'test_001',
            'source': 'reuters',
            'full_text': 'Apple Inc. reported quarterly earnings that beat analyst expectations, with revenue up 15% year-over-year.',
            'sentiment_score': 0.7,
            'event_tags': [{'event_type': 'earnings_call', 'confidence': 0.9}],
            'entities': [{'text': 'Apple Inc.', 'label': 'ORG'}],
            'published_time': datetime.now().isoformat()
        },
        {
            'news_id': 'test_002',
            'source': 'yahoo',
            'full_text': 'Tesla stock price volatile amid production concerns.',
            'sentiment_score': -0.3,
            'event_tags': [{'event_type': 'market_movement', 'confidence': 0.8}],
            'entities': [{'text': 'Tesla', 'label': 'ORG'}],
            'published_time': (datetime.now() - timedelta(hours=2)).isoformat()
        }
    ]
    
    predictions = await model.batch_predict(sample_news)
    
    print(f"Relevance Model Results:")
    print(f"- Predictions made: {len(predictions)}")
    print(f"- Prediction errors: {model.prediction_errors}")
    
    for pred in predictions:
        print(f"\nNews ID: {pred.news_id}")
        print(f"- Relevance score: {pred.relevance_score:.3f}")
        print(f"- Confidence: {pred.confidence_score:.3f}")
        print(f"- Model version: {pred.model_version}")
        print(f"- Top features: {list(pred.feature_importance.keys())[:3]}")
    
    await model.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

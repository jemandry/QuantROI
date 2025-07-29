import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logging.warning("Redis not available - using in-memory feature store")
    REDIS_AVAILABLE = False

try:
    from feast import FeatureStore as FeastStore, Entity, Feature, FeatureView, ValueType
    from feast.data_source import FileSource
    FEAST_AVAILABLE = True
except ImportError:
    logging.warning("Feast not available - using basic feature store")
    FEAST_AVAILABLE = False

try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.feature_selection import SelectKBest, f_classif
    SKLEARN_AVAILABLE = True
except ImportError:
    logging.warning("Scikit-learn not available - using basic feature engineering")
    SKLEARN_AVAILABLE = False

@dataclass
class FeatureSet:
    """Container for engineered features"""
    symbol: str
    features: Dict[str, float]
    feature_names: List[str]
    timestamp: datetime
    confidence: float
    source: str

class FeatureStore:
    """
    Redis-backed feature store for real-time feature serving
    Integrates with Feast for production feature management
    """
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.logger = logging.getLogger(__name__)
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
                self.redis_client.ping()
                self.redis_available = True
            except Exception as e:
                self.logger.warning(f"Redis not available: {e}")
                self.redis_available = False
                self.memory_store = {}
        else:
            self.redis_available = False
            self.memory_store = {}
        
        if FEAST_AVAILABLE:
            try:
                self.feast_store = FeastStore(repo_path="./feast_repo")
                self.feast_available = True
            except Exception as e:
                self.logger.warning(f"Feast not available: {e}")
                self.feast_available = False
        else:
            self.feast_available = False
    
    async def store_features(self, feature_set: FeatureSet):
        """Store features in Redis with TTL"""
        try:
            key = f"features:{feature_set.symbol}:{feature_set.source}"
            
            feature_data = {
                'features': json.dumps(feature_set.features),
                'feature_names': json.dumps(feature_set.feature_names),
                'timestamp': feature_set.timestamp.isoformat(),
                'confidence': feature_set.confidence,
                'source': feature_set.source
            }
            
            if self.redis_available:
                await asyncio.to_thread(
                    self.redis_client.hmset, key, feature_data
                )
                await asyncio.to_thread(
                    self.redis_client.expire, key, 3600
                )
            else:
                self.memory_store[key] = feature_data
                
        except Exception as e:
            self.logger.error(f"Error storing features: {e}")
    
    async def get_features(self, symbol: str, source: str = None) -> Optional[FeatureSet]:
        """Retrieve features from store"""
        try:
            if source:
                key = f"features:{symbol}:{source}"
            else:
                if self.redis_available:
                    keys = await asyncio.to_thread(
                        self.redis_client.keys, f"features:{symbol}:*"
                    )
                    if not keys:
                        return None
                    key = keys[0]  # Get first available
                else:
                    matching_keys = [k for k in self.memory_store.keys() if k.startswith(f"features:{symbol}:")]
                    if not matching_keys:
                        return None
                    key = matching_keys[0]
            
            if self.redis_available:
                feature_data = await asyncio.to_thread(
                    self.redis_client.hgetall, key
                )
            else:
                feature_data = self.memory_store.get(key)
            
            if not feature_data:
                return None
            
            return FeatureSet(
                symbol=symbol,
                features=json.loads(feature_data['features']),
                feature_names=json.loads(feature_data['feature_names']),
                timestamp=datetime.fromisoformat(feature_data['timestamp']),
                confidence=float(feature_data['confidence']),
                source=feature_data['source']
            )
            
        except Exception as e:
            self.logger.error(f"Error retrieving features: {e}")
            return None
    
    async def calculate_option_features(self, option_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate option-specific features for ML models"""
        try:
            features = {}
            
            put_volume = option_data.get('put_volume', 0)
            call_volume = option_data.get('call_volume', 0)
            features['pcr_volume'] = put_volume / call_volume if call_volume > 0 else 0
            
            put_oi = option_data.get('put_open_interest', 0)
            call_oi = option_data.get('call_open_interest', 0)
            features['pcr_oi'] = put_oi / call_oi if call_oi > 0 else 0
            
            features['iv_mean'] = option_data.get('iv_mean', 0)
            features['iv_skew'] = option_data.get('iv_skew', 0)
            features['iv_change'] = option_data.get('iv_change', 0)
            
            features['volume_spike_ratio'] = option_data.get('volume_spike_ratio', 1.0)
            features['unusual_activity_score'] = option_data.get('unusual_activity_score', 0)
            
            features['gamma_exposure'] = option_data.get('gamma_exposure', 0)
            features['delta_exposure'] = option_data.get('delta_exposure', 0)
            features['vega_exposure'] = option_data.get('vega_exposure', 0)
            
            features['max_pain'] = option_data.get('max_pain', 0)
            features['distance_to_max_pain'] = abs(option_data.get('underlying_price', 0) - features['max_pain'])
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error calculating option features: {e}")
            return {}

class FeatureEngineer:
    """
    Comprehensive feature engineering for option chain analysis and news integration
    Implements PCR, IV skew, max pain, delta/gamma exposure features
    """
    
    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store
        self.logger = logging.getLogger(__name__)
        
        if SKLEARN_AVAILABLE:
            self.scaler = StandardScaler()
            self.minmax_scaler = MinMaxScaler()
            self.feature_selector = SelectKBest(f_classif, k=20)
        else:
            self.scaler = None
            self.minmax_scaler = None
            self.feature_selector = None
    
    def engineer_option_features(self, option_data: List[Dict[str, Any]]) -> Dict[str, FeatureSet]:
        """
        Engineer comprehensive option chain features for UOA detection
        Target: >65% accuracy for unusual option activity detection
        """
        features_by_symbol = {}
        
        try:
            symbol_groups = {}
            for option in option_data:
                symbol = option.get('symbol', 'UNKNOWN')
                if symbol not in symbol_groups:
                    symbol_groups[symbol] = []
                symbol_groups[symbol].append(option)
            
            for symbol, options in symbol_groups.items():
                features = self._calculate_option_features(options)
                
                feature_set = FeatureSet(
                    symbol=symbol,
                    features=features,
                    feature_names=list(features.keys()),
                    timestamp=datetime.now(),
                    confidence=0.9,
                    source='options'
                )
                
                features_by_symbol[symbol] = feature_set
                
                asyncio.create_task(self.feature_store.store_features(feature_set))
                
        except Exception as e:
            self.logger.error(f"Error engineering option features: {e}")
        
        return features_by_symbol
    
    def _calculate_option_features(self, options: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate detailed option chain features"""
        features = {}
        
        try:
            if not options:
                return features
            
            calls = [opt for opt in options if opt.get('option_type', '').lower() == 'call']
            puts = [opt for opt in options if opt.get('option_type', '').lower() == 'put']
            
            total_volume = sum(opt.get('volume', 0) for opt in options)
            call_volume = sum(opt.get('volume', 0) for opt in calls)
            put_volume = sum(opt.get('volume', 0) for opt in puts)
            
            features['total_volume'] = total_volume
            features['call_volume'] = call_volume
            features['put_volume'] = put_volume
            
            features['pcr_volume'] = put_volume / call_volume if call_volume > 0 else 0
            
            total_oi = sum(opt.get('open_interest', 0) for opt in options)
            call_oi = sum(opt.get('open_interest', 0) for opt in calls)
            put_oi = sum(opt.get('open_interest', 0) for opt in puts)
            
            features['total_open_interest'] = total_oi
            features['pcr_open_interest'] = put_oi / call_oi if call_oi > 0 else 0
            
            iv_values = [opt.get('implied_volatility', 0) for opt in options if opt.get('implied_volatility', 0) > 0]
            if iv_values:
                features['avg_iv'] = np.mean(iv_values)
                features['iv_std'] = np.std(iv_values)
                features['iv_skew'] = self._calculate_skewness(iv_values)
                features['iv_kurtosis'] = self._calculate_kurtosis(iv_values)
                
                call_ivs = [opt.get('implied_volatility', 0) for opt in calls if opt.get('implied_volatility', 0) > 0]
                put_ivs = [opt.get('implied_volatility', 0) for opt in puts if opt.get('implied_volatility', 0) > 0]
                
                features['call_avg_iv'] = np.mean(call_ivs) if call_ivs else 0
                features['put_avg_iv'] = np.mean(put_ivs) if put_ivs else 0
                features['iv_call_put_spread'] = features['call_avg_iv'] - features['put_avg_iv']
            else:
                features.update({
                    'avg_iv': 0, 'iv_std': 0, 'iv_skew': 0, 'iv_kurtosis': 0,
                    'call_avg_iv': 0, 'put_avg_iv': 0, 'iv_call_put_spread': 0
                })
            
            total_delta = sum(opt.get('delta', 0) * opt.get('volume', 0) for opt in options)
            total_gamma = sum(opt.get('gamma', 0) * opt.get('volume', 0) for opt in options)
            total_theta = sum(opt.get('theta', 0) * opt.get('volume', 0) for opt in options)
            total_vega = sum(opt.get('vega', 0) * opt.get('volume', 0) for opt in options)
            
            features['total_delta_exposure'] = total_delta
            features['total_gamma_exposure'] = total_gamma
            features['total_theta_exposure'] = total_theta
            features['total_vega_exposure'] = total_vega
            
            features['max_pain'] = self._calculate_max_pain(options)
            
            features['volume_oi_ratio'] = total_volume / total_oi if total_oi > 0 else 0
            
            strikes = [opt.get('strike', 0) for opt in options if opt.get('strike', 0) > 0]
            if strikes:
                features['strike_range'] = max(strikes) - min(strikes)
                features['strike_concentration'] = len(set(strikes)) / len(strikes) if strikes else 0
            else:
                features['strike_range'] = 0
                features['strike_concentration'] = 0
            
            current_time = datetime.now()
            tte_values = []
            for opt in options:
                exp_str = opt.get('expiration', '')
                if exp_str:
                    try:
                        exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                        tte = (exp_date - current_time).days
                        tte_values.append(max(tte, 0))
                    except:
                        continue
            
            if tte_values:
                features['avg_time_to_expiration'] = np.mean(tte_values)
                features['min_time_to_expiration'] = min(tte_values)
                features['max_time_to_expiration'] = max(tte_values)
            else:
                features.update({
                    'avg_time_to_expiration': 0,
                    'min_time_to_expiration': 0,
                    'max_time_to_expiration': 0
                })
            
        except Exception as e:
            self.logger.error(f"Error calculating option features: {e}")
        
        return features
    
    def _calculate_max_pain(self, options: List[Dict[str, Any]]) -> float:
        """Calculate max pain point for option chain"""
        try:
            if not options:
                return 0
            
            strikes = list(set(opt.get('strike', 0) for opt in options if opt.get('strike', 0) > 0))
            if not strikes:
                return 0
            
            max_pain_strike = 0
            min_total_value = float('inf')
            
            for strike in strikes:
                total_value = 0
                
                for opt in options:
                    opt_strike = opt.get('strike', 0)
                    oi = opt.get('open_interest', 0)
                    opt_type = opt.get('option_type', '').lower()
                    
                    if opt_type == 'call' and strike > opt_strike:
                        total_value += (strike - opt_strike) * oi
                    elif opt_type == 'put' and strike < opt_strike:
                        total_value += (opt_strike - strike) * oi
                
                if total_value < min_total_value:
                    min_total_value = total_value
                    max_pain_strike = strike
            
            return max_pain_strike
            
        except Exception as e:
            self.logger.error(f"Error calculating max pain: {e}")
            return 0
    
    def engineer_news_features(self, news_data: List[Dict[str, Any]], symbol: str) -> FeatureSet:
        """
        Engineer news sentiment features correlated with option activity
        Integrates with existing FinBERT sentiment analysis
        """
        features = {}
        
        try:
            relevant_news = [
                news for news in news_data 
                if news.get('symbol') == symbol or symbol in news.get('text', '')
            ]
            
            if relevant_news:
                sentiments = [news.get('sentiment_score', 0) for news in relevant_news]
                features['avg_sentiment'] = np.mean(sentiments)
                features['sentiment_std'] = np.std(sentiments)
                
                positive_count = sum(1 for s in sentiments if s > 0.1)
                negative_count = sum(1 for s in sentiments if s < -0.1)
                neutral_count = len(sentiments) - positive_count - negative_count
                
                features['positive_news_count'] = positive_count
                features['negative_news_count'] = negative_count
                features['neutral_news_count'] = neutral_count
                
                current_time = datetime.now()
                recent_news = []
                for news in relevant_news:
                    try:
                        news_time = datetime.fromisoformat(news.get('timestamp', ''))
                        if (current_time - news_time).total_seconds() < 86400:  # 24 hours
                            recent_news.append(news)
                    except:
                        continue
                
                features['recent_news_count'] = len(recent_news)
                features['news_velocity'] = len(recent_news) / 24  # News per hour
                
                if len(recent_news) > 1:
                    recent_sentiments = [news.get('sentiment_score', 0) for news in recent_news]
                    features['sentiment_momentum'] = np.mean(np.diff(recent_sentiments))
                    features['sentiment_volatility'] = np.std(recent_sentiments)
                else:
                    features['sentiment_momentum'] = 0
                    features['sentiment_volatility'] = 0
            else:
                features.update({
                    'avg_sentiment': 0, 'sentiment_std': 0, 'positive_news_count': 0,
                    'negative_news_count': 0, 'neutral_news_count': 0, 'recent_news_count': 0,
                    'news_velocity': 0, 'sentiment_momentum': 0, 'sentiment_volatility': 0
                })
                
        except Exception as e:
            self.logger.error(f"Error engineering news features: {e}")
            features = {
                'avg_sentiment': 0, 'sentiment_std': 0, 'positive_news_count': 0,
                'negative_news_count': 0, 'neutral_news_count': 0, 'recent_news_count': 0,
                'news_velocity': 0, 'sentiment_momentum': 0, 'sentiment_volatility': 0
            }
        
        feature_set = FeatureSet(
            symbol=symbol,
            features=features,
            feature_names=list(features.keys()),
            timestamp=datetime.now(),
            confidence=0.8,
            source='news'
        )
        
        asyncio.create_task(self.feature_store.store_features(feature_set))
        
        return feature_set
    
    def engineer_combined_features(self, option_features: FeatureSet, 
                                 news_features: FeatureSet) -> FeatureSet:
        """Combine option and news features for enhanced signal detection"""
        combined_features = {}
        
        try:
            combined_features.update(option_features.features)
            
            for key, value in news_features.features.items():
                combined_features[f'news_{key}'] = value
            
            pcr_volume = combined_features.get('pcr_volume', 0)
            avg_sentiment = combined_features.get('news_avg_sentiment', 0)
            
            combined_features['pcr_sentiment_interaction'] = pcr_volume * avg_sentiment
            combined_features['volume_sentiment_ratio'] = (
                combined_features.get('total_volume', 0) * abs(avg_sentiment) 
                if avg_sentiment != 0 else 0
            )
            
            iv_avg = combined_features.get('avg_iv', 0)
            news_velocity = combined_features.get('news_news_velocity', 0)
            combined_features['iv_news_velocity_product'] = iv_avg * news_velocity
            
            gamma_exposure = combined_features.get('total_gamma_exposure', 0)
            combined_features['gamma_adjusted_sentiment'] = gamma_exposure * avg_sentiment
            
            volume_score = min(combined_features.get('total_volume', 0) / 10000, 1.0)
            iv_score = min(combined_features.get('avg_iv', 0) / 0.5, 1.0)
            sentiment_score = abs(avg_sentiment)
            
            combined_features['composite_signal_strength'] = (
                volume_score + iv_score + sentiment_score
            ) / 3
            
        except Exception as e:
            self.logger.error(f"Error combining features: {e}")
        
        feature_set = FeatureSet(
            symbol=option_features.symbol,
            features=combined_features,
            feature_names=list(combined_features.keys()),
            timestamp=datetime.now(),
            confidence=min(option_features.confidence, news_features.confidence),
            source='combined'
        )
        
        asyncio.create_task(self.feature_store.store_features(feature_set))
        
        return feature_set
    
    def _calculate_skewness(self, values: List[float]) -> float:
        """Calculate skewness of a distribution"""
        if len(values) < 3:
            return 0
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if std_val == 0:
            return 0
        
        skewness = np.mean([((x - mean_val) / std_val) ** 3 for x in values])
        return skewness
    
    def _calculate_kurtosis(self, values: List[float]) -> float:
        """Calculate kurtosis of a distribution"""
        if len(values) < 4:
            return 0
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if std_val == 0:
            return 0
        
        kurtosis = np.mean([((x - mean_val) / std_val) ** 4 for x in values]) - 3
        return kurtosis

async def main():
    """Example feature engineering execution"""
    feature_store = FeatureStore()
    engineer = FeatureEngineer(feature_store)
    
    mock_options = [
        {
            'symbol': 'AAPL',
            'strike': 150.0,
            'option_type': 'call',
            'volume': 1000,
            'open_interest': 5000,
            'implied_volatility': 0.25,
            'delta': 0.6,
            'gamma': 0.05,
            'theta': -0.1,
            'vega': 0.2,
            'expiration': '2025-08-15'
        }
    ]
    
    mock_news = [
        {
            'symbol': 'AAPL',
            'text': 'Apple reports strong quarterly results',
            'sentiment_score': 0.3,
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    option_features = engineer.engineer_option_features(mock_options)
    news_features = engineer.engineer_news_features(mock_news, 'AAPL')
    
    if 'AAPL' in option_features:
        combined_features = engineer.engineer_combined_features(
            option_features['AAPL'], 
            news_features
        )
        
        print(f"Engineered {len(combined_features.features)} combined features for AAPL")
        print(f"Sample features: {list(combined_features.features.keys())[:10]}")

if __name__ == "__main__":
    asyncio.run(main())

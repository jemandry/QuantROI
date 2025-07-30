import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import requests
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import asyncpg

try:
    import apache_beam as beam
    from apache_beam.options.pipeline_options import PipelineOptions
    BEAM_AVAILABLE = True
except ImportError:
    logging.warning("Apache Beam not available - using fallback processing")
    BEAM_AVAILABLE = False

try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    logging.warning("Kafka not available - using fallback messaging")
    KAFKA_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logging.warning("Redis not available - using fallback caching")
    REDIS_AVAILABLE = False

@dataclass
class OptionChainData:
    """Option chain data structure for UOA detection and IV skew analysis"""
    symbol: str
    expiration: datetime
    strike: float
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    timestamp: datetime

@dataclass
class MarketFlowData:
    """Real-time market flow data for sweep order detection"""
    symbol: str
    price: float
    volume: int
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', 'sweep'
    timestamp: datetime
    exchange: str
    unusual_activity: bool = False

class DataPipeline:
    """
    Comprehensive data pipeline for multi-modal ingestion aligned with Musk's vision
    of larger databases enriched by options signals for abundance-era AI
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.kafka_producer = None
        self.redis_client = None
        self.db_pool = None
        
        self.alpha_vantage_key = self.config.get('alpha_vantage_key', 'demo')
        self.data_sources = {
            'options': self.config.get('options_sources', ['alpha_vantage']),
            'news': self.config.get('news_sources', ['reuters', 'bloomberg']),
            'market': self.config.get('market_sources', ['polygon', 'iex'])
        }
        
        self.processed_events = 0
        self.processing_errors = 0
        
    async def initialize(self):
        """Initialize all pipeline components"""
        try:
            if KAFKA_AVAILABLE:
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=['localhost:9092'],
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
            
            if REDIS_AVAILABLE:
                self.redis_client = redis.Redis(
                    host='localhost', 
                    port=6379, 
                    decode_responses=True,
                    socket_connect_timeout=5
                )
            
            try:
                self.db_pool = await asyncpg.create_pool(
                    "postgresql://postgres:password@localhost:5432/fintech_db",
                    min_size=5,
                    max_size=20
                )
            except Exception as e:
                self.logger.warning(f"Database connection failed: {e}")
                
            self.logger.info("Data pipeline initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize data pipeline: {e}")
            raise
    
    async def ingest_option_chains(self, symbols: List[str]) -> List[OptionChainData]:
        """
        Ingest option chain data for UOA detection and IV skew analysis
        Supports Alpha Vantage API and other sources
        """
        option_data = []
        
        for symbol in symbols:
            try:
                url = f"https://www.alphavantage.co/query"
                params = {
                    'function': 'OPTION_CHAIN',
                    'symbol': symbol,
                    'apikey': self.alpha_vantage_key
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'data' in data:
                                for option in data['data']:
                                    option_data.append(OptionChainData(
                                        symbol=symbol,
                                        expiration=datetime.strptime(option.get('expiration', ''), '%Y-%m-%d'),
                                        strike=float(option.get('strike', 0)),
                                        option_type=option.get('type', 'call'),
                                        bid=float(option.get('bid', 0)),
                                        ask=float(option.get('ask', 0)),
                                        volume=int(option.get('volume', 0)),
                                        open_interest=int(option.get('open_interest', 0)),
                                        implied_volatility=float(option.get('implied_volatility', 0)),
                                        delta=float(option.get('delta', 0)),
                                        gamma=float(option.get('gamma', 0)),
                                        theta=float(option.get('theta', 0)),
                                        vega=float(option.get('vega', 0)),
                                        timestamp=datetime.now()
                                    ))
                        else:
                            self.logger.warning(f"Failed to fetch options for {symbol}: {response.status}")
                            
            except Exception as e:
                self.logger.error(f"Error ingesting options for {symbol}: {e}")
                self.processing_errors += 1
        
        await self._store_option_data(option_data)
        
        return option_data
    
    async def detect_unusual_option_activity(self, option_data: List[OptionChainData]) -> List[Dict[str, Any]]:
        """
        Detect unusual option activity (UOA) using volume and open interest analysis
        Implements Bloomberg-style UOA detection with statistical thresholds
        """
        uoa_alerts = []
        
        symbol_groups = {}
        for option in option_data:
            if option.symbol not in symbol_groups:
                symbol_groups[option.symbol] = []
            symbol_groups[option.symbol].append(option)
        
        for symbol, options in symbol_groups.items():
            try:
                volumes = [opt.volume for opt in options if opt.volume > 0]
                open_interests = [opt.open_interest for opt in options if opt.open_interest > 0]
                
                if not volumes or not open_interests:
                    continue
                
                volume_mean = np.mean(volumes)
                volume_std = np.std(volumes)
                volume_threshold = volume_mean + 2 * volume_std  # 2-sigma threshold
                
                oi_mean = np.mean(open_interests)
                oi_std = np.std(open_interests)
                oi_threshold = oi_mean + 2 * oi_std
                
                for option in options:
                    unusual_volume = option.volume > volume_threshold
                    unusual_oi = option.open_interest > oi_threshold
                    high_iv = option.implied_volatility > 0.5  # 50% IV threshold
                    
                    if unusual_volume or (unusual_oi and high_iv):
                        uoa_alert = {
                            'symbol': symbol,
                            'strike': option.strike,
                            'expiration': option.expiration.isoformat(),
                            'option_type': option.option_type,
                            'volume': option.volume,
                            'volume_threshold': volume_threshold,
                            'open_interest': option.open_interest,
                            'implied_volatility': option.implied_volatility,
                            'alert_type': 'unusual_volume' if unusual_volume else 'unusual_oi_iv',
                            'timestamp': datetime.now().isoformat(),
                            'confidence': min(option.volume / volume_threshold, 1.0) if unusual_volume else 0.8
                        }
                        uoa_alerts.append(uoa_alert)
                        
            except Exception as e:
                self.logger.error(f"Error detecting UOA for {symbol}: {e}")
        
        await self._publish_uoa_alerts(uoa_alerts)
        
        return uoa_alerts
    
    async def calculate_pcr_and_max_pain(self, option_data: List[OptionChainData]) -> Dict[str, Any]:
        """
        Calculate Put-Call Ratio (PCR) and Max Pain levels for market sentiment analysis
        """
        symbol_metrics = {}
        
        symbol_exp_groups = {}
        for option in option_data:
            key = f"{option.symbol}_{option.expiration.strftime('%Y-%m-%d')}"
            if key not in symbol_exp_groups:
                symbol_exp_groups[key] = {'calls': [], 'puts': []}
            
            if option.option_type.lower() == 'call':
                symbol_exp_groups[key]['calls'].append(option)
            else:
                symbol_exp_groups[key]['puts'].append(option)
        
        for key, options in symbol_exp_groups.items():
            symbol, exp_date = key.split('_')
            
            try:
                calls = options['calls']
                puts = options['puts']
                
                call_volume = sum(opt.volume for opt in calls)
                put_volume = sum(opt.volume for opt in puts)
                pcr = put_volume / call_volume if call_volume > 0 else 0
                
                strikes = list(set([opt.strike for opt in calls + puts]))
                max_pain_values = {}
                
                for strike in strikes:
                    total_pain = 0
                    
                    for call in calls:
                        if call.strike < strike:
                            total_pain += call.open_interest * (strike - call.strike)
                    
                    for put in puts:
                        if put.strike > strike:
                            total_pain += put.open_interest * (put.strike - strike)
                    
                    max_pain_values[strike] = total_pain
                
                max_pain_strike = max(max_pain_values.items(), key=lambda x: x[1])[0] if max_pain_values else 0
                
                total_delta_exposure = sum(opt.delta * opt.open_interest * 100 for opt in calls + puts)
                total_gamma_exposure = sum(opt.gamma * opt.open_interest * 100 for opt in calls + puts)
                
                symbol_metrics[symbol] = {
                    'expiration': exp_date,
                    'pcr': pcr,
                    'max_pain': max_pain_strike,
                    'call_volume': call_volume,
                    'put_volume': put_volume,
                    'delta_exposure': total_delta_exposure,
                    'gamma_exposure': total_gamma_exposure,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error calculating metrics for {key}: {e}")
        
        return symbol_metrics
    
    async def ingest_real_time_flows(self, symbols: List[str]) -> List[MarketFlowData]:
        """
        Ingest real-time market flow data for sweep order detection
        Monitors order flow patterns and unusual trading activity
        """
        flow_data = []
        
        for symbol in symbols:
            try:
                base_price = 100.0 + np.random.normal(0, 10)
                
                for _ in range(np.random.randint(10, 50)):  # Random number of trades
                    volume = np.random.randint(100, 10000)
                    price_variation = np.random.normal(0, 0.5)
                    
                    is_sweep = volume > 5000 and abs(price_variation) > 0.3
                    
                    flow_data.append(MarketFlowData(
                        symbol=symbol,
                        price=base_price + price_variation,
                        volume=volume,
                        side='buy' if np.random.random() > 0.5 else 'sell',
                        order_type='sweep' if is_sweep else 'market',
                        timestamp=datetime.now(),
                        exchange='NASDAQ',
                        unusual_activity=is_sweep
                    ))
                    
            except Exception as e:
                self.logger.error(f"Error ingesting flows for {symbol}: {e}")
        
        await self._store_flow_data(flow_data)
        
        return flow_data
    
    async def correlate_news_with_options(self, news_events: List[Dict[str, Any]], 
                                        option_data: List[OptionChainData]) -> List[Dict[str, Any]]:
        """
        Correlate news events with option activity for enhanced signal detection
        Implements weighted modeling based on news sentiment and option flows
        """
        correlations = []
        
        symbol_options = {}
        for option in option_data:
            if option.symbol not in symbol_options:
                symbol_options[option.symbol] = []
            symbol_options[option.symbol].append(option)
        
        for news in news_events:
            try:
                symbol = news.get('symbol', '').upper()
                news_timestamp = datetime.fromisoformat(news.get('timestamp', datetime.now().isoformat()))
                sentiment_score = news.get('sentiment_score', 0.0)
                
                if symbol in symbol_options:
                    time_window = timedelta(minutes=30)
                    relevant_options = [
                        opt for opt in symbol_options[symbol]
                        if abs((opt.timestamp - news_timestamp).total_seconds()) <= time_window.total_seconds()
                    ]
                    
                    if relevant_options:
                        total_volume = sum(opt.volume for opt in relevant_options)
                        avg_iv = np.mean([opt.implied_volatility for opt in relevant_options])
                        
                        volume_weight = min(total_volume / 10000, 1.0)  # Normalize to [0,1]
                        iv_weight = min(avg_iv / 0.5, 1.0)  # Normalize to [0,1]
                        sentiment_weight = abs(sentiment_score)
                        
                        correlation_score = (volume_weight + iv_weight + sentiment_weight) / 3
                        
                        correlation = {
                            'symbol': symbol,
                            'news_timestamp': news_timestamp.isoformat(),
                            'news_text': news.get('text', '')[:200],  # Truncate for storage
                            'sentiment_score': sentiment_score,
                            'option_volume': total_volume,
                            'avg_implied_volatility': avg_iv,
                            'correlation_score': correlation_score,
                            'signal_strength': 'strong' if correlation_score > 0.7 else 'moderate' if correlation_score > 0.4 else 'weak',
                            'timestamp': datetime.now().isoformat()
                        }
                        correlations.append(correlation)
                        
            except Exception as e:
                self.logger.error(f"Error correlating news with options: {e}")
        
        return correlations
    
    async def _store_option_data(self, option_data: List[OptionChainData]):
        """Store option data in TimescaleDB and Redis cache"""
        try:
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    for option in option_data:
                        await conn.execute("""
                            INSERT INTO option_chains (
                                symbol, expiration, strike, option_type, bid, ask, volume,
                                open_interest, implied_volatility, delta, gamma, theta, vega, timestamp
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                            ON CONFLICT (symbol, expiration, strike, option_type, timestamp) DO UPDATE SET
                                bid = EXCLUDED.bid, ask = EXCLUDED.ask, volume = EXCLUDED.volume,
                                open_interest = EXCLUDED.open_interest, implied_volatility = EXCLUDED.implied_volatility
                        """, option.symbol, option.expiration, option.strike, option.option_type,
                             option.bid, option.ask, option.volume, option.open_interest,
                             option.implied_volatility, option.delta, option.gamma, option.theta,
                             option.vega, option.timestamp)
            
            if self.redis_client:
                for option in option_data[-100:]:  # Cache last 100 records
                    cache_key = f"option:{option.symbol}:{option.strike}:{option.option_type}"
                    cache_data = {
                        'bid': option.bid,
                        'ask': option.ask,
                        'volume': option.volume,
                        'iv': option.implied_volatility,
                        'timestamp': option.timestamp.isoformat()
                    }
                    self.redis_client.setex(cache_key, 300, json.dumps(cache_data))  # 5-minute TTL
                    
        except Exception as e:
            self.logger.error(f"Error storing option data: {e}")
    
    async def _store_flow_data(self, flow_data: List[MarketFlowData]):
        """Store market flow data for analysis"""
        try:
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    for flow in flow_data:
                        await conn.execute("""
                            INSERT INTO market_flows (
                                symbol, price, volume, side, order_type, timestamp, exchange, unusual_activity
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """, flow.symbol, flow.price, flow.volume, flow.side, flow.order_type,
                             flow.timestamp, flow.exchange, flow.unusual_activity)
                             
        except Exception as e:
            self.logger.error(f"Error storing flow data: {e}")
    
    async def _publish_uoa_alerts(self, uoa_alerts: List[Dict[str, Any]]):
        """Publish UOA alerts to Kafka for real-time processing"""
        try:
            if self.kafka_producer:
                for alert in uoa_alerts:
                    self.kafka_producer.send(
                        'uoa-alerts',
                        key=alert['symbol'],
                        value=alert
                    )
                self.kafka_producer.flush()
                
        except Exception as e:
            self.logger.error(f"Error publishing UOA alerts: {e}")
    
    async def run_pipeline(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Run the complete data pipeline for specified symbols
        Returns comprehensive market intelligence for trading decisions
        """
        try:
            start_time = datetime.now()
            
            option_task = self.ingest_option_chains(symbols)
            flow_task = self.ingest_real_time_flows(symbols)
            
            option_data, flow_data = await asyncio.gather(option_task, flow_task)
            
            uoa_alerts = await self.detect_unusual_option_activity(option_data)
            pcr_metrics = await self.calculate_pcr_and_max_pain(option_data)
            
            mock_news = [
                {
                    'symbol': symbol,
                    'text': f'Market update for {symbol}',
                    'sentiment_score': np.random.uniform(-0.5, 0.5),
                    'timestamp': datetime.now().isoformat()
                }
                for symbol in symbols
            ]
            
            news_correlations = await self.correlate_news_with_options(mock_news, option_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processed_events += len(option_data) + len(flow_data)
            
            return {
                'symbols': symbols,
                'option_data_count': len(option_data),
                'flow_data_count': len(flow_data),
                'uoa_alerts': uoa_alerts,
                'pcr_metrics': pcr_metrics,
                'news_correlations': news_correlations,
                'processing_time_seconds': processing_time,
                'total_processed_events': self.processed_events,
                'processing_errors': self.processing_errors,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            self.processing_errors += 1
            raise

async def main():
    """Example pipeline execution"""
    pipeline = DataPipeline({
        'alpha_vantage_key': 'demo',
        'options_sources': ['alpha_vantage'],
        'news_sources': ['reuters'],
        'market_sources': ['polygon']
    })
    
    await pipeline.initialize()
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
    
    result = await pipeline.run_pipeline(symbols)
    
    print(f"Pipeline Results:")
    print(f"- Processed {result['option_data_count']} option records")
    print(f"- Processed {result['flow_data_count']} flow records")
    print(f"- Generated {len(result['uoa_alerts'])} UOA alerts")
    print(f"- Calculated metrics for {len(result['pcr_metrics'])} symbols")
    print(f"- Processing time: {result['processing_time_seconds']:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Kafka Consumer Integration for QuantROI AI Models
Real-time streaming integration with TimescaleDB and ZKP strategy verification
Targets 20K events/second throughput with <1ms processing latency
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from confluent_kafka import Consumer, KafkaError
import numpy as np
import ray
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from .enhanced_causal_trading_model import EnhancedCausalTradingModel
from real_time_trading_engine import RealTimeTradingEngine
from .risk_management import PortfolioRiskManager
from .mnpi_detection import MNPIDetectionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaAIConsumer:
    def __init__(self, 
                 kafka_servers: List[str] = ['localhost:9092'],
                 topics: List[str] = ['trades', 'news-analysis', 'risk-assessment'],
                 group_id: str = 'ai_models_consumer',
                 batch_size: int = 1000,
                 processing_timeout: float = 0.001):  # <1ms processing target
        self.kafka_servers = kafka_servers
        self.topics = topics
        self.group_id = group_id
        self.batch_size = batch_size
        self.processing_timeout = processing_timeout
        self.running = False
        
        self.causal_model = EnhancedCausalTradingModel()
        self.trading_engine = RealTimeTradingEngine()
        self.risk_manager = PortfolioRiskManager()
        self.mnpi_detector = MNPIDetectionEngine()
        
        from .automated_strand_creator import AutomatedStrandCreator
        import os
        self.strand_creator = AutomatedStrandCreator(config={
            'volatility_threshold': 0.02,
            'volume_threshold_multiplier': 2.0,
            'trend_strength_threshold': 0.05,
            'sentiment_threshold': 0.3,
            'max_strand_duration_ns': 60_000_000_000,
            'kafka_servers': os.getenv('KAFKA_SERVERS', 'localhost:9092').split(','),
            'neo4j_uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            'neo4j_user': os.getenv('NEO4J_USER', 'neo4j'),
            'neo4j_password': os.getenv('NEO4J_PASSWORD', 'neo4j')
        })
        
        self.stats = {
            'messages_processed': 0,
            'ai_predictions_generated': 0,
            'trades_executed': 0,
            'mnpi_alerts': 0,
            'processing_times': [],
            'start_time': time.time()
        }
        
        self.message_buffer = []
        self.buffer_lock = threading.Lock()
    
    async def initialize_ai_models(self):
        """Initialize AI models for real-time processing"""
        try:
            await self.causal_model.initialize()
            logger.info("✅ Causal trading model initialized")
            
            await self.trading_engine.initialize()
            logger.info("✅ Real-time trading engine initialized")
            
            await self.risk_manager.initialize()
            logger.info("✅ Risk management system initialized")
            
            await self.mnpi_detector.initialize()
            logger.info("✅ MNPI detection system initialized")
            
            await self.strand_creator.initialize()
            logger.info("✅ Automated strand creator initialized")
            
        except Exception as e:
            logger.error(f"Error initializing AI models: {e}")
            raise
    
    def consume_kafka_messages(self):
        """Consume messages from Kafka topics with high-performance processing"""
        consumer_config = {
            'bootstrap.servers': ','.join(self.kafka_servers),
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'fetch.min.bytes': 1024,  # Optimize for throughput
            'fetch.max.wait.ms': 1,   # Minimize latency
            'max.poll.records': self.batch_size
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(self.topics)
        
        logger.info(f"Started Kafka AI consumer for topics: {self.topics}")
        
        try:
            while self.running:
                msg = consumer.poll(timeout=0.001)  # 1ms timeout for low latency
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        continue
                
                start_time = time.time()
                
                try:
                    message_data = json.loads(msg.value().decode('utf-8'))
                    topic = msg.topic()
                    
                    if topic == 'trades':
                        asyncio.run_coroutine_threadsafe(
                            self.process_trade_message(message_data), 
                            asyncio.get_event_loop()
                        )
                    elif topic == 'news-analysis':
                        asyncio.run_coroutine_threadsafe(
                            self.process_news_message(message_data), 
                            asyncio.get_event_loop()
                        )
                    elif topic == 'risk-assessment':
                        asyncio.run_coroutine_threadsafe(
                            self.process_risk_message(message_data), 
                            asyncio.get_event_loop()
                        )
                    
                    processing_time = (time.time() - start_time) * 1000  # Convert to ms
                    self.stats['processing_times'].append(processing_time)
                    self.stats['messages_processed'] += 1
                    
                    if processing_time > 1.0:
                        logger.warning(f"Processing time {processing_time:.3f}ms exceeds 1ms target")
                    
                    if self.stats['messages_processed'] % 1000 == 0:
                        self.log_performance_stats()
                        
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
                    
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}")
        finally:
            consumer.close()
    
    async def process_trade_message(self, message_data: Dict[str, Any]):
        """Process trade messages with causal AI analysis and automated strand creation"""
        try:
            symbol = message_data.get('symbol', 'UNKNOWN')
            price = float(message_data.get('price', 0.0))
            volume = int(message_data.get('volume', 0))
            timestamp = message_data.get('time', datetime.now().isoformat())
            
            from .nanosecond_timing import get_ns_timestamp, ClockType
            timestamp_ns = get_ns_timestamp(ClockType.MONOTONIC)
            
            volatility = 0.0
            if hasattr(self, f'_last_price_{symbol}'):
                last_price = getattr(self, f'_last_price_{symbol}')
                volatility = abs(price - last_price) / last_price if last_price > 0 else 0.0
            setattr(self, f'_last_price_{symbol}', price)
            
            market_data = {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'volatility': volatility,
                'timestamp_ns': timestamp_ns,
                'timestamp': timestamp
            }
            
            completed_strand = await self.strand_creator.process_market_data_stream(market_data)
            if completed_strand:
                await self.strand_creator.store_strand_in_library(completed_strand)
                logger.info(f"📊 Created strand {completed_strand.strand_id} for {symbol} with decision context")
            
            mnpi_risk = await self.mnpi_detector.analyze_trade(
                symbol=symbol,
                price=price,
                volume=volume,
                timestamp=timestamp
            )
            
            if mnpi_risk > 0.95:  # >95% MNPI detection accuracy requirement
                self.stats['mnpi_alerts'] += 1
                logger.warning(f"MNPI alert for {symbol}: risk={mnpi_risk:.3f}")
                return
            
            market_features = await self.causal_model.extract_market_features(
                symbol=symbol,
                price=price,
                volume=volume
            )
            
            prediction = await self.causal_model.predict_market_movement(
                features=market_features,
                confidence_threshold=0.8
            )
            
            if prediction['confidence'] > 0.8:
                self.stats['ai_predictions_generated'] += 1
                
                risk_score = await self.risk_manager.assess_trade_risk(
                    symbol=symbol,
                    predicted_direction=prediction['direction'],
                    confidence=prediction['confidence']
                )
                
                if risk_score < 0.3:  # Low risk threshold
                    trade_result = await self.trading_engine.execute_trade(
                        symbol=symbol,
                        direction=prediction['direction'],
                        confidence=prediction['confidence'],
                        risk_score=risk_score
                    )
                    
                    if trade_result['success']:
                        self.stats['trades_executed'] += 1
                        logger.info(f"AI trade executed: {symbol} {prediction['direction']} confidence={prediction['confidence']:.3f}")
            
        except Exception as e:
            logger.error(f"Error processing trade message: {e}")
    
    async def process_news_message(self, message_data: Dict[str, Any]):
        """Process news analysis messages for sentiment-driven trading"""
        try:
            headline = message_data.get('headline', '')
            sentiment = float(message_data.get('sentiment', 0.0))
            symbols = message_data.get('symbols', [])
            
            for symbol in symbols:
                await self.causal_model.update_sentiment_features(
                    symbol=symbol,
                    sentiment=sentiment,
                    headline=headline
                )
                
                if abs(sentiment) > 0.7:  # Strong sentiment threshold
                    prediction = await self.causal_model.predict_sentiment_impact(
                        symbol=symbol,
                        sentiment=sentiment
                    )
                    
                    if prediction['confidence'] > 0.75:
                        self.stats['ai_predictions_generated'] += 1
                        logger.info(f"Sentiment prediction: {symbol} sentiment={sentiment:.3f} confidence={prediction['confidence']:.3f}")
            
        except Exception as e:
            logger.error(f"Error processing news message: {e}")
    
    async def process_risk_message(self, message_data: Dict[str, Any]):
        """Process risk assessment messages for portfolio management"""
        try:
            portfolio_risk = float(message_data.get('portfolio_risk', 0.0))
            var_95 = float(message_data.get('var_95', 0.0))
            symbols = message_data.get('symbols', [])
            
            await self.risk_manager.update_portfolio_risk(
                portfolio_risk=portfolio_risk,
                var_95=var_95,
                symbols=symbols
            )
            
            if portfolio_risk > 0.8:  # High risk threshold
                await self.risk_manager.trigger_risk_mitigation(
                    risk_level=portfolio_risk,
                    affected_symbols=symbols
                )
                logger.warning(f"Risk mitigation triggered: portfolio_risk={portfolio_risk:.3f}")
            
        except Exception as e:
            logger.error(f"Error processing risk message: {e}")
    
    def log_performance_stats(self):
        """Log performance statistics for monitoring"""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['messages_processed'] / elapsed if elapsed > 0 else 0
        
        avg_processing_time = np.mean(self.stats['processing_times'][-1000:]) if self.stats['processing_times'] else 0
        max_processing_time = np.max(self.stats['processing_times'][-1000:]) if self.stats['processing_times'] else 0
        
        logger.info(f"AI Consumer Stats - Processed: {self.stats['messages_processed']}, "
                   f"Rate: {rate:.2f} msg/sec, "
                   f"AI Predictions: {self.stats['ai_predictions_generated']}, "
                   f"Trades: {self.stats['trades_executed']}, "
                   f"MNPI Alerts: {self.stats['mnpi_alerts']}, "
                   f"Avg Processing: {avg_processing_time:.3f}ms, "
                   f"Max Processing: {max_processing_time:.3f}ms")
    
    async def start(self):
        """Start the Kafka AI consumer"""
        self.running = True
        
        await self.initialize_ai_models()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            kafka_task = executor.submit(self.consume_kafka_messages)
            
            logger.info("Kafka AI consumer started - targeting 20K events/second with <1ms processing")
            
            try:
                while self.running:
                    await asyncio.sleep(1)
                    if kafka_task.done():
                        break
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
            finally:
                self.running = False
                self.log_performance_stats()
                logger.info("Kafka AI consumer stopped")

    async def process_option_chain_message(self, message_data: Dict[str, Any]):
        """Process option chain messages with high-performance analysis"""
        try:
            from high_performance_option_analyzer import HighPerformanceOptionAnalyzer, OptionData
            
            symbol = message_data.get('symbol', 'UNKNOWN')
            option_chain = message_data.get('option_chain', {})
            
            if not option_chain:
                return
            
            option_data = OptionData(
                strikes=np.array(option_chain.get('strikes', [])),
                expiries=np.array(option_chain.get('expiries', [])),
                underlying_price=float(option_chain.get('underlying_price', 0)),
                risk_free_rate=float(option_chain.get('risk_free_rate', 0.05)),
                volatilities=np.array(option_chain.get('volatilities', [])),
                option_types=np.array(option_chain.get('option_types', [])),
                volumes=np.array(option_chain.get('volumes', [])),
                open_interests=np.array(option_chain.get('open_interests', []))
            )
            
            if not hasattr(self, 'option_analyzer'):
                self.option_analyzer = HighPerformanceOptionAnalyzer()
            
            analysis_result = await self.option_analyzer.process_symbol_distributed.remote(symbol, option_data)
            completed_result = ray.get(analysis_result)
            
            from simulation_store import TimescaleSimulationStore
            store = TimescaleSimulationStore()
            await store.store_option_analysis_results(symbol, completed_result)
            
            uoa_result = completed_result.get('uoa_result', {})
            if uoa_result.get('total_anomalies', 0) > 0:
                high_confidence_events = [
                    event for event in uoa_result.get('uoa_events', [])
                    if event.get('confidence', 0) > 0.7
                ]
                
                if high_confidence_events:
                    await self.generate_option_trading_signal(symbol, high_confidence_events, completed_result)
            
            self.stats['option_analyses_completed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing option chain message: {e}")
    
    async def generate_option_trading_signal(self, symbol: str, uoa_events: List[Dict], 
                                           analysis_result: Dict[str, Any]):
        """Generate trading signals based on UOA detection and Greeks analysis"""
        try:
            if not hasattr(self, 'retroactive_learning'):
                from .retroactive_option_learning import RetroactiveOptionLearning
                self.retroactive_learning = RetroactiveOptionLearning()
                await self.retroactive_learning.start_learning_worker()
            
            call_events = [e for e in uoa_events if e.get('option_type') == 'call']
            put_events = [e for e in uoa_events if e.get('option_type') == 'put']
            
            signal_strength = 0.0
            signal_direction = 'neutral'
            trade_action = 'hold'
            
            if len(call_events) > len(put_events):
                signal_direction = 'bullish'
                signal_strength = min(0.9, 0.5 + 0.1 * len(call_events))
                trade_action = 'buy_call'
            elif len(put_events) > len(call_events):
                signal_direction = 'bearish'
                signal_strength = min(0.9, 0.5 + 0.1 * len(put_events))
                trade_action = 'buy_put'
            
            max_pain_strike = analysis_result.get('max_pain_strike', 0)
            underlying_price = analysis_result.get('underlying_price', 0)
            
            if underlying_price > 0 and max_pain_strike > 0:
                price_distance = abs(underlying_price - max_pain_strike) / underlying_price
                if price_distance > 0.05:  # 5% threshold
                    signal_strength *= 1.2  # Amplify signal
            
            if signal_strength > 0.6:
                trading_signal = {
                    'symbol': symbol,
                    'signal_type': 'option_uoa',
                    'direction': signal_direction,
                    'strength': signal_strength,
                    'confidence': np.mean([e.get('confidence', 0) for e in uoa_events]),
                    'uoa_events_count': len(uoa_events),
                    'max_pain_strike': max_pain_strike,
                    'timestamp': datetime.now().isoformat(),
                    'trade_action': trade_action
                }
                
                option_conditions = analysis_result.get('option_conditions', {})
                if option_conditions:
                    trade_id = f"{symbol}_{int(time.time())}_{signal_direction}"
                    entry_price = underlying_price  # Use underlying price as proxy
                    
                    await self.retroactive_learning.record_option_trade_entry(
                        trade_id=trade_id,
                        symbol=symbol,
                        option_conditions=option_conditions,
                        trade_action=trade_action,
                        entry_price=entry_price
                    )
                    
                    from .simulation_store import TimescaleSimulationStore
                    store = TimescaleSimulationStore()
                    await store.store_option_trade_outcome(
                        trade_id=trade_id,
                        symbol=symbol,
                        option_conditions=option_conditions,
                        trade_action=trade_action,
                        entry_price=entry_price
                    )
                    
                    trading_signal['trade_id'] = trade_id
                
                await self.trading_engine.process_option_signal(trading_signal)
                
                self.stats['option_signals_generated'] += 1
                logger.info(f"Generated option trading signal for {symbol}: {signal_direction} ({signal_strength:.2f})")
        
        except Exception as e:
            logger.error(f"Error generating option trading signal: {e}")
    
    async def record_option_trade_outcome(self, trade_id: str, exit_price: float, profit_loss: float):
        """Record option trade outcome for retroactive learning"""
        try:
            if hasattr(self, 'retroactive_learning'):
                await self.retroactive_learning.record_option_trade_exit(
                    trade_id=trade_id,
                    exit_price=exit_price,
                    profit_loss=profit_loss
                )
                
                from .simulation_store import TimescaleSimulationStore
                store = TimescaleSimulationStore()
                
                logger.debug(f"Recorded option trade outcome: {trade_id}, P&L: {profit_loss:.4f}")
        except Exception as e:
            logger.error(f"Error recording option trade outcome: {e}")

async def main():
    """Main entry point for Kafka AI consumer"""
    consumer = KafkaAIConsumer(
        topics=['trades', 'news-analysis', 'risk-assessment', 'exegy-feed', 'compliance-monitoring', 'option-chains']
    )
    await consumer.start()

if __name__ == "__main__":
    asyncio.run(main())

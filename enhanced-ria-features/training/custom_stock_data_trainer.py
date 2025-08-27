#!/usr/bin/env python3
"""
Custom Stock Data Training System for QuantROI
Enables real-time learning from user-provided stock data
"""

import asyncio
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..causal_ai_engine.causal_ai_orchestrator import CausalAIOrchestrator
from ..real_time_pipeline.event_processor import HighPerformanceEventProcessor
from ..auto_agent_system.langchain_integration import LangchainAutoAgent
from ..storage_granularity.granularity_limiter import GranularityLimiter

logger = logging.getLogger(__name__)

class CustomStockDataTrainer:
    """
    Real-time learning system for custom stock data
    Integrates with existing QuantROI infrastructure
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.causal_orchestrator = None
        self.event_processor = None
        self.auto_agent = None
        self.granularity_limiter = GranularityLimiter()
        self.openai_api_key = openai_api_key
        
        self.training_metrics = {
            'events_processed': 0,
            'learning_accuracy': 0.0,
            'causal_relationships_discovered': 0,
            'prediction_accuracy': 0.0
        }
    
    async def initialize_learning_system(self):
        """Initialize all learning components"""
        try:
            logger.info("Initializing QuantROI learning system...")
            
            self.causal_orchestrator = CausalAIOrchestrator()
            await self.causal_orchestrator.initialize()
            
            self.event_processor = HighPerformanceEventProcessor(
                kafka_servers=['localhost:9092'],
                redis_url='redis://localhost:6379',
                max_workers=8,
                batch_size=50
            )
            await self.event_processor.initialize()
            
            if self.openai_api_key:
                self.auto_agent = LangchainAutoAgent(
                    self.granularity_limiter, 
                    self.openai_api_key
                )
            
            self.event_processor.register_handler('stock_price_update', self.handle_price_update)
            self.event_processor.register_handler('trade_execution', self.handle_trade_execution)
            self.event_processor.register_handler('market_news', self.handle_news_event)
            
            logger.info("Learning system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize learning system: {e}")
            return False
    
    async def load_custom_stock_data(self, data_file: str, symbol: str) -> bool:
        """
        Load custom stock data from CSV/JSON file
        Expected format: timestamp, open, high, low, close, volume
        """
        try:
            logger.info(f"Loading custom data for {symbol} from {data_file}")
            
            if data_file.endswith('.csv'):
                df = pd.read_csv(data_file)
            elif data_file.endswith('.json'):
                df = pd.read_json(data_file)
            else:
                raise ValueError("Unsupported file format. Use CSV or JSON.")
            
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            events = []
            for _, row in df.iterrows():
                event = {
                    'event_id': f"{symbol}_{row['timestamp']}",
                    'timestamp': pd.to_datetime(row['timestamp']).isoformat(),
                    'event_type': 'stock_price_update',
                    'source': 'custom_data',
                    'data': {
                        'symbol': symbol,
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume']),
                        'price_change': float(row['close'] - row['open']),
                        'price_change_pct': float((row['close'] - row['open']) / row['open'] * 100)
                    },
                    'priority': 2  # Medium priority for historical data
                }
                events.append(event)
            
            logger.info(f"Loaded {len(events)} events for {symbol}")
            
            await self.process_events_for_learning(events)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load custom stock data: {e}")
            return False
    
    async def process_events_for_learning(self, events: List[Dict[str, Any]]):
        """Process events through the learning pipeline"""
        try:
            logger.info(f"Processing {len(events)} events for learning...")
            
            for event in events:
                await self.event_processor.route_event(event)
                
                self.training_metrics['events_processed'] += 1
                
                if self.training_metrics['events_processed'] % 100 == 0:
                    await asyncio.sleep(0.01)  # Small delay
            
            logger.info("Event processing completed")
            
        except Exception as e:
            logger.error(f"Error processing events: {e}")
    
    async def handle_price_update(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stock price update events for learning"""
        try:
            symbol = event['data']['symbol']
            price = event['data']['close']
            volume = event['data']['volume']
            price_change_pct = event['data']['price_change_pct']
            
            causal_result = await self.causal_orchestrator.process_real_time_event({
                'event_type': 'price_movement',
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'change_pct': price_change_pct,
                'timestamp': event['timestamp']
            })
            
            if causal_result.get('success'):
                self.training_metrics['learning_accuracy'] = causal_result.get('accuracy', 0.0)
                self.training_metrics['causal_relationships_discovered'] += causal_result.get('new_relationships', 0)
            
            return {
                'processed': True,
                'symbol': symbol,
                'learning_result': causal_result,
                'timestamp': event['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error handling price update: {e}")
            return {'processed': False, 'error': str(e)}
    
    async def handle_trade_execution(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle trade execution events for retroactive learning"""
        try:
            symbol = event['data']['symbol']
            action = event['data']['action']  # buy/sell
            quantity = event['data']['quantity']
            price = event['data']['price']
            outcome = event['data'].get('outcome', 'pending')  # profit/loss/pending
            
            if outcome != 'pending':
                learning_data = {
                    'symbol': symbol,
                    'action': action,
                    'entry_price': price,
                    'outcome': outcome,
                    'quantity': quantity,
                    'timestamp': event['timestamp']
                }
                
                learning_result = await self.causal_orchestrator.process_retroactive_learning(learning_data)
                
                if learning_result.get('success'):
                    self.training_metrics['prediction_accuracy'] = learning_result.get('prediction_accuracy', 0.0)
            
            return {
                'processed': True,
                'symbol': symbol,
                'action': action,
                'learning_applied': outcome != 'pending'
            }
            
        except Exception as e:
            logger.error(f"Error handling trade execution: {e}")
            return {'processed': False, 'error': str(e)}
    
    async def handle_news_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle news events for causal learning"""
        try:
            symbol = event['data']['symbol']
            headline = event['data']['headline']
            sentiment = event['data'].get('sentiment', 0.0)
            
            news_impact = await self.causal_orchestrator.analyze_news_impact({
                'symbol': symbol,
                'headline': headline,
                'sentiment': sentiment,
                'timestamp': event['timestamp']
            })
            
            return {
                'processed': True,
                'symbol': symbol,
                'news_impact': news_impact
            }
            
        except Exception as e:
            logger.error(f"Error handling news event: {e}")
            return {'processed': False, 'error': str(e)}
    
    async def train_on_custom_data(self, symbol: str, data_file: str, enable_auto_agent: bool = True) -> Dict[str, Any]:
        """
        Main training function for custom stock data
        """
        try:
            logger.info(f"Starting training on custom data for {symbol}")
            
            if not await self.initialize_learning_system():
                return {'success': False, 'error': 'Failed to initialize learning system'}
            
            if not await self.load_custom_stock_data(data_file, symbol):
                return {'success': False, 'error': 'Failed to load custom data'}
            
            if enable_auto_agent and self.auto_agent:
                logger.info("Running auto-agent optimization...")
                
                gaps = self.granularity_limiter.detect_data_gaps(symbol, '1m')
                if gaps:
                    gap_resolution = await self.auto_agent.resolve_data_gaps_intelligently(
                        symbol=symbol,
                        gaps=gaps,
                        budget=50.0,  # $50 budget for data resolution
                        urgency='medium'
                    )
                    logger.info(f"Auto-agent gap resolution: {gap_resolution['success']}")
            
            training_report = {
                'success': True,
                'symbol': symbol,
                'training_metrics': self.training_metrics,
                'learning_summary': {
                    'events_processed': self.training_metrics['events_processed'],
                    'learning_accuracy': f"{self.training_metrics['learning_accuracy']:.2%}",
                    'causal_relationships': self.training_metrics['causal_relationships_discovered'],
                    'prediction_accuracy': f"{self.training_metrics['prediction_accuracy']:.2%}"
                },
                'recommendations': await self.generate_trading_recommendations(symbol)
            }
            
            logger.info(f"Training completed for {symbol}")
            return training_report
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def generate_trading_recommendations(self, symbol: str) -> List[str]:
        """Generate AI-driven trading recommendations based on learning"""
        try:
            recommendations = []
            
            if self.causal_orchestrator:
                causal_insights = await self.causal_orchestrator.get_causal_insights(symbol)
                
                if causal_insights.get('strong_predictors'):
                    recommendations.append(
                        f"Strong causal predictors identified: {', '.join(causal_insights['strong_predictors'])}"
                    )
                
                if causal_insights.get('regime_detection'):
                    regime = causal_insights['regime_detection']
                    recommendations.append(
                        f"Current market regime: {regime['type']} (confidence: {regime['confidence']:.2%})"
                    )
            
            if self.training_metrics['prediction_accuracy'] > 0.8:
                recommendations.append("High prediction accuracy achieved - consider increasing position sizes")
            elif self.training_metrics['prediction_accuracy'] < 0.6:
                recommendations.append("Low prediction accuracy - recommend more training data or feature engineering")
            
            if self.training_metrics['causal_relationships_discovered'] > 10:
                recommendations.append("Multiple causal relationships discovered - enable automated trading")
            else:
                recommendations.append("Limited causal relationships - consider adding more data sources")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations - check system logs"]
    
    async def get_learning_status(self) -> Dict[str, Any]:
        """Get current learning system status"""
        try:
            processor_metrics = await self.event_processor.get_metrics() if self.event_processor else {}
            
            status = {
                'system_initialized': all([
                    self.causal_orchestrator is not None,
                    self.event_processor is not None
                ]),
                'training_metrics': self.training_metrics,
                'processor_metrics': processor_metrics,
                'auto_agent_enabled': self.auto_agent is not None,
                'timestamp': datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting learning status: {e}")
            return {'error': str(e)}

async def train_on_apple_stock(data_file: str, openai_key: str = None):
    """Example: Train on Apple stock data"""
    trainer = CustomStockDataTrainer(openai_api_key=openai_key)
    result = await trainer.train_on_custom_data('AAPL', data_file)
    print(f"Training result: {json.dumps(result, indent=2)}")
    return result

async def train_on_multiple_stocks(stock_data_files: Dict[str, str], openai_key: str = None):
    """Example: Train on multiple stocks"""
    trainer = CustomStockDataTrainer(openai_api_key=openai_key)
    results = {}
    
    for symbol, data_file in stock_data_files.items():
        print(f"Training on {symbol}...")
        result = await trainer.train_on_custom_data(symbol, data_file)
        results[symbol] = result
        
        await asyncio.sleep(1)
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='QuantROI Custom Stock Data Trainer')
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., AAPL)')
    parser.add_argument('--data-file', required=True, help='Path to CSV/JSON data file')
    parser.add_argument('--openai-key', help='OpenAI API key for auto-agent features')
    parser.add_argument('--enable-auto-agent', action='store_true', help='Enable auto-agent optimization')
    
    args = parser.parse_args()
    
    async def main():
        trainer = CustomStockDataTrainer(openai_api_key=args.openai_key)
        result = await trainer.train_on_custom_data(
            symbol=args.symbol,
            data_file=args.data_file,
            enable_auto_agent=args.enable_auto_agent
        )
        
        print("\n" + "="*50)
        print("QUANTROI TRAINING RESULTS")
        print("="*50)
        print(json.dumps(result, indent=2))
        
        if result['success']:
            print(f"\n✅ Training completed successfully for {args.symbol}")
            print(f"📊 Events processed: {result['training_metrics']['events_processed']}")
            print(f"🎯 Learning accuracy: {result['learning_summary']['learning_accuracy']}")
            print(f"🔗 Causal relationships: {result['learning_summary']['causal_relationships']}")
            print(f"📈 Prediction accuracy: {result['learning_summary']['prediction_accuracy']}")
            
            print("\n🤖 AI Recommendations:")
            for rec in result['recommendations']:
                print(f"  • {rec}")
        else:
            print(f"\n❌ Training failed: {result.get('error', 'Unknown error')}")
    
    asyncio.run(main())

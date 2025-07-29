from enhanced_causal_trading_model import MasterStrategyLearningEngine, WealthGenerationAITrainer
from backtesting_engine import AdvancedBacktestingEngine
from monte_carlo_engine import ScenarioSimulationEngine
from risk_analytics import AdvancedRiskAnalytics, EventDrivenRiskMonitor
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import numpy as np

class BacktestingMasterStrategyIntegration:
    """
    Integration layer between backtesting engine and master strategy learning
    Implements event-driven architecture for real-time strategy adaptation
    """
    
    def __init__(self):
        self.backtesting_engine = AdvancedBacktestingEngine()
        self.master_strategy = MasterStrategyLearningEngine()
        self.wealth_trainer = WealthGenerationAITrainer()
        self.monte_carlo_engine = ScenarioSimulationEngine()
        self.risk_analytics = AdvancedRiskAnalytics()
        self.risk_monitor = EventDrivenRiskMonitor()
        
        self.event_queue = asyncio.Queue()
        self.strategy_performance_cache = {}
        
    async def run_adaptive_backtesting_cycle(
        self,
        symbols: List[str],
        lookback_months: int = 12
    ) -> Dict[str, Any]:
        """Run backtesting cycle that feeds back into master strategy learning"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_months * 30)
        
        logging.info(f"Starting adaptive backtesting cycle for {symbols}")
        logging.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        backtest_results = await self.backtesting_engine.run_concurrent_backtests(
            symbols=symbols,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        await self._process_backtest_events(backtest_results)
        
        for strategy_name, result in backtest_results.items():
            if strategy_name != 'monte_carlo_analysis':
                await self.master_strategy.update_strategy_performance(
                    strategy_name=strategy_name,
                    performance_metrics={
                        'total_return': result.total_return,
                        'sharpe_ratio': result.sharpe_ratio,
                        'max_drawdown': result.max_drawdown,
                        'win_rate': result.win_rate
                    }
                )
        
        await self.wealth_trainer.train_on_backtest_results(backtest_results)
        
        best_strategy_name = max(backtest_results.items(), key=lambda x: x[1].total_return)[0]
        monte_carlo_results = await self._run_monte_carlo_analysis(best_strategy_name, symbols)
        
        return {
            'backtest_results': backtest_results,
            'monte_carlo_results': monte_carlo_results,
            'strategy_updates': 'completed',
            'wealth_training': 'completed',
            'best_strategy': best_strategy_name
        }
    
    async def _process_backtest_events(self, backtest_results: Dict[str, Any]):
        """Process backtest results through event-driven system"""
        
        for strategy_name, result in backtest_results.items():
            if strategy_name == 'monte_carlo_analysis':
                continue
                
            event = {
                'type': 'portfolio_update',
                'strategy': strategy_name,
                'returns': [result.total_return],
                'timestamp': datetime.now().isoformat()
            }
            
            risk_response = self.risk_monitor.process_risk_event(event)
            
            self.strategy_performance_cache[strategy_name] = {
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'risk_alerts': risk_response.get('alerts', [])
            }
    
    async def _run_monte_carlo_analysis(self, strategy_name: str, symbols: List[str]) -> List[Dict]:
        """Run Monte Carlo analysis for the best performing strategy"""
        
        try:
            historical_data = await self.backtesting_engine.data_loader.load_multi_source_data(
                symbols, 
                (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            )
            
            monte_carlo_results = await self.monte_carlo_engine.run_comprehensive_testing(
                strategy_name, historical_data
            )
            
            serializable_results = []
            for result in monte_carlo_results:
                serializable_results.append({
                    'scenario_id': result.scenario_id,
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'var_95': result.var_95,
                    'var_99': result.var_99,
                    'win_rate': result.win_rate
                })
            
            return serializable_results
            
        except Exception as e:
            logging.error(f"Monte Carlo analysis failed: {e}")
            return []
    
    async def run_event_driven_strategy_selection(
        self,
        market_event: Dict[str, Any]
    ) -> str:
        """Select optimal strategy based on market events"""
        
        event_type = market_event.get('type', 'unknown')
        volatility = market_event.get('volatility', 0.02)
        trend_strength = market_event.get('trend_strength', 0.5)
        
        if event_type == 'high_volatility' or volatility > 0.04:
            selected_strategy = 'gated_dql'
        elif event_type == 'trending_market' or trend_strength > 0.7:
            selected_strategy = 'gated_pg'
        else:
            selected_strategy = 'master_strategy'
        
        if selected_strategy in self.strategy_performance_cache:
            cached_performance = self.strategy_performance_cache[selected_strategy]
            
            if cached_performance['sharpe_ratio'] < 0.5:
                selected_strategy = 'enhanced_master'
        
        logging.info(f"Selected strategy: {selected_strategy} for event: {event_type}")
        return selected_strategy
    
    async def run_walk_forward_analysis(
        self,
        symbols: List[str],
        train_months: int = 12,
        test_months: int = 3,
        step_months: int = 1
    ) -> Dict[str, Any]:
        """Run walk-forward analysis to prevent overfitting"""
        
        results = []
        current_date = datetime.now()
        
        for i in range(0, 24, step_months):  # 2 years of walk-forward
            train_end = current_date - timedelta(days=i * 30)
            train_start = train_end - timedelta(days=train_months * 30)
            test_end = train_end + timedelta(days=test_months * 30)
            
            if test_end > current_date:
                break
            
            logging.info(f"Walk-forward period {i+1}: Train {train_start.strftime('%Y-%m-%d')} to {train_end.strftime('%Y-%m-%d')}")
            
            train_results = await self.backtesting_engine.run_concurrent_backtests(
                symbols=symbols,
                start_date=train_start.strftime('%Y-%m-%d'),
                end_date=train_end.strftime('%Y-%m-%d')
            )
            
            test_results = await self.backtesting_engine.run_concurrent_backtests(
                symbols=symbols,
                start_date=train_end.strftime('%Y-%m-%d'),
                end_date=test_end.strftime('%Y-%m-%d')
            )
            
            for strategy_name in train_results.keys():
                if strategy_name in test_results:
                    results.append({
                        'period': i + 1,
                        'strategy': strategy_name,
                        'train_return': train_results[strategy_name].total_return,
                        'test_return': test_results[strategy_name].total_return,
                        'train_sharpe': train_results[strategy_name].sharpe_ratio,
                        'test_sharpe': test_results[strategy_name].sharpe_ratio
                    })
        
        return {
            'walk_forward_results': results,
            'summary': self._calculate_walk_forward_summary(results)
        }
    
    def _calculate_walk_forward_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics for walk-forward analysis"""
        
        if not results:
            return {}
        
        strategy_results = {}
        for result in results:
            strategy = result['strategy']
            if strategy not in strategy_results:
                strategy_results[strategy] = {
                    'test_returns': [],
                    'test_sharpes': [],
                    'consistency_scores': []
                }
            
            strategy_results[strategy]['test_returns'].append(result['test_return'])
            strategy_results[strategy]['test_sharpes'].append(result['test_sharpe'])
            
            consistency = abs(result['test_return'] - result['train_return']) / abs(result['train_return']) if result['train_return'] != 0 else 1
            strategy_results[strategy]['consistency_scores'].append(1 - consistency)
        
        summary = {}
        for strategy, metrics in strategy_results.items():
            summary[strategy] = {
                'avg_test_return': np.mean(metrics['test_returns']),
                'std_test_return': np.std(metrics['test_returns']),
                'avg_test_sharpe': np.mean(metrics['test_sharpes']),
                'consistency_score': np.mean(metrics['consistency_scores']),
                'num_periods': len(metrics['test_returns'])
            }
        
        return summary

class EventDrivenBacktestingOrchestrator:
    """
    Orchestrates event-driven backtesting across multiple components
    """
    
    def __init__(self):
        self.integration = BacktestingMasterStrategyIntegration()
        self.event_handlers = {
            'market_update': self._handle_market_update,
            'strategy_signal': self._handle_strategy_signal,
            'risk_alert': self._handle_risk_alert,
            'performance_update': self._handle_performance_update
        }
    
    async def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming events through appropriate handlers"""
        
        event_type = event.get('type', 'unknown')
        
        if event_type in self.event_handlers:
            return await self.event_handlers[event_type](event)
        else:
            logging.warning(f"Unknown event type: {event_type}")
            return {'status': 'unknown_event'}
    
    async def _handle_market_update(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle market update events"""
        
        symbol = event.get('symbol', 'UNKNOWN')
        price = event.get('price', 0)
        volatility = event.get('volatility', 0.02)
        
        selected_strategy = await self.integration.run_event_driven_strategy_selection(event)
        
        return {
            'status': 'market_update_processed',
            'symbol': symbol,
            'selected_strategy': selected_strategy,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_strategy_signal(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle strategy signal events"""
        
        strategy = event.get('strategy', 'unknown')
        signal = event.get('signal', 'hold')
        confidence = event.get('confidence', 0.5)
        
        logging.info(f"Strategy signal: {strategy} -> {signal} (confidence: {confidence})")
        
        return {
            'status': 'signal_processed',
            'strategy': strategy,
            'signal': signal,
            'confidence': confidence
        }
    
    async def _handle_risk_alert(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle risk alert events"""
        
        alert_type = event.get('alert_type', 'unknown')
        severity = event.get('severity', 'low')
        
        risk_response = self.integration.risk_monitor.process_risk_event(event)
        
        return {
            'status': 'risk_alert_processed',
            'alert_type': alert_type,
            'severity': severity,
            'risk_response': risk_response
        }
    
    async def _handle_performance_update(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle performance update events"""
        
        strategy = event.get('strategy', 'unknown')
        performance_metrics = event.get('metrics', {})
        
        self.integration.strategy_performance_cache[strategy] = performance_metrics
        
        return {
            'status': 'performance_updated',
            'strategy': strategy,
            'metrics': performance_metrics
        }

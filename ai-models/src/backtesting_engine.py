import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
import json
import yfinance as yf
from enhanced_causal_trading_model import (
    GatedDeepQLearningStrategy, 
    GatedPolicyGradientStrategy,
    MasterStrategyLearningEngine
)
from trading_instructions import TradingInstructionEngine, EnhancedMasterStrategy

@dataclass
class BacktestResult:
    strategy_name: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_duration: float
    performance_by_period: Dict[str, float]
    trade_log: List[Dict[str, Any]]

@dataclass
class MarketData:
    timestamp: datetime
    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    volatility: float
    regime: str  # 'bull', 'bear', 'sideways', 'high_vol'

class HistoricalDataLoader:
    """Loads and preprocesses historical market data for backtesting"""
    
    def __init__(self):
        self.data_cache = {}
        
    async def load_data(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Load historical data for given symbols and date range"""
        data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date, interval="1h")
                
                if df.empty:
                    logging.warning(f"No data found for {symbol}")
                    continue
                    
                df['volatility'] = df['Close'].rolling(window=24).std()
                df['returns'] = df['Close'].pct_change()
                df['sma_20'] = df['Close'].rolling(window=20).mean()
                df['sma_50'] = df['Close'].rolling(window=50).mean()
                
                df['regime'] = self._classify_market_regime(df)
                
                market_data = []
                for idx, row in df.iterrows():
                    market_data.append(MarketData(
                        timestamp=idx,
                        symbol=symbol,
                        open_price=row['Open'],
                        high_price=row['High'],
                        low_price=row['Low'],
                        close_price=row['Close'],
                        volume=row['Volume'],
                        volatility=row['volatility'] if not pd.isna(row['volatility']) else 0.0,
                        regime=row['regime']
                    ))
                
                data[symbol] = market_data
                logging.info(f"Loaded {len(market_data)} data points for {symbol}")
                
            except Exception as e:
                logging.error(f"Error loading data for {symbol}: {e}")
                
        return data
    
    def _classify_market_regime(self, df: pd.DataFrame) -> pd.Series:
        """Classify market regime based on price action and volatility"""
        regimes = []
        
        for i in range(len(df)):
            if i < 50:  # Need enough data for moving averages
                regimes.append('sideways')
                continue
                
            current_price = df.iloc[i]['Close']
            sma_20 = df.iloc[i]['sma_20']
            sma_50 = df.iloc[i]['sma_50']
            volatility = df.iloc[i]['volatility']
            
            if volatility > df['volatility'].rolling(window=100).mean().iloc[i] * 1.5:
                regimes.append('high_vol')
            elif current_price > sma_20 and current_price > sma_50 and sma_20 > sma_50:
                regimes.append('bull')
            elif current_price < sma_20 and current_price < sma_50 and sma_20 < sma_50:
                regimes.append('bear')
            else:
                regimes.append('sideways')
                
        return pd.Series(regimes, index=df.index)

class BacktestingEngine:
    """Main backtesting engine that runs strategies against historical data"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.data_loader = HistoricalDataLoader()
        self.results = {}
        
        self.gated_dql = GatedDeepQLearningStrategy(
            state_dim=10, action_dim=3, hidden_dim=128, learning_rate=0.001
        )
        self.gated_pg = GatedPolicyGradientStrategy(
            state_dim=10, action_dim=3, hidden_dim=128, learning_rate=0.001
        )
        self.master_engine = MasterStrategyLearningEngine()
        self.trading_instructions = TradingInstructionEngine()
        
    async def run_backtest(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        strategies: List[str] = None
    ) -> Dict[str, BacktestResult]:
        """Run comprehensive backtest across multiple strategies"""
        
        if strategies is None:
            strategies = ['gated_dql', 'gated_pg', 'master_strategy', 'enhanced_master']
            
        logging.info(f"Starting backtest from {start_date} to {end_date}")
        logging.info(f"Symbols: {symbols}")
        logging.info(f"Strategies: {strategies}")
        
        historical_data = await self.data_loader.load_data(symbols, start_date, end_date)
        
        if not historical_data:
            raise ValueError("No historical data loaded")
            
        results = {}
        
        for strategy_name in strategies:
            logging.info(f"Running backtest for {strategy_name}")
            
            try:
                result = await self._run_strategy_backtest(
                    strategy_name, historical_data, symbols[0]  # Use first symbol as primary
                )
                results[strategy_name] = result
                
            except Exception as e:
                logging.error(f"Error running {strategy_name}: {e}")
                
        return results
    
    async def _run_strategy_backtest(
        self, 
        strategy_name: str, 
        historical_data: Dict[str, List[MarketData]], 
        primary_symbol: str
    ) -> BacktestResult:
        """Run backtest for a specific strategy"""
        
        capital = self.initial_capital
        position = 0.0
        trades = []
        equity_curve = []
        
        data_points = historical_data[primary_symbol]
        
        for i, market_data in enumerate(data_points[50:], 50):  # Skip first 50 for indicators
            
            recent_data = data_points[max(0, i-10):i]
            state = self._prepare_state_features(recent_data, market_data)
            
            action, confidence, expected_return = await self._get_strategy_decision(
                strategy_name, state, market_data
            )
            
            if action != 0:  # 0 = hold, 1 = buy, -1 = sell
                trade_result = self._execute_trade(
                    action, confidence, market_data, capital, position
                )
                
                if trade_result:
                    trades.append(trade_result)
                    capital = trade_result['new_capital']
                    position = trade_result['new_position']
                    
            current_equity = capital + (position * market_data.close_price)
            equity_curve.append({
                'timestamp': market_data.timestamp,
                'equity': current_equity,
                'position': position,
                'price': market_data.close_price
            })
            
            if len(trades) > 0 and hasattr(self, f'_update_{strategy_name}'):
                await getattr(self, f'_update_{strategy_name}')(
                    state, action, trades[-1]['return'], market_data
                )
        
        return self._calculate_performance_metrics(
            strategy_name, trades, equity_curve, self.initial_capital
        )
    
    def _prepare_state_features(self, recent_data: List[MarketData], current_data: MarketData) -> np.ndarray:
        """Prepare state features for strategy input"""
        if len(recent_data) < 5:
            return np.zeros(10)
            
        prices = [d.close_price for d in recent_data[-5:]]
        returns = np.diff(prices) / prices[:-1] if len(prices) > 1 else [0]
        
        volatilities = [d.volatility for d in recent_data[-3:]]
        volumes = [d.volume for d in recent_data[-3:]]
        
        regime_map = {'bull': 1, 'bear': -1, 'sideways': 0, 'high_vol': 2}
        regime_score = regime_map.get(current_data.regime, 0)
        
        features = []
        features.extend(returns[-3:] if len(returns) >= 3 else [0, 0, 0])
        features.extend(volatilities)
        features.extend([v/1e6 for v in volumes])  # Normalize volume
        features.append(regime_score)
        
        while len(features) < 10:
            features.append(0)
        return np.array(features[:10])
    
    async def _get_strategy_decision(
        self, 
        strategy_name: str, 
        state: np.ndarray, 
        market_data: MarketData
    ) -> Tuple[int, float, float]:
        """Get trading decision from specified strategy"""
        
        if strategy_name == 'gated_dql':
            action = self.gated_dql.select_action(state)
            expected_return = self.gated_dql.calculate_expected_return(state, action)
            confidence = 0.7  # Default confidence
            
        elif strategy_name == 'gated_pg':
            action = self.gated_pg.select_action(state)
            expected_return = self.gated_pg.calculate_expected_return(state, action)
            confidence = 0.8
            
        elif strategy_name == 'master_strategy':
            strategy_choice = self.master_engine.select_optimal_strategy(
                market_regime=market_data.regime,
                volatility=market_data.volatility,
                qos_requirements={'latency': 1.0, 'accuracy': 0.95}
            )
            
            if strategy_choice == 'gated_dql':
                action = self.gated_dql.select_action(state)
                expected_return = self.gated_dql.calculate_expected_return(state, action)
            else:
                action = self.gated_pg.select_action(state)
                expected_return = self.gated_pg.calculate_expected_return(state, action)
                
            confidence = 0.85
            
        elif strategy_name == 'enhanced_master':
            instruction = self.trading_instructions.generate_market_signal(
                symbol=market_data.symbol,
                current_price=market_data.close_price,
                volume=market_data.volume,
                volatility=market_data.volatility,
                market_regime=market_data.regime
            )
            
            if hasattr(self.gated_dql, 'execute_trade_with_instruction'):
                action, expected_return = self.gated_dql.execute_trade_with_instruction(
                    state, instruction
                )
            else:
                action = self.gated_dql.select_action(state)
                expected_return = self.gated_dql.calculate_expected_return(state, action)
                
            confidence = instruction.get('confidence', 0.75)
            
        else:
            action, expected_return, confidence = 0, 0.0, 0.5
            
        return action, confidence, expected_return
    
    def _execute_trade(
        self, 
        action: int, 
        confidence: float, 
        market_data: MarketData, 
        capital: float, 
        current_position: float
    ) -> Optional[Dict[str, Any]]:
        """Execute a trade and return trade details"""
        
        max_position_size = capital * 0.1  # Max 10% of capital per trade
        position_size = max_position_size * confidence
        
        if action == 1:  # Buy
            if capital >= position_size:
                shares = position_size / market_data.close_price
                new_position = current_position + shares
                new_capital = capital - position_size
                
                return {
                    'timestamp': market_data.timestamp,
                    'action': 'buy',
                    'shares': shares,
                    'price': market_data.close_price,
                    'value': position_size,
                    'new_position': new_position,
                    'new_capital': new_capital,
                    'confidence': confidence,
                    'return': 0.0  # Will be calculated when position is closed
                }
                
        elif action == -1:  # Sell
            if current_position > 0:
                shares_to_sell = min(current_position, position_size / market_data.close_price)
                sell_value = shares_to_sell * market_data.close_price
                new_position = current_position - shares_to_sell
                new_capital = capital + sell_value
                
                return {
                    'timestamp': market_data.timestamp,
                    'action': 'sell',
                    'shares': shares_to_sell,
                    'price': market_data.close_price,
                    'value': sell_value,
                    'new_position': new_position,
                    'new_capital': new_capital,
                    'confidence': confidence,
                    'return': 0.0  # Will be calculated based on buy price
                }
        
        return None
    
    def _calculate_performance_metrics(
        self, 
        strategy_name: str, 
        trades: List[Dict[str, Any]], 
        equity_curve: List[Dict[str, Any]], 
        initial_capital: float
    ) -> BacktestResult:
        """Calculate comprehensive performance metrics"""
        
        if not equity_curve:
            return BacktestResult(
                strategy_name=strategy_name,
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                total_trades=0,
                avg_trade_duration=0.0,
                performance_by_period={},
                trade_log=[]
            )
        
        final_equity = equity_curve[-1]['equity']
        total_return = (final_equity - initial_capital) / initial_capital
        
        equity_values = [point['equity'] for point in equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        peak = equity_values[0]
        max_drawdown = 0
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        profitable_trades = sum(1 for trade in trades if trade.get('return', 0) > 0)
        win_rate = profitable_trades / len(trades) if trades else 0
        
        avg_trade_duration = 24.0  # Assume 24 hours average
        
        performance_by_period = self._calculate_monthly_performance(equity_curve)
        
        return BacktestResult(
            strategy_name=strategy_name,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=len(trades),
            avg_trade_duration=avg_trade_duration,
            performance_by_period=performance_by_period,
            trade_log=trades
        )
    
    def _calculate_monthly_performance(self, equity_curve: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate monthly performance breakdown"""
        monthly_performance = {}
        
        if not equity_curve:
            return monthly_performance
            
        monthly_data = {}
        for point in equity_curve:
            month_key = point['timestamp'].strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(point['equity'])
        
        for month, equities in monthly_data.items():
            if len(equities) > 1:
                monthly_return = (equities[-1] - equities[0]) / equities[0]
                monthly_performance[month] = monthly_return
                
        return monthly_performance

class BacktestRunner:
    """High-level interface for running backtests"""
    
    def __init__(self):
        self.engine = BacktestingEngine()
        
    async def run_comprehensive_backtest(
        self, 
        symbols: List[str] = None, 
        lookback_months: int = 12,
        strategies: List[str] = None
    ) -> Dict[str, BacktestResult]:
        """Run a comprehensive backtest with default parameters"""
        
        if symbols is None:
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
            
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_months * 30)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        print(f"🚀 Starting comprehensive backtest...")
        print(f"📅 Period: {start_str} to {end_str}")
        print(f"📈 Symbols: {symbols}")
        
        results = await self.engine.run_backtest(
            symbols=symbols,
            start_date=start_str,
            end_date=end_str,
            strategies=strategies
        )
        
        self._print_results_summary(results)
        
        return results
    
    def _print_results_summary(self, results: Dict[str, BacktestResult]):
        """Print formatted results summary"""
        
        print("\n" + "="*80)
        print("🎯 BACKTEST RESULTS SUMMARY")
        print("="*80)
        
        for strategy_name, result in results.items():
            print(f"\n📊 {strategy_name.upper()}")
            print("-" * 40)
            print(f"Total Return: {result.total_return:.2%}")
            print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
            print(f"Max Drawdown: {result.max_drawdown:.2%}")
            print(f"Win Rate: {result.win_rate:.2%}")
            print(f"Total Trades: {result.total_trades}")
            
        best_strategy = max(results.items(), key=lambda x: x[1].total_return)
        print(f"\n🏆 BEST PERFORMING STRATEGY: {best_strategy[0].upper()}")
        print(f"🎉 Total Return: {best_strategy[1].total_return:.2%}")

async def main():
    """Main function to demonstrate backtesting system"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🤖 QuantROI Backtesting Engine")
    print("=" * 50)
    
    runner = BacktestRunner()
    
    try:
        results = await runner.run_comprehensive_backtest(
            symbols=['AAPL', 'MSFT', 'SPY'],
            lookback_months=6,
            strategies=['gated_dql', 'gated_pg', 'master_strategy', 'enhanced_master']
        )
        
        results_file = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        json_results = {}
        for strategy, result in results.items():
            json_results[strategy] = {
                'strategy_name': result.strategy_name,
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'avg_trade_duration': result.avg_trade_duration,
                'performance_by_period': result.performance_by_period
            }
        
        with open(results_file, 'w') as f:
            json.dump(json_results, f, indent=2)
            
        print(f"\n💾 Results saved to: {results_file}")
        
    except Exception as e:
        logging.error(f"Backtest failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

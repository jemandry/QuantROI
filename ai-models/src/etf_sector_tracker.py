import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time
from datetime import datetime, timedelta
import yfinance as yf
from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest

class ETFSectorTracker:
    """
    Track S&P sector ETFs and learn relationships between component stocks
    Integrates with existing Brownian motion storage for stochastic modeling
    """
    
    def __init__(self, simulation_bridge: SimulationEngineBridge):
        self.simulation_bridge = simulation_bridge
        
        self.sector_etfs = {
            'XLK': {'name': 'Technology', 'components': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA']},
            'XLF': {'name': 'Financial', 'components': ['JPM', 'BAC', 'WFC', 'GS', 'MS']},
            'XLE': {'name': 'Energy', 'components': ['XOM', 'CVX', 'COP', 'EOG', 'SLB']},
            'XLV': {'name': 'Healthcare', 'components': ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK']},
            'XLY': {'name': 'Consumer Discretionary', 'components': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE']},
            'XLP': {'name': 'Consumer Staples', 'components': ['PG', 'KO', 'PEP', 'WMT', 'COST']},
            'XLI': {'name': 'Industrial', 'components': ['BA', 'CAT', 'GE', 'MMM', 'UPS']},
            'XLB': {'name': 'Materials', 'components': ['LIN', 'APD', 'SHW', 'FCX', 'NEM']},
            'XLRE': {'name': 'Real Estate', 'components': ['AMT', 'PLD', 'CCI', 'EQIX', 'SPG']},
            'XLU': {'name': 'Utilities', 'components': ['NEE', 'SO', 'DUK', 'AEP', 'EXC']}
        }
        
        self.acceleration_history = {}
        self.correlation_matrix = {}
        self.moving_averages = {}
        
    async def detect_sector_acceleration(self, lookback_periods: int = 20) -> Dict[str, Any]:
        """Detect acceleration of change in sector ETFs"""
        acceleration_results = {}
        
        for etf_symbol, sector_info in self.sector_etfs.items():
            try:
                etf_data = yf.download(etf_symbol, period="1mo", interval="1d")
                
                if len(etf_data) < lookback_periods:
                    continue
                
                prices = etf_data['Close'].values[-lookback_periods:]
                
                velocity = np.diff(prices)
                
                acceleration = np.diff(velocity)
                
                acceleration_threshold = 2 * np.std(acceleration)
                recent_acceleration = acceleration[-1] if len(acceleration) > 0 else 0
                
                is_accelerating = abs(recent_acceleration) > acceleration_threshold
                
                acceleration_results[etf_symbol] = {
                    'sector_name': sector_info['name'],
                    'current_acceleration': float(recent_acceleration),
                    'acceleration_threshold': float(acceleration_threshold),
                    'is_accelerating': is_accelerating,
                    'acceleration_direction': 'positive' if recent_acceleration > 0 else 'negative',
                    'component_stocks': sector_info['components']
                }
                
                if etf_symbol not in self.acceleration_history:
                    self.acceleration_history[etf_symbol] = []
                
                self.acceleration_history[etf_symbol].append({
                    'timestamp': datetime.now(),
                    'acceleration': recent_acceleration,
                    'is_accelerating': is_accelerating
                })
                
                if len(self.acceleration_history[etf_symbol]) > 1000:
                    self.acceleration_history[etf_symbol] = self.acceleration_history[etf_symbol][-1000:]
                
            except Exception as e:
                acceleration_results[etf_symbol] = {'error': str(e)}
        
        return {
            'timestamp': datetime.now().isoformat(),
            'sector_accelerations': acceleration_results,
            'accelerating_sectors': [
                etf for etf, data in acceleration_results.items() 
                if data.get('is_accelerating', False)
            ]
        }
    
    async def learn_component_relationships(self, sector_etf: str, 
                                          analysis_period_days: int = 30) -> Dict[str, Any]:
        """Learn relationships between ETF and component stocks using Brownian motion"""
        if sector_etf not in self.sector_etfs:
            return {'error': f'Unknown sector ETF: {sector_etf}'}
        
        sector_info = self.sector_etfs[sector_etf]
        component_stocks = sector_info['components']
        
        symbols = [sector_etf] + component_stocks
        
        try:
            data = yf.download(symbols, period=f"{analysis_period_days}d", interval="1h")
            
            if data.empty:
                return {'error': 'No data available'}
            
            returns = data['Close'].pct_change().dropna()
            correlation_matrix = returns.corr()
            
            etf_correlations = correlation_matrix[sector_etf].drop(sector_etf).to_dict()
            
            simulation_results = {}
            
            for stock in component_stocks:
                if stock in returns.columns:
                    stock_returns = returns[stock].dropna()
                    
                    if len(stock_returns) > 10:
                        mu = stock_returns.mean() * 252  # Annualized drift
                        sigma = stock_returns.std() * np.sqrt(252)  # Annualized volatility
                        s0 = data['Close'][stock].iloc[-1]  # Current price
                        
                        sim_request = SimulationRequest(
                            s0=float(s0),
                            mu=float(mu),
                            sigma=float(sigma),
                            dt=1/252,  # Daily steps
                            t=30/252,  # 30 days
                            n_simulations=1000
                        )
                        
                        vectors = await self.simulation_bridge.generate_monte_carlo_vectors(sim_request)
                        
                        if vectors:
                            final_prices = [path[-1] for path in vectors if path]
                            
                            simulation_results[stock] = {
                                'correlation_with_etf': float(etf_correlations.get(stock, 0)),
                                'current_price': float(s0),
                                'simulated_mean_price': float(np.mean(final_prices)),
                                'simulated_std_price': float(np.std(final_prices)),
                                'simulation_paths': len(vectors),
                                'gbm_parameters': {
                                    'mu': float(mu),
                                    'sigma': float(sigma),
                                    's0': float(s0)
                                }
                            }
            
            return {
                'sector_etf': sector_etf,
                'sector_name': sector_info['name'],
                'analysis_period_days': analysis_period_days,
                'correlation_matrix': correlation_matrix.to_dict(),
                'component_relationships': simulation_results,
                'strongest_correlations': sorted(
                    etf_correlations.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:3]
            }
            
        except Exception as e:
            return {'error': str(e)}

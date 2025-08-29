import asyncio
import json
import logging
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, deque
import torch
import torch.nn as nn
from scipy import stats
from scipy.stats import pearsonr, spearmanr, kendalltau
import warnings
warnings.filterwarnings('ignore')

@dataclass
class CorrelationResult:
    """Results from option signal and trade outcome correlation analysis"""
    correlation_coefficient: float
    p_value: float
    correlation_type: str  # 'pearson', 'spearman', 'kendall'
    sample_size: int
    confidence_interval: Tuple[float, float]
    significance_level: float
    
@dataclass
class OptionSignalCorrelation:
    """Correlation between specific option signal and trade outcomes"""
    signal_name: str
    signal_values: List[float]
    trade_outcomes: List[float]
    correlation_result: CorrelationResult
    lag_analysis: Dict[int, float]  # lag -> correlation
    optimal_lag: int
    predictive_power: float

class OptionTradeCorrelationEngine:
    """
    Comprehensive correlation analysis between option signals and trade outcomes
    Implements multiple correlation methods and lag analysis for predictive insights
    """
    
    def __init__(self, max_memory_size: int = 5000, min_samples: int = 30):
        self.logger = logging.getLogger(__name__)
        self.max_memory_size = max_memory_size
        self.min_samples = min_samples
        
        self.signal_history = defaultdict(lambda: deque(maxlen=max_memory_size))
        self.outcome_history = defaultdict(lambda: deque(maxlen=max_memory_size))
        self.correlation_cache = {}
        self.last_analysis_time = {}
        
        self.correlation_methods = ['pearson', 'spearman', 'kendall']
        self.max_lag = 10  # Maximum lag periods to analyze
        self.significance_threshold = 0.05
        self.cache_duration = 300  # 5 minutes cache
    
    async def record_option_signal(self, symbol: str, signal_name: str, 
                                 signal_value: float, timestamp: float = None):
        """Record option signal value for correlation analysis"""
        try:
            if timestamp is None:
                timestamp = time.time()
                
            signal_key = f"{symbol}_{signal_name}"
            self.signal_history[signal_key].append({
                'value': signal_value,
                'timestamp': timestamp
            })
            
            self.logger.debug(f"Recorded option signal: {signal_key} = {signal_value}")
            
        except Exception as e:
            self.logger.error(f"Error recording option signal: {e}")
    
    async def record_trade_outcome(self, symbol: str, trade_id: str, 
                                 profit_loss: float, success: bool, 
                                 trade_duration_minutes: int, timestamp: float = None):
        """Record trade outcome for correlation analysis"""
        try:
            if timestamp is None:
                timestamp = time.time()
                
            outcome_key = f"{symbol}_outcomes"
            self.outcome_history[outcome_key].append({
                'trade_id': trade_id,
                'profit_loss': profit_loss,
                'success': success,
                'trade_duration_minutes': trade_duration_minutes,
                'timestamp': timestamp,
                'normalized_return': self._normalize_return(profit_loss, trade_duration_minutes)
            })
            
            self.logger.debug(f"Recorded trade outcome: {symbol} P&L={profit_loss:.4f}")
            
        except Exception as e:
            self.logger.error(f"Error recording trade outcome: {e}")
    
    def _normalize_return(self, profit_loss: float, duration_minutes: int) -> float:
        """Normalize return by time to enable fair comparison"""
        if duration_minutes <= 0:
            return profit_loss
        
        hours = duration_minutes / 60.0
        daily_return = profit_loss / max(hours / 24.0, 0.01)  # Avoid division by zero
        return daily_return
    
    async def compute_signal_outcome_correlation(self, symbol: str, signal_name: str,
                                               correlation_method: str = 'pearson',
                                               use_cache: bool = True) -> Optional[OptionSignalCorrelation]:
        """
        Compute correlation between specific option signal and trade outcomes
        Includes lag analysis to identify predictive relationships
        """
        try:
            signal_key = f"{symbol}_{signal_name}"
            outcome_key = f"{symbol}_outcomes"
            cache_key = f"{signal_key}_{correlation_method}"
            
            if use_cache and cache_key in self.correlation_cache:
                cache_entry = self.correlation_cache[cache_key]
                if time.time() - cache_entry['timestamp'] < self.cache_duration:
                    return cache_entry['result']
            
            signal_data = list(self.signal_history[signal_key])
            outcome_data = list(self.outcome_history[outcome_key])
            
            if len(signal_data) < self.min_samples or len(outcome_data) < self.min_samples:
                self.logger.warning(f"Insufficient data for correlation: {signal_key}")
                return None
            
            aligned_signals, aligned_outcomes = self._align_time_series(signal_data, outcome_data)
            
            if len(aligned_signals) < self.min_samples:
                return None
            
            correlation_result = self._compute_correlation(aligned_signals, aligned_outcomes, correlation_method)
            lag_analysis = self._compute_lag_correlations(aligned_signals, aligned_outcomes, correlation_method)
            optimal_lag = max(lag_analysis.items(), key=lambda x: abs(x[1]))[0] if lag_analysis else 0
            predictive_power = self._calculate_predictive_power(aligned_signals, aligned_outcomes, optimal_lag)
            
            option_correlation = OptionSignalCorrelation(
                signal_name=signal_name,
                signal_values=aligned_signals,
                trade_outcomes=aligned_outcomes,
                correlation_result=correlation_result,
                lag_analysis=lag_analysis,
                optimal_lag=optimal_lag,
                predictive_power=predictive_power
            )
            
            self.correlation_cache[cache_key] = {
                'result': option_correlation,
                'timestamp': time.time()
            }
            
            return option_correlation
            
        except Exception as e:
            self.logger.error(f"Error computing signal-outcome correlation: {e}")
            return None
    
    def _align_time_series(self, signal_data: List[Dict], outcome_data: List[Dict]) -> Tuple[List[float], List[float]]:
        """Align signal and outcome data by timestamp"""
        try:
            signal_data = sorted(signal_data, key=lambda x: x['timestamp'])
            outcome_data = sorted(outcome_data, key=lambda x: x['timestamp'])
            
            aligned_signals = []
            aligned_outcomes = []
            
            for signal in signal_data:
                signal_time = signal['timestamp']
                closest_outcome = None
                min_time_diff = float('inf')
                
                for outcome in outcome_data:
                    time_diff = abs(outcome['timestamp'] - signal_time)
                    if time_diff < min_time_diff and time_diff < 3600:  # Within 1 hour
                        min_time_diff = time_diff
                        closest_outcome = outcome
                
                if closest_outcome:
                    aligned_signals.append(signal['value'])
                    aligned_outcomes.append(closest_outcome['normalized_return'])
            
            return aligned_signals, aligned_outcomes
            
        except Exception as e:
            self.logger.error(f"Error aligning time series: {e}")
            return [], []
    
    def _compute_correlation(self, x: List[float], y: List[float], method: str) -> CorrelationResult:
        """Compute correlation using specified method"""
        try:
            x_array = np.array(x)
            y_array = np.array(y)
            
            if method == 'pearson':
                corr, p_value = pearsonr(x_array, y_array)
            elif method == 'spearman':
                corr, p_value = spearmanr(x_array, y_array)
            elif method == 'kendall':
                corr, p_value = kendalltau(x_array, y_array)
            else:
                raise ValueError(f"Unknown correlation method: {method}")
            
            n = len(x)
            z_score = 1.96  # 95% confidence
            se = 1.0 / np.sqrt(n - 3) if n > 3 else 1.0
            ci_lower = corr - z_score * se
            ci_upper = corr + z_score * se
            
            return CorrelationResult(
                correlation_coefficient=float(corr) if not np.isnan(corr) else 0.0,
                p_value=float(p_value) if not np.isnan(p_value) else 1.0,
                correlation_type=method,
                sample_size=n,
                confidence_interval=(ci_lower, ci_upper),
                significance_level=0.05
            )
            
        except Exception as e:
            self.logger.error(f"Error computing correlation: {e}")
            return CorrelationResult(0.0, 1.0, method, len(x), (0.0, 0.0), 0.05)
    
    def _compute_lag_correlations(self, x: List[float], y: List[float], method: str) -> Dict[int, float]:
        """Compute correlations at different lags"""
        try:
            lag_correlations = {}
            x_array = np.array(x)
            y_array = np.array(y)
            
            for lag in range(-self.max_lag, self.max_lag + 1):
                if lag == 0:
                    if method == 'pearson':
                        corr, _ = pearsonr(x_array, y_array)
                    elif method == 'spearman':
                        corr, _ = spearmanr(x_array, y_array)
                    else:
                        corr, _ = kendalltau(x_array, y_array)
                elif lag > 0:
                    if len(x_array) > lag:
                        x_lagged = x_array[:-lag]
                        y_lagged = y_array[lag:]
                        if len(x_lagged) > 5:  # Minimum samples for correlation
                            if method == 'pearson':
                                corr, _ = pearsonr(x_lagged, y_lagged)
                            elif method == 'spearman':
                                corr, _ = spearmanr(x_lagged, y_lagged)
                            else:
                                corr, _ = kendalltau(x_lagged, y_lagged)
                        else:
                            corr = 0.0
                    else:
                        corr = 0.0
                else:  # lag < 0
                    lag_abs = abs(lag)
                    if len(y_array) > lag_abs:
                        x_lagged = x_array[lag_abs:]
                        y_lagged = y_array[:-lag_abs]
                        if len(x_lagged) > 5:
                            if method == 'pearson':
                                corr, _ = pearsonr(x_lagged, y_lagged)
                            elif method == 'spearman':
                                corr, _ = spearmanr(x_lagged, y_lagged)
                            else:
                                corr, _ = kendalltau(x_lagged, y_lagged)
                        else:
                            corr = 0.0
                    else:
                        corr = 0.0
                
                lag_correlations[lag] = float(corr) if not np.isnan(corr) else 0.0
            
            return lag_correlations
            
        except Exception as e:
            self.logger.error(f"Error computing lag correlations: {e}")
            return {}
    
    def _calculate_predictive_power(self, x: List[float], y: List[float], optimal_lag: int) -> float:
        """Calculate predictive power based on correlation strength and significance"""
        try:
            if optimal_lag == 0:
                return 0.0
            
            x_array = np.array(x)
            y_array = np.array(y)
            
            if optimal_lag > 0 and len(x_array) > optimal_lag:
                x_lagged = x_array[:-optimal_lag]
                y_lagged = y_array[optimal_lag:]
                if len(x_lagged) > 5:
                    corr, p_value = pearsonr(x_lagged, y_lagged)
                    if not np.isnan(corr) and p_value < 0.05:
                        return abs(corr) * (1 - p_value)  # Weight by significance
            elif optimal_lag < 0:
                lag_abs = abs(optimal_lag)
                if len(y_array) > lag_abs:
                    x_lagged = x_array[lag_abs:]
                    y_lagged = y_array[:-lag_abs]
                    if len(x_lagged) > 5:
                        corr, p_value = pearsonr(x_lagged, y_lagged)
                        if not np.isnan(corr) and p_value < 0.05:
                            return abs(corr) * (1 - p_value)
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating predictive power: {e}")
            return 0.0
    
    def get_correlation_summary(self, symbol: str) -> Dict[str, Any]:
        """Get summary of all correlations for a symbol"""
        try:
            summary = {
                'symbol': symbol,
                'signal_count': 0,
                'outcome_count': 0,
                'significant_correlations': [],
                'top_predictive_signals': [],
                'timestamp': datetime.now().isoformat()
            }
            
            for key in self.signal_history:
                if key.startswith(f"{symbol}_"):
                    summary['signal_count'] += len(self.signal_history[key])
            
            outcome_key = f"{symbol}_outcomes"
            if outcome_key in self.outcome_history:
                summary['outcome_count'] = len(self.outcome_history[outcome_key])
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating correlation summary: {e}")
            return {'error': str(e)}

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time
from datetime import datetime, timedelta
import os
from pathlib import Path

class TechnicalIndicatorStorage:
    """
    Multi-resolution moving average storage with Arrow/Parquet optimization
    Supports <100ms query performance for peak/decline detection
    """
    
    def __init__(self, storage_path: str = "/tmp/quantroi_indicators"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.resolutions = {
            'minute': {'freq': '1min', 'retention_days': 7},
            'hourly': {'freq': '1H', 'retention_days': 30},
            'daily': {'freq': '1D', 'retention_days': 365},
            'weekly': {'freq': '1W', 'retention_days': 1095}  # 3 years
        }
        
        self.ma_configs = {
            'sma_20': {'type': 'simple', 'window': 20},
            'sma_50': {'type': 'simple', 'window': 50},
            'sma_180': {'type': 'simple', 'window': 180},
            'ema_12': {'type': 'exponential', 'span': 12},
            'ema_26': {'type': 'exponential', 'span': 26},
            'ema_50': {'type': 'exponential', 'span': 50}
        }
        
        self.indicator_configs = {
            'rsi_14': {'type': 'rsi', 'window': 14},
            'macd': {'type': 'macd', 'fast': 12, 'slow': 26, 'signal': 9},
            'bollinger': {'type': 'bollinger', 'window': 20, 'std': 2}
        }
        
        self.cache = {}
        
    async def compute_and_store_indicators(self, symbol: str, 
                                         price_data: pd.DataFrame,
                                         resolution: str = 'daily') -> Dict[str, Any]:
        """Compute and store technical indicators with multi-resolution support"""
        
        if resolution not in self.resolutions:
            return {'error': f'Unsupported resolution: {resolution}'}
        
        start_time = time.time()
        
        try:
            resampled_data = self._resample_data(price_data, resolution)
            
            ma_data = self._compute_moving_averages(resampled_data)
            
            indicator_data = self._compute_technical_indicators(resampled_data)
            
            combined_data = pd.concat([resampled_data, ma_data, indicator_data], axis=1)
            
            combined_data['symbol'] = symbol
            combined_data['resolution'] = resolution
            combined_data['computed_at'] = datetime.now()
            
            storage_result = await self._store_with_arrow(symbol, combined_data, resolution)
            
            cache_key = f"{symbol}_{resolution}"
            self.cache[cache_key] = {
                'data': combined_data.tail(1000),  # Keep last 1000 rows in cache
                'last_updated': datetime.now()
            }
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'symbol': symbol,
                'resolution': resolution,
                'indicators_computed': len(ma_data.columns) + len(indicator_data.columns),
                'data_points': len(combined_data),
                'processing_time_ms': processing_time,
                'storage_result': storage_result,
                'performance_target_met': processing_time < 100  # <100ms target
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _resample_data(self, data: pd.DataFrame, resolution: str) -> pd.DataFrame:
        """Resample price data to target resolution"""
        freq = self.resolutions[resolution]['freq']
        
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        resampled = data.resample(freq).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        return resampled
    
    def _compute_moving_averages(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute multiple moving averages"""
        ma_data = pd.DataFrame(index=data.index)
        
        for ma_name, config in self.ma_configs.items():
            if config['type'] == 'simple':
                ma_data[ma_name] = data['Close'].rolling(window=config['window']).mean()
            elif config['type'] == 'exponential':
                ma_data[ma_name] = data['Close'].ewm(span=config['span']).mean()
        
        return ma_data
    
    def _compute_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute technical indicators (RSI, MACD, Bollinger Bands)"""
        indicator_data = pd.DataFrame(index=data.index)
        
        if 'rsi_14' in self.indicator_configs:
            rsi_config = self.indicator_configs['rsi_14']
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_config['window']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_config['window']).mean()
            rs = gain / loss
            indicator_data['rsi_14'] = 100 - (100 / (1 + rs))
        
        if 'macd' in self.indicator_configs:
            macd_config = self.indicator_configs['macd']
            ema_fast = data['Close'].ewm(span=macd_config['fast']).mean()
            ema_slow = data['Close'].ewm(span=macd_config['slow']).mean()
            indicator_data['macd'] = ema_fast - ema_slow
            indicator_data['macd_signal'] = indicator_data['macd'].ewm(span=macd_config['signal']).mean()
            indicator_data['macd_histogram'] = indicator_data['macd'] - indicator_data['macd_signal']
        
        if 'bollinger' in self.indicator_configs:
            bb_config = self.indicator_configs['bollinger']
            sma = data['Close'].rolling(window=bb_config['window']).mean()
            std = data['Close'].rolling(window=bb_config['window']).std()
            indicator_data['bb_upper'] = sma + (std * bb_config['std'])
            indicator_data['bb_lower'] = sma - (std * bb_config['std'])
            indicator_data['bb_middle'] = sma
        
        return indicator_data
    
    async def _store_with_arrow(self, symbol: str, data: pd.DataFrame, 
                              resolution: str) -> Dict[str, Any]:
        """Store data using Arrow/Parquet for optimized queries"""
        try:
            table = pa.Table.from_pandas(data, preserve_index=True)
            
            partition_path = self.storage_path / resolution / symbol
            partition_path.mkdir(parents=True, exist_ok=True)
            
            filename = f"{symbol}_{resolution}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
            file_path = partition_path / filename
            
            pq.write_table(table, file_path, compression='snappy')
            
            await self._cleanup_old_files(partition_path, resolution)
            
            return {
                'file_path': str(file_path),
                'file_size_bytes': file_path.stat().st_size,
                'compression': 'snappy',
                'rows_stored': len(data)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _cleanup_old_files(self, partition_path: Path, resolution: str):
        """Clean up old files based on retention policy"""
        retention_days = self.resolutions[resolution]['retention_days']
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for file_path in partition_path.glob("*.parquet"):
            if file_path.stat().st_mtime < cutoff_date.timestamp():
                file_path.unlink()
    
    async def query_indicators_fast(self, symbol: str, resolution: str,
                                  start_time: Optional[datetime] = None,
                                  end_time: Optional[datetime] = None,
                                  indicators: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fast query with <100ms performance using cache and Arrow optimization"""
        query_start = time.time()
        
        try:
            cache_key = f"{symbol}_{resolution}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]['data']
                
                if start_time or end_time:
                    if start_time:
                        cached_data = cached_data[cached_data.index >= start_time]
                    if end_time:
                        cached_data = cached_data[cached_data.index <= end_time]
                
                if indicators:
                    available_indicators = [col for col in indicators if col in cached_data.columns]
                    cached_data = cached_data[available_indicators + ['symbol', 'resolution']]
                
                query_time = (time.time() - query_start) * 1000
                
                return {
                    'symbol': symbol,
                    'resolution': resolution,
                    'data': cached_data.to_dict('records'),
                    'data_points': len(cached_data),
                    'query_time_ms': query_time,
                    'cache_hit': True,
                    'performance_target_met': query_time < 100
                }
            
            partition_path = self.storage_path / resolution / symbol
            
            if not partition_path.exists():
                return {'error': f'No data found for {symbol} at {resolution} resolution'}
            
            parquet_files = list(partition_path.glob("*.parquet"))
            if not parquet_files:
                return {'error': f'No parquet files found for {symbol}'}
            
            latest_file = max(parquet_files, key=lambda p: p.stat().st_mtime)
            
            table = pq.read_table(latest_file)
            data = table.to_pandas()
            
            if start_time or end_time:
                if start_time:
                    data = data[data.index >= start_time]
                if end_time:
                    data = data[data.index <= end_time]
            
            if indicators:
                available_indicators = [col for col in indicators if col in data.columns]
                data = data[available_indicators + ['symbol', 'resolution']]
            
            query_time = (time.time() - query_start) * 1000
            
            return {
                'symbol': symbol,
                'resolution': resolution,
                'data': data.to_dict('records'),
                'data_points': len(data),
                'query_time_ms': query_time,
                'cache_hit': False,
                'performance_target_met': query_time < 100
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def detect_peaks_and_declines(self, symbol: str, resolution: str = 'daily',
                                      lookback_periods: int = 50) -> Dict[str, Any]:
        """Detect peaks and declines using multi-resolution moving averages"""
        
        query_result = await self.query_indicators_fast(
            symbol, resolution, 
            indicators=['sma_20', 'sma_50', 'sma_180', 'Close', 'rsi_14']
        )
        
        if 'error' in query_result:
            return query_result
        
        data = pd.DataFrame(query_result['data'])
        
        if len(data) < lookback_periods:
            return {'error': f'Insufficient data: {len(data)} < {lookback_periods}'}
        
        recent_data = data.tail(lookback_periods)
        
        prices = recent_data['Close'].values
        peaks = []
        declines = []
        
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                peaks.append({
                    'index': i,
                    'price': prices[i],
                    'timestamp': recent_data.index[i] if hasattr(recent_data, 'index') else i
                })
            elif prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                declines.append({
                    'index': i,
                    'price': prices[i],
                    'timestamp': recent_data.index[i] if hasattr(recent_data, 'index') else i
                })
        
        current_price = prices[-1]
        sma_20 = recent_data['sma_20'].iloc[-1] if 'sma_20' in recent_data.columns else None
        sma_50 = recent_data['sma_50'].iloc[-1] if 'sma_50' in recent_data.columns else None
        sma_180 = recent_data['sma_180'].iloc[-1] if 'sma_180' in recent_data.columns else None
        
        trend_analysis = {
            'current_price': current_price,
            'above_sma_20': current_price > sma_20 if sma_20 else None,
            'above_sma_50': current_price > sma_50 if sma_50 else None,
            'above_sma_180': current_price > sma_180 if sma_180 else None,
            'trend_direction': 'bullish' if (sma_20 and sma_50 and current_price > sma_20 > sma_50) else 'bearish'
        }
        
        return {
            'symbol': symbol,
            'resolution': resolution,
            'lookback_periods': lookback_periods,
            'peaks_detected': len(peaks),
            'declines_detected': len(declines),
            'peaks': peaks[-5:],  # Last 5 peaks
            'declines': declines[-5:],  # Last 5 declines
            'trend_analysis': trend_analysis,
            'query_performance': query_result.get('performance_target_met', False)
        }

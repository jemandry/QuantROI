import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import os

try:
    from batch_simulation_engine import BatchSimulationEngine
    from simulation_store import TimescaleSimulationStore
except ImportError:
    from .batch_simulation_engine import BatchSimulationEngine
    from .simulation_store import TimescaleSimulationStore

class BatchSimulationScheduler:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.batch_engine = BatchSimulationEngine()
        self.timescale_store = TimescaleSimulationStore()
        
        self.off_peak_hours = [22, 23, 0, 1, 2, 3, 4, 5]
        self.peak_hours = [9, 10, 11, 12, 13, 14, 15, 16]
        
        self.daily_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY', 'QQQ', 'NVDA', 'AMZN']
        self.weekly_symbols = self._load_extended_symbol_list()
        self.strategies = ['arbitrage', 'momentum', 'mean_reversion', 'volatility_breakout']
        
        self.running = False
        self.last_batch_run = None
        self.batch_statistics = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_simulations_processed': 0,
            'average_processing_time': 0.0,
            'cost_savings_estimate': 0.0
        }
    
    def _load_extended_symbol_list(self) -> List[str]:
        extended_symbols = [
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX',
            'JPM', 'JNJ', 'PG', 'UNH', 'HD', 'V', 'MA', 'DIS',
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'GLD',
            'GME', 'AMC', 'PLTR', 'RIVN', 'LCID', 'SOFI', 'HOOD', 'COIN',
            'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLU', 'XLP', 'XLRE'
        ]
        return extended_symbols
    
    async def initialize(self):
        await self.batch_engine.initialize()
        await self.timescale_store.initialize()
        self.logger.info("Batch simulation scheduler initialized")
    
    def start_scheduler(self):
        self.running = True
        
        schedule.every().day.at("02:00").do(self._schedule_daily_batch)
        schedule.every().sunday.at("01:00").do(self._schedule_weekly_batch)
        schedule.every().monday.at("17:00").do(self._schedule_market_close_analysis)
        schedule.every().tuesday.at("17:00").do(self._schedule_market_close_analysis)
        schedule.every().wednesday.at("17:00").do(self._schedule_market_close_analysis)
        schedule.every().thursday.at("17:00").do(self._schedule_market_close_analysis)
        schedule.every().friday.at("17:00").do(self._schedule_market_close_analysis)
        schedule.every(4).hours.do(self._check_volatility_triggers)
        
        self.logger.info("Batch simulation scheduler started")
        asyncio.create_task(self._scheduler_loop())
    
    async def _scheduler_loop(self):
        while self.running:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(300)
    
    def _schedule_daily_batch(self):
        asyncio.create_task(self._run_daily_batch())
    
    def _schedule_weekly_batch(self):
        asyncio.create_task(self._run_weekly_batch())
    
    def _schedule_market_close_analysis(self):
        asyncio.create_task(self._run_market_close_analysis())
    
    def _check_volatility_triggers(self):
        asyncio.create_task(self._run_volatility_triggered_batch())
    
    async def _run_daily_batch(self):
        try:
            self.logger.info("Starting daily batch simulation run")
            
            start_time = time.time()
            
            result = await self.batch_engine.run_batch_simulations(
                symbols=self.daily_symbols,
                strategies=self.strategies,
                trigger_type="daily_scheduled"
            )
            
            processing_time = time.time() - start_time
            self._update_batch_statistics(result, processing_time, "daily")
            
            self.logger.info(f"Daily batch completed: {result.get('total_simulations', 0)} simulations in {processing_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in daily batch run: {e}")
            self.batch_statistics['failed_runs'] += 1
    
    async def _run_weekly_batch(self):
        try:
            self.logger.info("Starting weekly comprehensive batch simulation run")
            
            start_time = time.time()
            
            result = await self.batch_engine.run_batch_simulations(
                symbols=self.weekly_symbols,
                strategies=self.strategies + ['pairs_trading', 'sector_rotation'],
                trigger_type="weekly_comprehensive"
            )
            
            processing_time = time.time() - start_time
            self._update_batch_statistics(result, processing_time, "weekly")
            
            self.logger.info(f"Weekly batch completed: {result.get('total_simulations', 0)} simulations in {processing_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in weekly batch run: {e}")
            self.batch_statistics['failed_runs'] += 1
    
    async def _run_market_close_analysis(self):
        try:
            self.logger.info("Starting market close analysis batch")
            
            high_volume_symbols = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']
            
            result = await self.batch_engine.run_batch_simulations(
                symbols=high_volume_symbols,
                strategies=['momentum', 'mean_reversion'],
                trigger_type="market_close_analysis"
            )
            
            self.logger.info(f"Market close analysis completed: {result.get('total_simulations', 0)} simulations")
            
        except Exception as e:
            self.logger.error(f"Error in market close analysis: {e}")
    
    async def _run_volatility_triggered_batch(self):
        try:
            current_hour = datetime.now().hour
            
            if current_hour in self.peak_hours:
                volatile_symbols = ['TSLA', 'NVDA', 'GME', 'AMC']
                
                result = await self.batch_engine.run_batch_simulations(
                    symbols=volatile_symbols,
                    strategies=['volatility_breakout', 'momentum'],
                    trigger_type="volatility_triggered"
                )
                
                if result.get('total_simulations', 0) > 0:
                    self.logger.info(f"Volatility-triggered batch completed: {result.get('total_simulations', 0)} simulations")
            
        except Exception as e:
            self.logger.error(f"Error in volatility-triggered batch: {e}")
    
    def _update_batch_statistics(self, result: Dict[str, Any], processing_time: float, batch_type: str):
        try:
            self.batch_statistics['total_runs'] += 1
            
            if 'error' not in result:
                self.batch_statistics['successful_runs'] += 1
                self.batch_statistics['total_simulations_processed'] += result.get('total_simulations', 0)
                
                total_time = self.batch_statistics['average_processing_time'] * (self.batch_statistics['total_runs'] - 1)
                self.batch_statistics['average_processing_time'] = (total_time + processing_time) / self.batch_statistics['total_runs']
                
                estimated_real_time_cost = result.get('total_simulations', 0) * 0.01
                batch_cost = estimated_real_time_cost * 0.3
                savings = estimated_real_time_cost - batch_cost
                self.batch_statistics['cost_savings_estimate'] += savings
            else:
                self.batch_statistics['failed_runs'] += 1
            
            self.last_batch_run = {
                'timestamp': datetime.now().isoformat(),
                'batch_type': batch_type,
                'result': result,
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Error updating batch statistics: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        return {
            'running': self.running,
            'last_batch_run': self.last_batch_run,
            'statistics': self.batch_statistics,
            'next_scheduled_runs': {
                'daily_batch': "02:00 daily",
                'weekly_batch': "01:00 Sunday",
                'market_close': "17:00 weekdays"
            },
            'economic_efficiency': {
                'estimated_monthly_savings': f"${self.batch_statistics['cost_savings_estimate']:.2f}",
                'processing_efficiency': f"{self.batch_statistics['average_processing_time']:.2f}s avg",
                'success_rate': f"{(self.batch_statistics['successful_runs'] / max(self.batch_statistics['total_runs'], 1)) * 100:.1f}%"
            }
        }
    
    def stop_scheduler(self):
        self.running = False
        schedule.clear()
        self.logger.info("Batch simulation scheduler stopped")

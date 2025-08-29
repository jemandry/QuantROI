import asyncio
import logging
import numpy as np
import torch
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from dataclasses import dataclass

try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logging.warning("Ray not available - using standard multiprocessing")

try:
    from phase2_ai_enhancement_engine import Phase2AIEnhancementEngine
except ImportError:
    try:
        from .phase2_ai_enhancement_engine import Phase2AIEnhancementEngine
    except ImportError:
        Phase2AIEnhancementEngine = None

@dataclass
class ProcessingTask:
    task_id: str
    event_data: Dict[str, Any]
    priority: int = 1  # 1=high, 2=medium, 3=low
    processing_type: str = 'full'  # 'full', 'causal_only', 'option_only'
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class DistributedAIProcessor:
    """
    Distributed AI processor for scalable Phase 2 AI workloads
    Supports both Ray and standard multiprocessing for different deployment scenarios
    """
    
    def __init__(self, num_workers: int = None, use_ray: bool = None):
        self.logger = logging.getLogger(__name__)
        
        self.num_workers = num_workers or min(8, mp.cpu_count())
        self.use_ray = use_ray if use_ray is not None else RAY_AVAILABLE
        
        if self.use_ray and RAY_AVAILABLE:
            if not ray.is_initialized():
                ray.init(ignore_reinit_error=True)
            self.logger.info(f"Initialized Ray with {self.num_workers} workers")
        else:
            self.use_ray = False
            self.logger.info(f"Using standard multiprocessing with {self.num_workers} workers")
        
        self.task_queue = asyncio.Queue(maxsize=1000)
        self.result_cache = {}
        self.processing_stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'average_processing_time': 0.0,
            'worker_utilization': 0.0
        }
        
        if not self.use_ray:
            self.thread_pool = ThreadPoolExecutor(max_workers=self.num_workers)
            self.process_pool = ProcessPoolExecutor(max_workers=max(2, self.num_workers // 2))
        
        self.is_running = False
        self.worker_tasks = []
        
        self.logger.info(f"Distributed AI Processor initialized with {self.num_workers} workers")
    
    async def start_processing(self):
        """Start distributed processing workers"""
        self.is_running = True
        
        for i in range(self.num_workers):
            if self.use_ray:
                worker_task = asyncio.create_task(self._ray_worker(f"worker_{i}"))
            else:
                worker_task = asyncio.create_task(self._standard_worker(f"worker_{i}"))
            self.worker_tasks.append(worker_task)
        
        monitor_task = asyncio.create_task(self._monitor_performance())
        self.worker_tasks.append(monitor_task)
        
        self.logger.info(f"Started {len(self.worker_tasks)} distributed processing workers")
    
    async def submit_task(self, event_data: Dict[str, Any], priority: int = 1, 
                         processing_type: str = 'full') -> str:
        """Submit a processing task to the distributed queue"""
        task_id = f"task_{int(time.time() * 1000000)}_{hash(str(event_data)) % 10000}"
        
        task = ProcessingTask(
            task_id=task_id,
            event_data=event_data,
            priority=priority,
            processing_type=processing_type
        )
        
        try:
            await self.task_queue.put(task)
            self.logger.debug(f"Submitted task {task_id} with priority {priority}")
            return task_id
        except asyncio.QueueFull:
            self.logger.warning(f"Task queue full, rejecting task {task_id}")
            raise Exception("Processing queue is full")
    
    async def get_result(self, task_id: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Get processing result for a task"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if task_id in self.result_cache:
                result = self.result_cache.pop(task_id)
                return result
            
            await asyncio.sleep(0.1)
        
        self.logger.warning(f"Timeout waiting for result of task {task_id}")
        return None
    
    async def _ray_worker(self, worker_id: str):
        """Ray-based distributed worker"""
        if not self.use_ray:
            return
        
        self.logger.info(f"Starting Ray worker {worker_id}")
        
        while self.is_running:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                start_time = time.time()
                
                if task.processing_type == 'full':
                    result = await self._process_full_ray(task.event_data)
                elif task.processing_type == 'causal_only':
                    result = await self._process_causal_ray(task.event_data)
                elif task.processing_type == 'option_only':
                    result = await self._process_option_ray(task.event_data)
                else:
                    result = {'error': f'Unknown processing type: {task.processing_type}'}
                
                processing_time = time.time() - start_time
                
                self.result_cache[task.task_id] = {
                    'result': result,
                    'processing_time': processing_time,
                    'worker_id': worker_id,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.processing_stats['tasks_processed'] += 1
                self._update_processing_stats(processing_time)
                
                self.logger.debug(f"Worker {worker_id} completed task {task.task_id} in {processing_time:.3f}s")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in Ray worker {worker_id}: {e}")
                self.processing_stats['tasks_failed'] += 1
                await asyncio.sleep(1.0)
    
    async def _standard_worker(self, worker_id: str):
        """Standard multiprocessing worker"""
        self.logger.info(f"Starting standard worker {worker_id}")
        
        while self.is_running:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                start_time = time.time()
                
                if task.processing_type == 'full':
                    result = await self._process_full_standard(task.event_data)
                elif task.processing_type == 'causal_only':
                    result = await self._process_causal_standard(task.event_data)
                elif task.processing_type == 'option_only':
                    result = await self._process_option_standard(task.event_data)
                else:
                    result = {'error': f'Unknown processing type: {task.processing_type}'}
                
                processing_time = time.time() - start_time
                
                self.result_cache[task.task_id] = {
                    'result': result,
                    'processing_time': processing_time,
                    'worker_id': worker_id,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.processing_stats['tasks_processed'] += 1
                self._update_processing_stats(processing_time)
                
                self.logger.debug(f"Worker {worker_id} completed task {task.task_id} in {processing_time:.3f}s")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in standard worker {worker_id}: {e}")
                self.processing_stats['tasks_failed'] += 1
                await asyncio.sleep(1.0)
    
    async def _process_full_ray(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process full AI pipeline using Ray"""
        if not self.use_ray:
            return {'error': 'Ray not available'}
        
        try:
            engine = Phase2AIEnhancementEngine()
            result = await engine.process_enhanced_market_event(event_data)
            await engine.shutdown()
            return result
        except Exception as e:
            return {'error': str(e)}
    
    async def _process_full_standard(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process full AI pipeline using standard multiprocessing"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool, 
                self._sync_process_full, 
                event_data
            )
            return result
        except Exception as e:
            return {'error': str(e)}
    
    def _sync_process_full(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous full processing for thread pool"""
        try:
            engine = Phase2AIEnhancementEngine()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(engine.process_enhanced_market_event(event_data))
                loop.run_until_complete(engine.shutdown())
                return result
            finally:
                loop.close()
                
        except Exception as e:
            return {'error': str(e)}
    
    async def _process_causal_ray(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process only causal analysis using Ray"""
        try:
            engine = Phase2AIEnhancementEngine()
            result = await engine._analyze_temporal_causality(event_data)
            await engine.shutdown()
            return result
        except Exception as e:
            return {'error': str(e)}
    
    async def _process_causal_standard(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process only causal analysis using standard processing"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._sync_process_causal,
                event_data
            )
            return result
        except Exception as e:
            return {'error': str(e)}
    
    def _sync_process_causal(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous causal processing for thread pool"""
        try:
            engine = Phase2AIEnhancementEngine()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(engine._analyze_temporal_causality(event_data))
                loop.run_until_complete(engine.shutdown())
                return result
            finally:
                loop.close()
                
        except Exception as e:
            return {'error': str(e)}
    
    async def _process_option_ray(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process only option analysis using Ray"""
        try:
            engine = Phase2AIEnhancementEngine()
            result = await engine._analyze_option_signals(event_data)
            await engine.shutdown()
            return result
        except Exception as e:
            return {'error': str(e)}
    
    async def _process_option_standard(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process only option analysis using standard processing"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._sync_process_option,
                event_data
            )
            return result
        except Exception as e:
            return {'error': str(e)}
    
    def _sync_process_option(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous option processing for thread pool"""
        try:
            engine = Phase2AIEnhancementEngine()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(engine._analyze_option_signals(event_data))
                loop.run_until_complete(engine.shutdown())
                return result
            finally:
                loop.close()
                
        except Exception as e:
            return {'error': str(e)}
    
    async def _monitor_performance(self):
        """Monitor worker performance and utilization"""
        while self.is_running:
            try:
                active_tasks = self.task_queue.qsize()
                max_tasks = self.task_queue.maxsize
                utilization = active_tasks / max_tasks if max_tasks > 0 else 0.0
                
                self.processing_stats['worker_utilization'] = utilization
                
                if self.processing_stats['tasks_processed'] % 100 == 0 and self.processing_stats['tasks_processed'] > 0:
                    self.logger.info(
                        f"Processed {self.processing_stats['tasks_processed']} tasks, "
                        f"avg time: {self.processing_stats['average_processing_time']:.3f}s, "
                        f"utilization: {utilization:.2%}, "
                        f"failures: {self.processing_stats['tasks_failed']}"
                    )
                
                await asyncio.sleep(10.0)  # Monitor every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(10.0)
    
    def _update_processing_stats(self, processing_time: float):
        """Update processing statistics"""
        current_avg = self.processing_stats['average_processing_time']
        total_tasks = self.processing_stats['tasks_processed']
        
        new_avg = ((current_avg * (total_tasks - 1)) + processing_time) / total_tasks
        self.processing_stats['average_processing_time'] = new_avg
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return {
            'stats': self.processing_stats.copy(),
            'queue_size': self.task_queue.qsize(),
            'queue_capacity': self.task_queue.maxsize,
            'active_workers': len(self.worker_tasks),
            'use_ray': self.use_ray,
            'num_workers': self.num_workers,
            'is_running': self.is_running
        }
    
    async def shutdown(self):
        """Shutdown distributed processing"""
        self.logger.info("Shutting down distributed AI processor")
        
        self.is_running = False
        
        for task in self.worker_tasks:
            task.cancel()
        
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        if not self.use_ray:
            self.thread_pool.shutdown(wait=True)
            self.process_pool.shutdown(wait=True)
        
        if self.use_ray and RAY_AVAILABLE:
            ray.shutdown()
        
        self.logger.info("Distributed AI processor shutdown complete")

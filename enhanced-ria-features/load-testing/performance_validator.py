#!/usr/bin/env python3
"""
Load Testing Infrastructure for 20K+ Events/Second Validation
Comprehensive performance testing with real market data simulation
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import aiokafka
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import statistics

logger = logging.getLogger(__name__)

@dataclass
class LoadTestConfig:
    target_rps: int = 20000
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    concurrent_users: int = 1000
    endpoints: List[str] = None
    kafka_topics: List[str] = None

@dataclass
class PerformanceMetrics:
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    requests_per_second: float
    error_rate: float
    throughput_achieved: bool

class PerformanceValidator:
    """Comprehensive load testing and performance validation"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results = []
        self.start_time = None
        self.end_time = None
        
        if not self.config.endpoints:
            self.config.endpoints = [
                'http://localhost:8000/api/v1/causal/discovery',
                'http://localhost:8000/api/v1/causal/intervention',
                'http://localhost:8000/api/v1/causal/regime-detection',
                'http://localhost:8000/api/v1/causal/explanations'
            ]
        
        if not self.config.kafka_topics:
            self.config.kafka_topics = [
                'market-events',
                'causal-events',
                'trading-signals'
            ]
    
    async def run_comprehensive_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load test covering all components"""
        logger.info(f"Starting comprehensive load test: {self.config.target_rps} RPS for {self.config.duration_seconds}s")
        
        results = {}
        
        logger.info("Running HTTP API load test...")
        results['http_api'] = await self.run_http_load_test()
        
        logger.info("Running Kafka event load test...")
        results['kafka_events'] = await self.run_kafka_load_test()
        
        logger.info("Running real-time pipeline test...")
        results['real_time_pipeline'] = await self.run_pipeline_load_test()
        
        logger.info("Running memory hierarchy load test...")
        results['memory_hierarchy'] = await self.run_memory_hierarchy_test()
        
        logger.info("Running causal AI performance test...")
        results['causal_ai'] = await self.run_causal_ai_test()
        
        report = self.generate_performance_report(results)
        
        return report
    
    async def run_http_load_test(self) -> PerformanceMetrics:
        """Load test HTTP API endpoints"""
        self.start_time = time.time()
        
        semaphore = asyncio.Semaphore(self.config.concurrent_users)
        
        test_requests = self.generate_test_requests()
        
        tasks = []
        for i in range(self.config.target_rps * self.config.duration_seconds):
            task = asyncio.create_task(
                self.make_http_request(semaphore, test_requests[i % len(test_requests)])
            )
            tasks.append(task)
            
            if i > 0 and i % self.config.target_rps == 0:
                await asyncio.sleep(1)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.end_time = time.time()
        
        return self.calculate_metrics(results)
    
    async def run_kafka_load_test(self) -> PerformanceMetrics:
        """Load test Kafka event processing"""
        producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=['localhost:9092'],
            compression_type='snappy'
        )
        
        await producer.start()
        
        try:
            start_time = time.time()
            
            events = self.generate_kafka_events()
            
            tasks = []
            for i, event in enumerate(events):
                task = asyncio.create_task(
                    producer.send(
                        self.config.kafka_topics[i % len(self.config.kafka_topics)],
                        json.dumps(event).encode('utf-8')
                    )
                )
                tasks.append(task)
                
                if i > 0 and i % self.config.target_rps == 0:
                    await asyncio.sleep(1)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            
            successful = len([r for r in results if not isinstance(r, Exception)])
            failed = len(results) - successful
            
            return PerformanceMetrics(
                total_requests=len(results),
                successful_requests=successful,
                failed_requests=failed,
                average_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                max_latency_ms=0.0,
                requests_per_second=len(results) / (end_time - start_time),
                error_rate=failed / len(results) if results else 0.0,
                throughput_achieved=successful >= self.config.target_rps * self.config.duration_seconds * 0.95
            )
            
        finally:
            await producer.stop()
    
    async def run_pipeline_load_test(self) -> PerformanceMetrics:
        """Test real-time pipeline performance"""
        start_time = time.time()
        
        events = []
        for i in range(self.config.target_rps * self.config.duration_seconds):
            event = {
                'event_id': f'market_event_{i}',
                'timestamp': datetime.now().isoformat(),
                'event_type': 'market_update',
                'source': 'test_generator',
                'data': {
                    'symbol': f'TEST{i % 100}',
                    'price': 100 + np.random.normal(0, 5),
                    'volume': np.random.randint(1000, 10000),
                    'bid': 99.5 + np.random.normal(0, 2),
                    'ask': 100.5 + np.random.normal(0, 2)
                },
                'priority': 1 if i % 10 == 0 else 2
            }
            events.append(event)
        
        latencies = []
        successful = 0
        failed = 0
        
        async with aiohttp.ClientSession() as session:
            for event in events:
                try:
                    event_start = time.time()
                    
                    async with session.post(
                        'http://localhost:8000/api/v1/events/process',
                        json=event,
                        timeout=aiohttp.ClientTimeout(total=1.0)
                    ) as response:
                        if response.status == 200:
                            successful += 1
                        else:
                            failed += 1
                        
                        latency = (time.time() - event_start) * 1000
                        latencies.append(latency)
                
                except Exception:
                    failed += 1
        
        end_time = time.time()
        
        return PerformanceMetrics(
            total_requests=len(events),
            successful_requests=successful,
            failed_requests=failed,
            average_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0.0,
            p99_latency_ms=np.percentile(latencies, 99) if latencies else 0.0,
            max_latency_ms=max(latencies) if latencies else 0.0,
            requests_per_second=len(events) / (end_time - start_time),
            error_rate=failed / len(events) if events else 0.0,
            throughput_achieved=successful >= self.config.target_rps * self.config.duration_seconds * 0.95
        )
    
    async def run_memory_hierarchy_test(self) -> PerformanceMetrics:
        """Test memory hierarchy performance"""
        start_time = time.time()
        
        latencies = []
        successful = 0
        failed = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(10000):
                try:
                    operation_start = time.time()
                    
                    if i % 3 == 0:
                        url = f'http://localhost:8004/api/v1/memory/hot/get/key_{i % 100}'
                    elif i % 3 == 1:
                        url = f'http://localhost:8004/api/v1/memory/warm/get/key_{i % 1000}'
                    else:
                        url = f'http://localhost:8004/api/v1/memory/cold/get/key_{i % 10000}'
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            successful += 1
                        else:
                            failed += 1
                        
                        latency = (time.time() - operation_start) * 1000000
                        latencies.append(latency)
                
                except Exception:
                    failed += 1
        
        end_time = time.time()
        
        return PerformanceMetrics(
            total_requests=10000,
            successful_requests=successful,
            failed_requests=failed,
            average_latency_ms=statistics.mean(latencies) / 1000 if latencies else 0.0,
            p95_latency_ms=np.percentile(latencies, 95) / 1000 if latencies else 0.0,
            p99_latency_ms=np.percentile(latencies, 99) / 1000 if latencies else 0.0,
            max_latency_ms=max(latencies) / 1000 if latencies else 0.0,
            requests_per_second=10000 / (end_time - start_time),
            error_rate=failed / 10000,
            throughput_achieved=statistics.mean(latencies) < 50 if latencies else False
        )
    
    async def run_causal_ai_test(self) -> PerformanceMetrics:
        """Test causal AI performance with accuracy validation"""
        start_time = time.time()
        
        test_data = self.generate_causal_test_data()
        
        latencies = []
        successful = 0
        failed = 0
        accuracy_scores = []
        
        async with aiohttp.ClientSession() as session:
            for data in test_data:
                try:
                    operation_start = time.time()
                    
                    async with session.post(
                        'http://localhost:8000/api/v1/causal/discovery',
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            successful += 1
                            
                            accuracy = result.get('causal_discovery_result', {}).get('discovery_accuracy', 0.0)
                            accuracy_scores.append(accuracy)
                        else:
                            failed += 1
                        
                        latency = (time.time() - operation_start) * 1000
                        latencies.append(latency)
                
                except Exception:
                    failed += 1
        
        end_time = time.time()
        
        avg_accuracy = statistics.mean(accuracy_scores) if accuracy_scores else 0.0
        accuracy_target_met = avg_accuracy > 0.85
        
        return PerformanceMetrics(
            total_requests=len(test_data),
            successful_requests=successful,
            failed_requests=failed,
            average_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0.0,
            p99_latency_ms=np.percentile(latencies, 99) if latencies else 0.0,
            max_latency_ms=max(latencies) if latencies else 0.0,
            requests_per_second=len(test_data) / (end_time - start_time),
            error_rate=failed / len(test_data) if test_data else 0.0,
            throughput_achieved=accuracy_target_met and statistics.mean(latencies) < 100 if latencies else False
        )
    
    def generate_test_requests(self) -> List[Dict[str, Any]]:
        """Generate test requests for HTTP load testing"""
        requests = []
        
        for i in range(1000):
            requests.append({
                'url': 'http://localhost:8000/api/v1/causal/discovery',
                'method': 'POST',
                'data': {
                    'data': {
                        'X': np.random.randn(100).tolist(),
                        'Y': np.random.randn(100).tolist(),
                        'Z': np.random.randn(100).tolist()
                    },
                    'method': 'pc',
                    'significance_level': 0.05
                }
            })
            
            requests.append({
                'url': 'http://localhost:8000/api/v1/causal/intervention',
                'method': 'POST',
                'data': {
                    'data': {
                        'treatment': np.random.randn(100).tolist(),
                        'outcome': np.random.randn(100).tolist()
                    },
                    'treatment': 'treatment',
                    'outcome': 'outcome',
                    'intervention_value': 1.0
                }
            })
        
        return requests
    
    def generate_kafka_events(self) -> List[Dict[str, Any]]:
        """Generate Kafka events for load testing"""
        events = []
        
        for i in range(self.config.target_rps * self.config.duration_seconds):
            event = {
                'event_id': f'load_test_event_{i}',
                'timestamp': datetime.now().isoformat(),
                'event_type': 'market_update',
                'source': 'load_test',
                'data': {
                    'symbol': f'TEST{i % 100}',
                    'price': 100 + np.random.normal(0, 5),
                    'volume': np.random.randint(1000, 10000)
                },
                'priority': np.random.choice([1, 2, 3], p=[0.1, 0.6, 0.3])
            }
            events.append(event)
        
        return events
    
    def generate_causal_test_data(self) -> List[Dict[str, Any]]:
        """Generate test data for causal AI validation"""
        test_data = []
        
        for i in range(100):
            n_samples = 200
            X = np.random.normal(0, 1, n_samples)
            Y = 0.5 * X + np.random.normal(0, 0.5, n_samples)
            Z = 0.3 * Y + np.random.normal(0, 0.3, n_samples)
            
            test_data.append({
                'data': {
                    'X': X.tolist(),
                    'Y': Y.tolist(),
                    'Z': Z.tolist()
                },
                'method': 'pc',
                'significance_level': 0.05
            })
        
        return test_data
    
    async def make_http_request(self, semaphore: asyncio.Semaphore, request: Dict[str, Any]) -> Dict[str, Any]:
        """Make a single HTTP request with timing"""
        async with semaphore:
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        request['method'],
                        request['url'],
                        json=request.get('data'),
                        timeout=aiohttp.ClientTimeout(total=5.0)
                    ) as response:
                        end_time = time.time()
                        
                        return {
                            'success': response.status == 200,
                            'status_code': response.status,
                            'latency_ms': (end_time - start_time) * 1000,
                            'timestamp': start_time
                        }
            
            except Exception as e:
                end_time = time.time()
                return {
                    'success': False,
                    'status_code': 0,
                    'latency_ms': (end_time - start_time) * 1000,
                    'error': str(e),
                    'timestamp': start_time
                }
    
    def calculate_metrics(self, results: List[Dict[str, Any]]) -> PerformanceMetrics:
        """Calculate performance metrics from results"""
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_results = [r for r in results if not (isinstance(r, dict) and r.get('success', False))]
        
        latencies = [r['latency_ms'] for r in successful_results]
        
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 1
        
        return PerformanceMetrics(
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            average_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0.0,
            p99_latency_ms=np.percentile(latencies, 99) if latencies else 0.0,
            max_latency_ms=max(latencies) if latencies else 0.0,
            requests_per_second=len(results) / total_time,
            error_rate=len(failed_results) / len(results) if results else 0.0,
            throughput_achieved=len(successful_results) >= self.config.target_rps * self.config.duration_seconds * 0.95
        )
    
    def generate_performance_report(self, results: Dict[str, PerformanceMetrics]) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'test_config': {
                'target_rps': self.config.target_rps,
                'duration_seconds': self.config.duration_seconds,
                'concurrent_users': self.config.concurrent_users
            },
            'overall_results': {},
            'component_results': {},
            'performance_targets_met': {},
            'recommendations': []
        }
        
        for component, metrics in results.items():
            report['component_results'][component] = {
                'requests_per_second': metrics.requests_per_second,
                'average_latency_ms': metrics.average_latency_ms,
                'p95_latency_ms': metrics.p95_latency_ms,
                'error_rate': metrics.error_rate,
                'throughput_achieved': metrics.throughput_achieved
            }
            
            if component == 'http_api':
                report['performance_targets_met'][component] = {
                    'throughput': metrics.requests_per_second >= 20000,
                    'latency': metrics.p95_latency_ms < 100,
                    'error_rate': metrics.error_rate < 0.01
                }
            elif component == 'memory_hierarchy':
                report['performance_targets_met'][component] = {
                    'latency': metrics.average_latency_ms < 0.05,
                    'error_rate': metrics.error_rate < 0.001
                }
            elif component == 'causal_ai':
                report['performance_targets_met'][component] = {
                    'latency': metrics.average_latency_ms < 100,
                    'accuracy': metrics.throughput_achieved,
                    'error_rate': metrics.error_rate < 0.05
                }
        
        all_targets_met = all(
            all(targets.values()) 
            for targets in report['performance_targets_met'].values()
        )
        
        report['overall_results'] = {
            'all_performance_targets_met': all_targets_met,
            'ready_for_production': all_targets_met,
            'test_timestamp': datetime.now().isoformat()
        }
        
        if not all_targets_met:
            for component, targets in report['performance_targets_met'].items():
                for target, met in targets.items():
                    if not met:
                        report['recommendations'].append(
                            f"Optimize {component} {target} performance"
                        )
        
        return report

async def main():
    """Main function for running load tests"""
    config = LoadTestConfig(
        target_rps=20000,
        duration_seconds=60,
        concurrent_users=1000
    )
    
    validator = PerformanceValidator(config)
    report = await validator.run_comprehensive_load_test()
    
    with open('performance_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Performance Test Results:")
    print(f"All targets met: {report['overall_results']['all_performance_targets_met']}")
    print(f"Ready for production: {report['overall_results']['ready_for_production']}")
    
    if report['recommendations']:
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"- {rec}")

if __name__ == "__main__":
    asyncio.run(main())

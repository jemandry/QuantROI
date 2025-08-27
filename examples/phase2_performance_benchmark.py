import asyncio
import time
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor
import requests
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Phase2PerformanceBenchmark:
    """Performance benchmark for Phase 2 components"""
    
    def __init__(self):
        self.base_urls = {
            'nlp_voice': 'http://localhost:8004',
            'auto_agent': 'http://localhost:8005',
            'simulation_engine': 'http://localhost:8006'
        }
        self.results = {}
    
    def benchmark_nlp_voice_interface(self, num_requests=100):
        """Benchmark NLP/Voice interface performance"""
        print(f"\n=== Benchmarking NLP/Voice Interface ({num_requests} requests) ===")
        
        queries = [
            "predict stock price for AAPL",
            "analyze VIX impact on Microsoft",
            "forecast volatility for GOOGL",
            "what is the system status",
            "get performance metrics"
        ]
        
        latencies = []
        errors = 0
        
        for i in range(num_requests):
            query = queries[i % len(queries)]
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{self.base_urls['nlp_voice']}/process_query",
                    json={"query": query},
                    timeout=5
                )
                latency = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    latencies.append(latency)
                else:
                    errors += 1
                    
            except Exception as e:
                errors += 1
                logger.error(f"NLP request {i} failed: {e}")
        
        if latencies:
            self.results['nlp_voice'] = {
                'avg_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': statistics.quantiles(latencies, n=20)[18],
                'p99_latency_ms': statistics.quantiles(latencies, n=100)[98],
                'min_latency_ms': min(latencies),
                'max_latency_ms': max(latencies),
                'success_rate': (len(latencies) / num_requests) * 100,
                'errors': errors,
                'total_requests': num_requests
            }
            
            print(f"  Average latency: {self.results['nlp_voice']['avg_latency_ms']:.2f}ms")
            print(f"  P95 latency: {self.results['nlp_voice']['p95_latency_ms']:.2f}ms")
            print(f"  Success rate: {self.results['nlp_voice']['success_rate']:.1f}%")
    
    def benchmark_auto_agent(self, num_requests=50):
        """Benchmark Auto-Agent system performance"""
        print(f"\n=== Benchmarking Auto-Agent System ({num_requests} requests) ===")
        
        test_cases = [
            {
                'endpoint': '/detect_gaps',
                'payload': {'symbols': ['AAPL', 'MSFT'], 'timeframes': ['1D', '1h']}
            },
            {
                'endpoint': '/predict_vix',
                'payload': {'symbol': 'AAPL', 'timeframe': '1D'}
            },
            {
                'endpoint': '/resolve_gap',
                'payload': {'symbol': 'AAPL', 'timeframe': '1D', 'gap_type': 'data_missing', 'severity': 0.8}
            }
        ]
        
        latencies = []
        errors = 0
        
        for i in range(num_requests):
            test_case = test_cases[i % len(test_cases)]
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{self.base_urls['auto_agent']}{test_case['endpoint']}",
                    json=test_case['payload'],
                    timeout=10
                )
                latency = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    latencies.append(latency)
                else:
                    errors += 1
                    
            except Exception as e:
                errors += 1
                logger.error(f"Auto-agent request {i} failed: {e}")
        
        if latencies:
            self.results['auto_agent'] = {
                'avg_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': statistics.quantiles(latencies, n=20)[18],
                'min_latency_ms': min(latencies),
                'max_latency_ms': max(latencies),
                'success_rate': (len(latencies) / num_requests) * 100,
                'errors': errors,
                'total_requests': num_requests
            }
            
            print(f"  Average latency: {self.results['auto_agent']['avg_latency_ms']:.2f}ms")
            print(f"  P95 latency: {self.results['auto_agent']['p95_latency_ms']:.2f}ms")
            print(f"  Success rate: {self.results['auto_agent']['success_rate']:.1f}%")
    
    def benchmark_simulation_engine(self, num_requests=30):
        """Benchmark Simulation Engine performance"""
        print(f"\n=== Benchmarking Simulation Engine ({num_requests} requests) ===")
        
        test_cases = [
            {
                'endpoint': '/simulate_gbm',
                'payload': {'s0': 100.0, 'mu': 0.05, 'sigma': 0.2, 'dt': 0.01, 't': 1.0}
            },
            {
                'endpoint': '/monte_carlo_vectors',
                'payload': {'s0': 100.0, 'mu': 0.05, 'sigma': 0.2, 'dt': 0.01, 't': 0.5, 'n_simulations': 10}
            },
            {
                'endpoint': '/combine_strands',
                'payload': {'strands': [[100, 101, 102], [100, 99, 101], [100, 100.5, 101.5]], 'weights': [0.5, 0.3, 0.2]}
            }
        ]
        
        latencies = []
        errors = 0
        
        for i in range(num_requests):
            test_case = test_cases[i % len(test_cases)]
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{self.base_urls['simulation_engine']}{test_case['endpoint']}",
                    json=test_case['payload'],
                    timeout=15
                )
                latency = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    latencies.append(latency)
                else:
                    errors += 1
                    
            except Exception as e:
                errors += 1
                logger.error(f"Simulation request {i} failed: {e}")
        
        if latencies:
            self.results['simulation_engine'] = {
                'avg_latency_ms': statistics.mean(latencies),
                'p95_latency_ms': statistics.quantiles(latencies, n=20)[18],
                'min_latency_ms': min(latencies),
                'max_latency_ms': max(latencies),
                'success_rate': (len(latencies) / num_requests) * 100,
                'errors': errors,
                'total_requests': num_requests
            }
            
            print(f"  Average latency: {self.results['simulation_engine']['avg_latency_ms']:.2f}ms")
            print(f"  P95 latency: {self.results['simulation_engine']['p95_latency_ms']:.2f}ms")
            print(f"  Success rate: {self.results['simulation_engine']['success_rate']:.1f}%")
    
    def benchmark_concurrent_load(self, concurrent_users=10, requests_per_user=20):
        """Benchmark concurrent load across all services"""
        print(f"\n=== Benchmarking Concurrent Load ({concurrent_users} users, {requests_per_user} req/user) ===")
        
        def user_simulation(user_id):
            user_latencies = []
            user_errors = 0
            
            for i in range(requests_per_user):
                service = ['nlp_voice', 'auto_agent', 'simulation_engine'][i % 3]
                start_time = time.time()
                
                try:
                    if service == 'nlp_voice':
                        response = requests.post(
                            f"{self.base_urls[service]}/process_query",
                            json={"query": "predict stock price for AAPL"},
                            timeout=5
                        )
                    elif service == 'auto_agent':
                        response = requests.post(
                            f"{self.base_urls[service]}/predict_vix",
                            json={"symbol": "AAPL", "timeframe": "1D"},
                            timeout=10
                        )
                    else:
                        response = requests.post(
                            f"{self.base_urls[service]}/simulate_gbm",
                            json={'s0': 100.0, 'mu': 0.05, 'sigma': 0.2, 'dt': 0.01, 't': 0.5},
                            timeout=15
                        )
                    
                    latency = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        user_latencies.append(latency)
                    else:
                        user_errors += 1
                        
                except Exception as e:
                    user_errors += 1
            
            return user_latencies, user_errors
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_simulation, i) for i in range(concurrent_users)]
            results = [future.result() for future in futures]
        
        all_latencies = []
        total_errors = 0
        
        for latencies, errors in results:
            all_latencies.extend(latencies)
            total_errors += errors
        
        if all_latencies:
            total_requests = concurrent_users * requests_per_user
            throughput = len(all_latencies) / (max(all_latencies) / 1000) if all_latencies else 0
            
            self.results['concurrent_load'] = {
                'avg_latency_ms': statistics.mean(all_latencies),
                'p95_latency_ms': statistics.quantiles(all_latencies, n=20)[18],
                'p99_latency_ms': statistics.quantiles(all_latencies, n=100)[98],
                'throughput_rps': throughput,
                'success_rate': (len(all_latencies) / total_requests) * 100,
                'total_errors': total_errors,
                'concurrent_users': concurrent_users,
                'total_requests': total_requests
            }
            
            print(f"  Average latency: {self.results['concurrent_load']['avg_latency_ms']:.2f}ms")
            print(f"  P95 latency: {self.results['concurrent_load']['p95_latency_ms']:.2f}ms")
            print(f"  P99 latency: {self.results['concurrent_load']['p99_latency_ms']:.2f}ms")
            print(f"  Throughput: {self.results['concurrent_load']['throughput_rps']:.1f} req/sec")
            print(f"  Success rate: {self.results['concurrent_load']['success_rate']:.1f}%")
    
    def check_service_health(self):
        """Check health of all Phase 2 services"""
        print("\n=== Service Health Check ===")
        
        health_status = {}
        
        for service, base_url in self.base_urls.items():
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    health_status[service] = "✓ Healthy"
                else:
                    health_status[service] = f"✗ Unhealthy (HTTP {response.status_code})"
            except Exception as e:
                health_status[service] = f"✗ Unreachable ({str(e)})"
        
        for service, status in health_status.items():
            print(f"  {service}: {status}")
        
        return health_status
    
    def generate_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "="*60)
        print("PHASE 2 PERFORMANCE BENCHMARK REPORT")
        print("="*60)
        
        for service, metrics in self.results.items():
            print(f"\n{service.upper().replace('_', ' ')}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.2f}")
                else:
                    print(f"  {metric}: {value}")
        
        print(f"\n{'PERFORMANCE TARGETS VALIDATION'}")
        print("-" * 40)
        
        targets_met = True
        
        if 'nlp_voice' in self.results:
            nlp_avg = self.results['nlp_voice']['avg_latency_ms']
            if nlp_avg < 200:
                print(f"✓ NLP/Voice latency: {nlp_avg:.2f}ms < 200ms target")
            else:
                print(f"✗ NLP/Voice latency: {nlp_avg:.2f}ms > 200ms target")
                targets_met = False
        
        if 'auto_agent' in self.results:
            agent_avg = self.results['auto_agent']['avg_latency_ms']
            if agent_avg < 1000:
                print(f"✓ Auto-Agent latency: {agent_avg:.2f}ms < 1000ms target")
            else:
                print(f"✗ Auto-Agent latency: {agent_avg:.2f}ms > 1000ms target")
                targets_met = False
        
        if 'simulation_engine' in self.results:
            sim_avg = self.results['simulation_engine']['avg_latency_ms']
            if sim_avg < 500:
                print(f"✓ Simulation Engine latency: {sim_avg:.2f}ms < 500ms target")
            else:
                print(f"✗ Simulation Engine latency: {sim_avg:.2f}ms > 500ms target")
                targets_met = False
        
        if 'concurrent_load' in self.results:
            throughput = self.results['concurrent_load']['throughput_rps']
            if throughput > 100:
                print(f"✓ Concurrent throughput: {throughput:.1f} req/sec > 100 req/sec target")
            else:
                print(f"✗ Concurrent throughput: {throughput:.1f} req/sec < 100 req/sec target")
                targets_met = False
        
        print(f"\nOVERALL: {'✓ ALL TARGETS MET' if targets_met else '✗ SOME TARGETS MISSED'}")
        
        return targets_met

def main():
    benchmark = Phase2PerformanceBenchmark()
    
    health_status = benchmark.check_service_health()
    
    healthy_services = [k for k, v in health_status.items() if "✓" in v]
    
    if len(healthy_services) < 3:
        print(f"\nWarning: Only {len(healthy_services)}/3 services are healthy. Skipping benchmarks.")
        return False
    
    benchmark.benchmark_nlp_voice_interface()
    benchmark.benchmark_auto_agent()
    benchmark.benchmark_simulation_engine()
    
    benchmark.benchmark_concurrent_load()
    
    targets_met = benchmark.generate_report()
    
    return targets_met

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

"""
Performance testing suite for strand creation engines
Validates <1ms latency and 20K+ events/second throughput requirements
"""

import pytest
import asyncio
import time
import numpy as np
from typing import List, Dict, Any
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor
import threading

from ..src.braided_cord_data_engine import BraidedCordDataEngine, StorageTier, StrandMetadata
from ..src.strand_types import EventStrand, MarketStrand
from ..src.event_upload_processor import EventUploadProcessor
from ..src.automated_strand_creator import AutomatedStrandCreator
from ..src.market_regime_detector import MarketRegime

logging.basicConfig(level=logging.INFO)

class TestStrandPerformance:
    """Comprehensive performance testing for strand creation engines"""
    
    @pytest.fixture
    async def data_engine(self):
        """Initialize data engine for testing"""
        engine = BraidedCordDataEngine()
        await engine.initialize()
        yield engine
        await engine.cleanup()
    
    @pytest.fixture
    async def event_processor(self):
        """Initialize event processor for testing"""
        processor = EventUploadProcessor(
            batch_size=500,
            flush_interval=1.0,
            max_concurrent_batches=8
        )
        await processor.initialize()
        await processor.start_processing()
        yield processor
        await processor.stop_processing()
    
    @pytest.fixture
    async def strand_creator(self):
        """Initialize strand creator for testing"""
        creator = AutomatedStrandCreator()
        await creator.initialize()
        yield creator
        await creator.cleanup()
    
    def generate_test_events(self, count: int, event_type: str = "market") -> List[Dict[str, Any]]:
        """Generate test events for performance testing"""
        events = []
        base_time = time.time_ns()
        
        for i in range(count):
            if event_type == "market":
                event = {
                    'timestamp_ns': base_time + i * 1000000,  # 1ms intervals
                    'type_id': 1,
                    'source_id': i % 10,
                    'type': 'market_data',
                    'payload': {
                        'price': 100.0 + np.random.normal(0, 1),
                        'volume': 1000 + np.random.randint(0, 500),
                        'sentiment': np.random.uniform(-1, 1)
                    }
                }
            else:
                event = {
                    'timestamp_ns': base_time + i * 1000000,
                    'type_id': 2,
                    'source_id': i % 5,
                    'type': 'general_event',
                    'payload': {
                        'data': f"event_{i}",
                        'value': np.random.random()
                    }
                }
            
            events.append(event)
        
        return events
    
    @pytest.mark.asyncio
    async def test_data_engine_latency(self, data_engine):
        """Test BraidedCordDataEngine latency requirements (<1ms for hot tier)"""
        test_data = np.random.random(1000).astype(np.float64)
        metadata = StrandMetadata(
            strand_id="test_latency",
            timestamp_ns=time.time_ns(),
            tier=StorageTier.HOT,
            size_bytes=test_data.nbytes,
            access_count=1,
            last_accessed_ns=time.time_ns()
        )
        
        latencies = []
        
        for i in range(100):
            start_time = time.perf_counter_ns()
            
            await data_engine.store_strand(test_data, metadata)
            
            end_time = time.perf_counter_ns()
            latency_ns = end_time - start_time
            latencies.append(latency_ns)
        
        avg_latency_ms = np.mean(latencies) / 1e6
        p95_latency_ms = np.percentile(latencies, 95) / 1e6
        p99_latency_ms = np.percentile(latencies, 99) / 1e6
        
        print(f"Data Engine Hot Tier Latency:")
        print(f"  Average: {avg_latency_ms:.3f}ms")
        print(f"  P95: {p95_latency_ms:.3f}ms")
        print(f"  P99: {p99_latency_ms:.3f}ms")
        
        assert avg_latency_ms < 1.0, f"Average latency {avg_latency_ms:.3f}ms exceeds 1ms requirement"
        assert p95_latency_ms < 2.0, f"P95 latency {p95_latency_ms:.3f}ms exceeds 2ms threshold"
    
    @pytest.mark.asyncio
    async def test_event_processor_throughput(self, event_processor):
        """Test EventUploadProcessor throughput (20K+ events/second)"""
        event_counts = [1000, 5000, 10000, 20000, 25000]
        
        for event_count in event_counts:
            events = self.generate_test_events(event_count)
            
            start_time = time.perf_counter()
            
            successful = 0
            failed = 0
            
            for event in events:
                result = await event_processor.upload_event(event)
                if result:
                    successful += 1
                else:
                    failed += 1
            
            await asyncio.sleep(2.0)
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            throughput = successful / duration
            
            print(f"Event Processor Throughput Test ({event_count} events):")
            print(f"  Successful: {successful}")
            print(f"  Failed: {failed}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Throughput: {throughput:.0f} events/second")
            
            if event_count <= 20000:
                assert throughput >= 20000, f"Throughput {throughput:.0f} below 20K events/second requirement"
    
    @pytest.mark.asyncio
    async def test_strand_creation_latency(self, strand_creator):
        """Test strand creation latency"""
        event_counts = [10, 50, 100, 500, 1000]
        
        for event_count in event_counts:
            events = self.generate_test_events(event_count)
            market_data = {
                'vix': 15.0,
                'realized_vol': 0.2,
                'bid_ask_spread': 0.001,
                'volume': 1.0,
                'sentiment_score': 0.1
            }
            
            latencies = []
            
            for _ in range(10):  # Run 10 iterations
                start_time = time.perf_counter_ns()
                
                strands = await strand_creator.create_strands_from_events(events, market_data)
                
                end_time = time.perf_counter_ns()
                latency_ms = (end_time - start_time) / 1e6
                latencies.append(latency_ms)
            
            avg_latency = np.mean(latencies)
            p95_latency = np.percentile(latencies, 95)
            
            print(f"Strand Creation Latency ({event_count} events):")
            print(f"  Average: {avg_latency:.2f}ms")
            print(f"  P95: {p95_latency:.2f}ms")
            print(f"  Strands created: {len(strands) if 'strands' in locals() else 0}")
            
            if event_count <= 100:
                assert avg_latency < 10.0, f"Average latency {avg_latency:.2f}ms too high for {event_count} events"
    
    @pytest.mark.asyncio
    async def test_vectorized_operations_performance(self):
        """Test performance of vectorized operations vs loops"""
        sizes = [1000, 5000, 10000, 50000]
        
        for size in sizes:
            events = self.generate_test_events(size)
            
            loop_times = []
            vectorized_times = []
            
            for _ in range(5):
                start_time = time.perf_counter()
                
                timestamps = []
                for event in events:
                    timestamps.append(event['timestamp_ns'])
                
                loop_time = time.perf_counter() - start_time
                loop_times.append(loop_time)
                
                start_time = time.perf_counter()
                
                timestamps_vec = np.array([event['timestamp_ns'] for event in events])
                
                vectorized_time = time.perf_counter() - start_time
                vectorized_times.append(vectorized_time)
            
            avg_loop_time = np.mean(loop_times) * 1000
            avg_vectorized_time = np.mean(vectorized_times) * 1000
            speedup = avg_loop_time / avg_vectorized_time
            
            print(f"Vectorization Performance ({size} events):")
            print(f"  Loop approach: {avg_loop_time:.2f}ms")
            print(f"  Vectorized approach: {avg_vectorized_time:.2f}ms")
            print(f"  Speedup: {speedup:.1f}x")
            
            assert speedup > 1.0, f"Vectorized operations should be faster than loops"
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, event_processor):
        """Test concurrent event processing performance"""
        num_threads = [1, 2, 4, 8]
        events_per_thread = 2500  # Total 20K events with 8 threads
        
        for thread_count in num_threads:
            events = self.generate_test_events(events_per_thread)
            
            async def process_events_batch():
                successful = 0
                for event in events:
                    result = await event_processor.upload_event(event)
                    if result:
                        successful += 1
                return successful
            
            start_time = time.perf_counter()
            
            tasks = [process_events_batch() for _ in range(thread_count)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            total_successful = sum(results)
            total_events = events_per_thread * thread_count
            throughput = total_successful / duration
            
            print(f"Concurrent Processing ({thread_count} threads):")
            print(f"  Total events: {total_events}")
            print(f"  Successful: {total_successful}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Throughput: {throughput:.0f} events/second")
            
            if thread_count >= 4:
                assert throughput >= 15000, f"Concurrent throughput {throughput:.0f} below threshold"
    
    @pytest.mark.asyncio
    async def test_memory_usage_efficiency(self, strand_creator):
        """Test memory usage efficiency during strand creation"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        large_event_batch = self.generate_test_events(10000)
        market_data = {
            'vix': 20.0,
            'realized_vol': 0.25,
            'bid_ask_spread': 0.002,
            'volume': 1.5,
            'sentiment_score': 0.2
        }
        
        memory_samples = []
        
        for i in range(10):
            strands = await strand_creator.create_strands_from_events(large_event_batch, market_data)
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(current_memory)
            
            await asyncio.sleep(0.1)
        
        peak_memory = max(memory_samples)
        memory_growth = peak_memory - initial_memory
        
        print(f"Memory Usage Test:")
        print(f"  Initial memory: {initial_memory:.1f}MB")
        print(f"  Peak memory: {peak_memory:.1f}MB")
        print(f"  Memory growth: {memory_growth:.1f}MB")
        print(f"  Memory per 10K events: {memory_growth:.1f}MB")
        
        assert memory_growth < 500, f"Memory growth {memory_growth:.1f}MB too high for 10K events"
    
    @pytest.mark.asyncio
    async def test_strand_search_performance(self, strand_creator):
        """Test strand search performance"""
        events = self.generate_test_events(5000)
        market_data = {
            'vix': 15.0,
            'realized_vol': 0.2,
            'bid_ask_spread': 0.001,
            'volume': 1.0,
            'sentiment_score': 0.1
        }
        
        strands = await strand_creator.create_strands_from_events(events, market_data)
        
        search_times = []
        
        for _ in range(50):
            start_time = time.perf_counter()
            
            results = await strand_creator.search_strands_by_pattern(
                "price_to_volume",
                regime=MarketRegime.LOW_VOLATILITY_STABLE
            )
            
            end_time = time.perf_counter()
            search_time_ms = (end_time - start_time) * 1000
            search_times.append(search_time_ms)
        
        avg_search_time = np.mean(search_times)
        p95_search_time = np.percentile(search_times, 95)
        
        print(f"Strand Search Performance:")
        print(f"  Average search time: {avg_search_time:.2f}ms")
        print(f"  P95 search time: {p95_search_time:.2f}ms")
        print(f"  Results found: {len(results) if 'results' in locals() else 0}")
        
        assert avg_search_time < 5.0, f"Average search time {avg_search_time:.2f}ms too slow"
        assert p95_search_time < 10.0, f"P95 search time {p95_search_time:.2f}ms too slow"
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, event_processor, strand_creator):
        """Test end-to-end performance from event upload to strand creation"""
        event_count = 10000
        events = self.generate_test_events(event_count)
        
        market_data = {
            'vix': 18.0,
            'realized_vol': 0.22,
            'bid_ask_spread': 0.0015,
            'volume': 1.2,
            'sentiment_score': 0.15
        }
        
        start_time = time.perf_counter()
        
        upload_successful = 0
        for event in events:
            result = await event_processor.upload_event(event)
            if result:
                upload_successful += 1
        
        await asyncio.sleep(2.0)
        
        strands = await strand_creator.create_strands_from_events(events, market_data)
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        overall_throughput = upload_successful / total_duration
        
        print(f"End-to-End Performance Test:")
        print(f"  Events uploaded: {upload_successful}/{event_count}")
        print(f"  Strands created: {len(strands)}")
        print(f"  Total duration: {total_duration:.2f}s")
        print(f"  Overall throughput: {overall_throughput:.0f} events/second")
        
        assert overall_throughput >= 15000, f"End-to-end throughput {overall_throughput:.0f} below 15K events/second"
        assert len(strands) > 0, "No strands were created"
    
    def test_strand_types_performance(self):
        """Test performance of EventStrand and MarketStrand operations"""
        event_count = 5000
        events = self.generate_test_events(event_count)
        
        creation_times = []
        
        for _ in range(10):
            start_time = time.perf_counter()
            
            strand = EventStrand.create_from_events(events)
            
            end_time = time.perf_counter()
            creation_time_ms = (end_time - start_time) * 1000
            creation_times.append(creation_time_ms)
        
        avg_creation_time = np.mean(creation_times)
        
        print(f"EventStrand Creation Performance ({event_count} events):")
        print(f"  Average creation time: {avg_creation_time:.2f}ms")
        print(f"  Events per ms: {event_count / avg_creation_time:.1f}")
        
        assert avg_creation_time < 50.0, f"Strand creation time {avg_creation_time:.2f}ms too slow"
        
        search_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            
            filtered = strand.get_events_in_time_range(
                strand.timestamps_ns[0], 
                strand.timestamps_ns[len(strand.timestamps_ns)//2]
            )
            
            end_time = time.perf_counter()
            search_time_ms = (end_time - start_time) * 1000
            search_times.append(search_time_ms)
        
        avg_search_time = np.mean(search_times)
        
        print(f"  Average search time: {avg_search_time:.3f}ms")
        
        assert avg_search_time < 1.0, f"Strand search time {avg_search_time:.3f}ms too slow"

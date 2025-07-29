#!/usr/bin/env python3
"""
Performance test for TimescaleDB and Kafka integration
Tests 20K events/second throughput and <1ms latency requirements
"""

import asyncio
import asyncpg
import json
import time
import threading
from datetime import datetime
from kafka import KafkaProducer
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTest:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            batch_size=16384,
            linger_ms=1
        )
        self.db_connection = "postgresql://postgres:postgres@localhost:5432/fintech_db"
        self.test_results = {
            'messages_sent': 0,
            'messages_stored': 0,
            'start_time': 0,
            'end_time': 0,
            'latencies': [],
            'errors': 0
        }
    
    def generate_test_message(self, i: int) -> dict:
        """Generate realistic test trading message"""
        return {
            "time": datetime.now().isoformat(),
            "symbol": f"TEST{i % 100:03d}",
            "price": 100.0 + (i % 1000) * 0.01,
            "volume": 100 + (i % 500),
            "strategy_type": ["gated_dql", "gated_policy_gradient", "tft"][i % 3],
            "confidence": 0.8 + (i % 20) * 0.01
        }
    
    async def send_high_volume_messages(self, target_rate: int = 20000, duration: int = 10):
        """Send messages at target rate for specified duration"""
        logger.info(f"Starting high-volume test: {target_rate} msg/sec for {duration} seconds")
        
        self.test_results['start_time'] = time.time()
        messages_to_send = target_rate * duration
        interval = 1.0 / target_rate
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for i in range(messages_to_send):
                message = self.generate_test_message(i)
                
                future = executor.submit(self._send_message_with_timing, message, i)
                futures.append(future)
                
                if i > 0 and i % 1000 == 0:
                    await asyncio.sleep(0.001)  # Brief pause every 1000 messages
                
                if i % 5000 == 0:
                    logger.info(f"Sent {i}/{messages_to_send} messages")
            
            for future in futures:
                try:
                    future.result(timeout=1.0)
                except Exception as e:
                    self.test_results['errors'] += 1
                    logger.error(f"Send error: {e}")
        
        self.test_results['end_time'] = time.time()
        self.producer.flush()
        logger.info(f"Completed sending {self.test_results['messages_sent']} messages")
    
    def _send_message_with_timing(self, message: dict, message_id: int):
        """Send individual message and track timing"""
        try:
            start_time = time.time()
            
            self.producer.send('trades', value=message)
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            
            self.test_results['latencies'].append(latency)
            self.test_results['messages_sent'] += 1
            
        except Exception as e:
            self.test_results['errors'] += 1
            logger.error(f"Error sending message {message_id}: {e}")
    
    async def verify_database_storage(self, expected_count: int):
        """Verify messages were stored in TimescaleDB"""
        logger.info("Verifying database storage...")
        
        await asyncio.sleep(15)
        
        try:
            conn = await asyncpg.connect(self.db_connection)
            
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM trades 
                WHERE symbol LIKE 'TEST%' 
                AND time >= NOW() - INTERVAL '5 minutes'
            """)
            
            self.test_results['messages_stored'] = count
            
            latency_tests = []
            for _ in range(100):
                start_time = time.time()
                
                await conn.fetchrow("""
                    SELECT * FROM trades 
                    WHERE symbol = 'TEST001' 
                    ORDER BY time DESC 
                    LIMIT 1
                """)
                
                query_latency = (time.time() - start_time) * 1000
                latency_tests.append(query_latency)
            
            avg_query_latency = sum(latency_tests) / len(latency_tests)
            max_query_latency = max(latency_tests)
            
            logger.info(f"Database verification complete:")
            logger.info(f"  Expected messages: {expected_count}")
            logger.info(f"  Stored messages: {count}")
            logger.info(f"  Storage rate: {count / expected_count * 100:.1f}%")
            logger.info(f"  Avg query latency: {avg_query_latency:.3f}ms")
            logger.info(f"  Max query latency: {max_query_latency:.3f}ms")
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Database verification error: {e}")
            self.test_results['errors'] += 1
    
    def calculate_performance_metrics(self):
        """Calculate and display performance metrics"""
        duration = self.test_results['end_time'] - self.test_results['start_time']
        actual_rate = self.test_results['messages_sent'] / duration if duration > 0 else 0
        
        if self.test_results['latencies']:
            avg_latency = sum(self.test_results['latencies']) / len(self.test_results['latencies'])
            max_latency = max(self.test_results['latencies'])
            min_latency = min(self.test_results['latencies'])
            p95_latency = sorted(self.test_results['latencies'])[int(len(self.test_results['latencies']) * 0.95)]
        else:
            avg_latency = max_latency = min_latency = p95_latency = 0
        
        logger.info("=== PERFORMANCE TEST RESULTS ===")
        logger.info(f"Test Duration: {duration:.2f} seconds")
        logger.info(f"Messages Sent: {self.test_results['messages_sent']}")
        logger.info(f"Messages Stored: {self.test_results['messages_stored']}")
        logger.info(f"Actual Send Rate: {actual_rate:.0f} msg/sec")
        logger.info(f"Storage Success Rate: {self.test_results['messages_stored'] / self.test_results['messages_sent'] * 100:.1f}%")
        logger.info(f"Errors: {self.test_results['errors']}")
        logger.info(f"Send Latency - Avg: {avg_latency:.3f}ms, Max: {max_latency:.3f}ms, Min: {min_latency:.3f}ms, P95: {p95_latency:.3f}ms")
        
        rate_ok = actual_rate >= 18000  # Allow 10% tolerance
        latency_ok = p95_latency < 1.0  # <1ms requirement
        storage_ok = self.test_results['messages_stored'] / self.test_results['messages_sent'] > 0.95
        
        logger.info("=== REQUIREMENT VERIFICATION ===")
        logger.info(f"20K msg/sec requirement: {'✓ PASS' if rate_ok else '✗ FAIL'}")
        logger.info(f"<1ms latency requirement: {'✓ PASS' if latency_ok else '✗ FAIL'}")
        logger.info(f"95%+ storage requirement: {'✓ PASS' if storage_ok else '✗ FAIL'}")
        
        return rate_ok and latency_ok and storage_ok

async def main():
    """Run comprehensive performance test"""
    test = PerformanceTest()
    
    try:
        await test.send_high_volume_messages(target_rate=20000, duration=5)
        
        await test.verify_database_storage(expected_count=100000)
        
        success = test.calculate_performance_metrics()
        
        if success:
            logger.info("🎉 ALL PERFORMANCE REQUIREMENTS MET!")
        else:
            logger.warning("⚠️  Some performance requirements not met")
            
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
    finally:
        test.producer.close()

if __name__ == "__main__":
    asyncio.run(main())

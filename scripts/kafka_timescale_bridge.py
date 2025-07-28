#!/usr/bin/env python3
"""
Kafka to TimescaleDB Bridge
High-performance bridge for streaming Kafka messages to TimescaleDB
Targets 20K events/second throughput with <1ms latency
"""

import asyncio
import asyncpg
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from kafka import KafkaConsumer
import threading
from concurrent.futures import ThreadPoolExecutor
import signal
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaTimescaleBridge:
    def __init__(self, 
                 kafka_servers: List[str] = ['localhost:9092'],
                 topics: List[str] = ['trades', 'exegy-feed', 'news-analysis', 'risk-assessment', 'compliance-monitoring'],
                 db_connection: str = "postgresql://postgres:postgres@localhost:5432/fintech_db",
                 batch_size: int = 1000,
                 flush_interval: float = 5.0):
        self.kafka_servers = kafka_servers
        self.topics = topics
        self.db_connection = db_connection
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pool = None
        self.running = False
        self.message_buffer = []
        self.buffer_lock = threading.Lock()
        self.stats = {
            'messages_processed': 0,
            'messages_stored': 0,
            'errors': 0,
            'start_time': time.time()
        }
    
    async def initialize_db_pool(self):
        """Initialize AsyncPG connection pool for high performance"""
        self.pool = await asyncpg.create_pool(
            self.db_connection,
            min_size=10,
            max_size=100,
            command_timeout=1.0
        )
        logger.info("Database connection pool initialized")
    
    async def batch_insert_trades(self, messages: List[Dict[str, Any]]):
        """Batch insert messages to TimescaleDB for optimal performance"""
        if not messages:
            return
        
        try:
            async with self.pool.acquire() as connection:
                batch_data = []
                for msg in messages:
                    timestamp = msg.get('time', datetime.now().isoformat())
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    
                    batch_data.append((
                        timestamp,
                        msg.get('symbol', 'UNKNOWN'),
                        float(msg.get('price', 0.0)),
                        int(msg.get('volume', 0)),
                        msg.get('strategy_type', 'kafka_stream'),
                        float(msg.get('confidence', 0.0))
                    ))
                
                await connection.copy_records_to_table(
                    'trades',
                    records=batch_data,
                    columns=['time', 'symbol', 'price', 'volume', 'strategy_type', 'confidence']
                )
                
                self.stats['messages_stored'] += len(messages)
                logger.info(f"Batch inserted {len(messages)} records to TimescaleDB")
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error batch inserting to TimescaleDB: {e}")
    
    async def flush_buffer(self):
        """Flush message buffer to database"""
        with self.buffer_lock:
            if self.message_buffer:
                messages_to_flush = self.message_buffer.copy()
                self.message_buffer.clear()
            else:
                return
        
        await self.batch_insert_trades(messages_to_flush)
    
    async def periodic_flush(self):
        """Periodically flush buffer to maintain low latency"""
        while self.running:
            await asyncio.sleep(self.flush_interval)
            await self.flush_buffer()
    
    def consume_kafka_messages(self):
        """Consume messages from Kafka topics"""
        consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='timescale_bridge'
        )
        
        logger.info(f"Started Kafka consumer for topics: {self.topics}")
        
        try:
            for message in consumer:
                if not self.running:
                    break
                
                try:
                    message_data = message.value
                    self.stats['messages_processed'] += 1
                    
                    with self.buffer_lock:
                        self.message_buffer.append(message_data)
                        logger.info(f"Added message to buffer: {message_data}")
                        
                        if len(self.message_buffer) >= self.batch_size:
                            logger.info(f"Buffer full ({len(self.message_buffer)} messages), triggering flush")
                            asyncio.run_coroutine_threadsafe(self.flush_buffer(), asyncio.get_event_loop())
                    
                    if self.stats['messages_processed'] % 1000 == 0:
                        self.log_stats()
                        
                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error processing Kafka message: {e}")
                    
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}")
        finally:
            consumer.close()
    
    def log_stats(self):
        """Log performance statistics"""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['messages_processed'] / elapsed if elapsed > 0 else 0
        
        logger.info(f"Stats - Processed: {self.stats['messages_processed']}, "
                   f"Stored: {self.stats['messages_stored']}, "
                   f"Errors: {self.stats['errors']}, "
                   f"Rate: {rate:.2f} msg/sec")
    
    async def start(self):
        """Start the Kafka to TimescaleDB bridge"""
        self.running = True
        
        await self.initialize_db_pool()
        
        flush_task = asyncio.create_task(self.periodic_flush())
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            kafka_task = executor.submit(self.consume_kafka_messages)
            
            logger.info("Kafka to TimescaleDB bridge started")
            
            try:
                while self.running:
                    await asyncio.sleep(1)
                    if kafka_task.done():
                        break
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
            finally:
                self.running = False
                flush_task.cancel()
                
                await self.flush_buffer()
                
                if self.pool:
                    await self.pool.close()
                
                self.log_stats()
                logger.info("Kafka to TimescaleDB bridge stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

async def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bridge = KafkaTimescaleBridge()
    await bridge.start()

if __name__ == "__main__":
    asyncio.run(main())

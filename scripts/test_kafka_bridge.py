#!/usr/bin/env python3
"""
Simple test script to verify Kafka to TimescaleDB bridge functionality
"""

import asyncio
import asyncpg
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_connection():
    """Test TimescaleDB connection"""
    try:
        conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/fintech_db")
        result = await conn.fetchval("SELECT COUNT(*) FROM trades")
        logger.info(f"Database connection successful. Current trades count: {result}")
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def test_kafka_producer():
    """Test Kafka producer"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        test_message = {
            "time": datetime.now().isoformat(),
            "symbol": "TEST",
            "price": 100.0,
            "volume": 10,
            "strategy_type": "test_bridge",
            "confidence": 0.99
        }
        
        producer.send('trades', value=test_message)
        producer.flush()
        producer.close()
        logger.info("Kafka producer test successful")
        return True
    except Exception as e:
        logger.error(f"Kafka producer test failed: {e}")
        return False

def test_kafka_consumer():
    """Test Kafka consumer"""
    try:
        consumer = KafkaConsumer(
            'trades',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            consumer_timeout_ms=5000
        )
        
        logger.info("Kafka consumer test started, waiting for messages...")
        message_count = 0
        for message in consumer:
            logger.info(f"Received message: {message.value}")
            message_count += 1
            if message_count >= 1:
                break
        
        consumer.close()
        logger.info(f"Kafka consumer test completed, received {message_count} messages")
        return message_count > 0
    except Exception as e:
        logger.error(f"Kafka consumer test failed: {e}")
        return False

async def insert_test_data():
    """Insert test data directly to TimescaleDB"""
    try:
        conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/fintech_db")
        
        await conn.execute("""
            INSERT INTO trades (time, symbol, price, volume, strategy_type, confidence) 
            VALUES (NOW(), $1, $2, $3, $4, $5)
        """, "DIRECT_TEST", 150.25, 100, "direct_insert", 0.95)
        
        result = await conn.fetchval("SELECT COUNT(*) FROM trades WHERE symbol = 'DIRECT_TEST'")
        logger.info(f"Direct database insert successful. Test records: {result}")
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Direct database insert failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("Starting Kafka-TimescaleDB bridge tests...")
    
    db_ok = await test_database_connection()
    
    insert_ok = await insert_test_data()
    
    producer_ok = test_kafka_producer()
    
    consumer_ok = test_kafka_consumer()
    
    logger.info(f"Test results:")
    logger.info(f"  Database connection: {'✓' if db_ok else '✗'}")
    logger.info(f"  Direct database insert: {'✓' if insert_ok else '✗'}")
    logger.info(f"  Kafka producer: {'✓' if producer_ok else '✗'}")
    logger.info(f"  Kafka consumer: {'✓' if consumer_ok else '✗'}")
    
    if all([db_ok, insert_ok, producer_ok]):
        logger.info("Basic components working. Bridge script issue is likely in the integration logic.")
    else:
        logger.error("Basic component failures detected. Fix these first.")

if __name__ == "__main__":
    asyncio.run(main())

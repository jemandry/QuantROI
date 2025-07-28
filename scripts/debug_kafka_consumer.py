#!/usr/bin/env python3
"""
Debug script to test Kafka message consumption
"""

import json
import logging
from kafka import KafkaConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_kafka_consumer():
    """Debug Kafka consumer to see what messages are available"""
    try:
        consumer = KafkaConsumer(
            'trades',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='debug_consumer',
            consumer_timeout_ms=10000
        )
        
        logger.info("Debug consumer started, checking for messages...")
        message_count = 0
        
        for message in consumer:
            logger.info(f"Message {message_count + 1}: {message.value}")
            logger.info(f"Topic: {message.topic}, Partition: {message.partition}, Offset: {message.offset}")
            message_count += 1
            
            if message_count >= 10:  # Limit to 10 messages for debugging
                break
        
        consumer.close()
        logger.info(f"Debug consumer completed. Total messages: {message_count}")
        
        if message_count == 0:
            logger.warning("No messages found in 'trades' topic")
            
    except Exception as e:
        logger.error(f"Debug consumer failed: {e}")

if __name__ == "__main__":
    debug_kafka_consumer()

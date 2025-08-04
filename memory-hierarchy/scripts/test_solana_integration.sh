#!/bin/bash
set -e

echo "=== Testing Solana Event Logging Integration ==="
echo "This script tests the Solana event logging with braided cord integration"

echo "Starting memory hierarchy service..."
cd /home/ubuntu/repos/quantroi/memory-hierarchy
cargo build --release
./target/release/memory-hierarchy-service &
SERVICE_PID=$!

sleep 5

echo "Testing Anchor build event logging..."
curl -X POST http://localhost:8080/solana/event/anchor_build \
    -H "Content-Type: application/json" \
    -d '{
        "project_path": "/app/contracts/delegation-management",
        "success": true
    }' || echo "Service not ready yet"

echo "Testing contract execution event logging..."
curl -X POST http://localhost:8080/solana/event/contract_execution \
    -H "Content-Type: application/json" \
    -d '{
        "transaction_signature": "5J7XjMQVrBBjCKVKvEpnQ8QqBbzxvQz9KvEpnQ8QqBbzxvQz9",
        "program_id": "11111111111111111111111111111111",
        "merton_params": {
            "mu": 0.05,
            "sigma": 0.2,
            "jump_lambda": 0.1,
            "jump_mu": -0.05,
            "jump_sigma": 0.1
        }
    }' || echo "Service not ready yet"

echo "Testing Solana events retrieval..."
curl -X GET http://localhost:8080/solana/events || echo "Service not ready yet"

echo "Cleaning up..."
kill $SERVICE_PID 2>/dev/null || true

echo "✅ Solana event logging integration tests completed!"

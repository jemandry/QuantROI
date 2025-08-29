#!/bin/bash
set -e

echo "=== Testing Anchor CLI Docker Container ==="
echo "This script tests the Docker containerization solution for Anchor CLI"

echo "Building Anchor CLI Docker image..."
cd /home/ubuntu/repos/quantroi/memory-hierarchy
docker build -f Dockerfile.anchor -t quantroi-anchor-cli .

echo "Testing Anchor CLI version..."
docker run --rm quantroi-anchor-cli anchor --version

echo "Testing Solana CLI version..."
docker run --rm quantroi-anchor-cli solana --version

echo "Testing cargo-build-sbf availability..."
docker run --rm quantroi-anchor-cli cargo build-sbf --help

echo "Testing with mounted Solana contracts..."
docker run --rm \
    -v /home/ubuntu/repos/quantroi/solana-contracts:/app/contracts \
    -w /app/contracts \
    quantroi-anchor-cli \
    bash -c "ls -la && anchor --version"

echo "✅ Anchor CLI Docker container tests completed successfully!"
echo "Container is ready for use with GLIBC 2.39 compatibility"

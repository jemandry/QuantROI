#!/bin/bash
set -e

echo "Making scripts executable..."

chmod +x /home/ubuntu/repos/quantroi/memory-hierarchy/scripts/build_anchor_from_source.sh
chmod +x /home/ubuntu/repos/quantroi/memory-hierarchy/scripts/test_anchor_docker.sh
chmod +x /home/ubuntu/repos/quantroi/memory-hierarchy/scripts/test_solana_integration.sh

echo "✅ All scripts are now executable"

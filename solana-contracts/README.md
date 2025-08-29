# Solana Smart Contracts
## Ethical AI-Driven Fintech Trading Platform

This directory contains all Solana smart contracts (programs) written in Rust using the Anchor framework.

## Contract Overview

### Core Contracts
- **delegation/**: Bank-to-AI policy delegation contracts
- **knowledge-tests/**: Investor competency verification
- **ria-contracts/**: Registered Investment Advisor agreements
- **payments/**: Cryptographic payment processing
- **billing/**: Automated fee management
- **execution-masking/**: Trade execution privacy
- **goal-tracking/**: Investment objective monitoring
- **voting/**: Governance and decision voting
- **transfers/**: Departmental fund transfers
- **roi-competitions/**: AI agent performance competitions

## Development Setup

```bash
# Install Solana CLI
sh -c "$(curl -sSfL https://release.solana.com/v1.16.0/install)"

# Install Anchor
cargo install --git https://github.com/coral-xyz/anchor avm --locked --force
avm install latest
avm use latest

# Build contracts
anchor build

# Run tests
anchor test
```

## Performance Requirements
- Execution time: <1ms per transaction
- Compute units: <30K per transaction
- Throughput: 1000+ TPS sustained

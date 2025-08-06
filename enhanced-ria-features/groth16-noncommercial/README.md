# Groth16 Non-Commercial ZKP Implementation

This directory contains the non-commercial Groth16 ZKP implementation that works in tandem with the production Noir ZKP system. This implementation is designed for:

- **Educational purposes**
- **Research and development**
- **Testing and comparison with Noir ZKP**
- **Non-commercial applications**

## Architecture

The Groth16 implementation provides an alternative ZKP path that can be used alongside the Noir ZKP system for comparison and testing purposes.

### Key Components

1. **Stake Proof Circuit** (`stake_proof_circuit.circom`) - Anonymous stake verification with Merkle tree proofs
2. **Circuit Compiler** (`groth16_compiler.js`) - Compilation and proof generation utilities
3. **Integration Layer** (`groth16_integration.py`) - Python integration for testing
4. **Test Suite** (`tests/`) - Comprehensive testing for non-commercial use

### Usage

This implementation is intended for:
- Academic research
- Educational demonstrations
- Development testing
- Performance comparisons with Noir ZKP

### License

This implementation is provided for non-commercial use only. For commercial applications, please use the Noir ZKP implementation in `/noir-voting/`.

## Integration with Noir ZKP

The Groth16 implementation works in tandem with the Noir ZKP system:

```python
# Example: Dual-path ZKP verification
from noir_voting.enhanced_noir_integration import NoirEnhancedVotingSystem
from groth16_noncommercial.groth16_integration import Groth16VotingSystem

# Production path (Noir)
noir_system = NoirEnhancedVotingSystem()
noir_result = await noir_system.submitEnhancedVote(vote, wallet_signature)

# Non-commercial path (Groth16) - for testing/comparison
groth16_system = Groth16VotingSystem()
groth16_result = await groth16_system.generateStakeProof(stake_amount, merkle_proof)

# Compare results for validation
assert noir_result.verified == groth16_result.verified
```

## Patent Differentiation

Both implementations maintain clear patent differentiation:
- **Noir ZKP**: Off-chain proof verification with PLUME signatures
- **Groth16**: Traditional ZKP with Merkle tree stake verification
- **Common Strategy**: Zero-knowledge proofs vs blockchain data queries (US20200258338A1)

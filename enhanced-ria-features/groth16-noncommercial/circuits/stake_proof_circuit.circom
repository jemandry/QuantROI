pragma circom 2.0.0;

// NON-COMMERCIAL USE ONLY - EDUCATIONAL AND RESEARCH PURPOSES
// This Groth16 implementation works in tandem with the production Noir ZKP system
// For commercial applications, use the Noir ZKP implementation in /noir-voting/

include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/merkletree.circom";

template StakeProofCircuit() {
    // NON-COMMERCIAL EDUCATIONAL INPUTS
    signal input stake_amount;
    signal input merkle_proof[10];
    signal input merkle_root;
    signal private input private_key;
    
    // NON-COMMERCIAL EDUCATIONAL OUTPUT
    signal output valid_stake;
    signal output stake_commitment;
    
    // Educational constraint: minimum stake requirement
    component min_stake_check = GreaterEqualThan(32);
    min_stake_check.in[0] <== stake_amount;
    min_stake_check.in[1] <== 100; // Minimum 100 units for educational example
    
    // Educational Merkle tree verification
    component merkle_verifier = MerkleTreeChecker(10);
    merkle_verifier.leaf <== stake_amount;
    merkle_verifier.root <== merkle_root;
    for (var i = 0; i < 10; i++) {
        merkle_verifier.pathElements[i] <== merkle_proof[i];
    }
    
    // Educational stake commitment generation
    component commitment_hasher = Poseidon(2);
    commitment_hasher.inputs[0] <== stake_amount;
    commitment_hasher.inputs[1] <== private_key;
    stake_commitment <== commitment_hasher.out;
    
    // Educational validation: stake is valid if minimum met and Merkle proof valid
    valid_stake <== min_stake_check.out * merkle_verifier.root;
}

// Educational component instantiation
component main = StakeProofCircuit();

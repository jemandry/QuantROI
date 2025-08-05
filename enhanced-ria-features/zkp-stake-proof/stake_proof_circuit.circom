pragma circom 2.0.0;

/*
Zero-Knowledge Stake Proof Circuit
Proves stake/token rights to vote without revealing wallet identity
Implements Groth16 via snarkjs for anonymous yet verifiable voting
*/

include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/bitify.circom";

template StakeProofCircuit(n) {
    // Public inputs
    signal input merkleRoot;           // Merkle root of all valid stakes
    signal input minStakeThreshold;    // Minimum stake required to vote
    signal input nullifierHash;       // Prevents double voting
    
    // Private inputs (witness)
    signal input stakeAmount;         // Actual stake amount (private)
    signal input walletSecret;        // Wallet private key or secret
    signal input merkleProof[n];      // Merkle proof of stake inclusion
    signal input merkleIndices[n];    // Path indices for Merkle proof
    
    // Outputs
    signal output validStake;         // 1 if stake is valid, 0 otherwise
    signal output nullifier;          // Unique nullifier to prevent double voting
    
    // Components
    component stakeCheck = GreaterEqualThan(64);
    component merkleVerifier = MerkleTreeVerifier(n);
    component nullifierHasher = Poseidon(2);
    component stakeHasher = Poseidon(2);
    
    // Verify stake amount meets minimum threshold
    stakeCheck.in[0] <== stakeAmount;
    stakeCheck.in[1] <== minStakeThreshold;
    
    // Generate stake commitment hash
    stakeHasher.inputs[0] <== stakeAmount;
    stakeHasher.inputs[1] <== walletSecret;
    
    // Verify Merkle proof of stake inclusion
    merkleVerifier.leaf <== stakeHasher.out;
    merkleVerifier.root <== merkleRoot;
    for (var i = 0; i < n; i++) {
        merkleVerifier.pathElements[i] <== merkleProof[i];
        merkleVerifier.pathIndices[i] <== merkleIndices[i];
    }
    
    // Generate nullifier to prevent double voting
    nullifierHasher.inputs[0] <== walletSecret;
    nullifierHasher.inputs[1] <== merkleRoot; // Bind to specific voting round
    nullifier <== nullifierHasher.out;
    
    // Verify nullifier matches expected value
    nullifierHash === nullifier;
    
    // Output valid stake only if all conditions met
    validStake <== stakeCheck.out * merkleVerifier.valid;
}

template MerkleTreeVerifier(n) {
    signal input leaf;
    signal input root;
    signal input pathElements[n];
    signal input pathIndices[n];
    
    signal output valid;
    
    component hashers[n];
    component selectors[n];
    
    signal computedHash[n+1];
    computedHash[0] <== leaf;
    
    for (var i = 0; i < n; i++) {
        selectors[i] = Selector();
        selectors[i].in[0] <== computedHash[i];
        selectors[i].in[1] <== pathElements[i];
        selectors[i].sel <== pathIndices[i];
        
        hashers[i] = Poseidon(2);
        hashers[i].inputs[0] <== selectors[i].out[0];
        hashers[i].inputs[1] <== selectors[i].out[1];
        
        computedHash[i+1] <== hashers[i].out;
    }
    
    component rootCheck = IsEqual();
    rootCheck.in[0] <== computedHash[n];
    rootCheck.in[1] <== root;
    
    valid <== rootCheck.out;
}

template Selector() {
    signal input in[2];
    signal input sel;
    signal output out[2];
    
    // If sel == 0: out[0] = in[0], out[1] = in[1]
    // If sel == 1: out[0] = in[1], out[1] = in[0]
    out[0] <== in[0] + sel * (in[1] - in[0]);
    out[1] <== in[1] + sel * (in[0] - in[1]);
}

// Main circuit with 20-level Merkle tree (supports ~1M stakes)
component main = StakeProofCircuit(20);

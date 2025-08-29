pragma circom 2.0.0;

/*
ZKP Voting Circuit - US20200258338A1 Implementation
Implements Claim 3 (random vote IDs) and Claim 9 (hash verification)
for anonymous yet verifiable voting in RIA governance systems
*/

include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/bitify.circom";

template VotingCircuit(n) {
    // Public inputs
    signal input merkleRoot;           // Root of eligible voters tree
    signal input voteCommitment;       // Hash of vote choice + nonce
    signal input nullifierHash;       // Prevents double voting (Claim 5)
    signal input randomSeed;           // For random vote ID generation (Claim 3)
    
    // Private inputs (witness)
    signal input voterSecret;         // Voter's private key/secret
    signal input voteChoice;          // Actual vote (0 or 1)
    signal input nonce;               // Random nonce for commitment
    signal input merkleProof[n];      // Proof of voter eligibility
    signal input merkleIndices[n];    // Path indices for Merkle proof
    
    // Outputs
    signal output randomVoteID;       // Random vote identifier (Claim 3)
    signal output nullifier;          // Unique nullifier to prevent double voting
    signal output validVote;          // 1 if vote is valid, 0 otherwise
    
    // Components
    component merkleVerifier = MerkleTreeVerifier(n);
    component commitmentHasher = Poseidon(2);
    component nullifierHasher = Poseidon(2);
    component randomIDGenerator = Poseidon(3);
    component voterHasher = Poseidon(1);
    component voteValidator = IsEqual();
    
    // Generate voter commitment hash for Merkle tree
    voterHasher.inputs[0] <== voterSecret;
    
    // Verify voter eligibility through Merkle proof
    merkleVerifier.leaf <== voterHasher.out;
    merkleVerifier.root <== merkleRoot;
    for (var i = 0; i < n; i++) {
        merkleVerifier.pathElements[i] <== merkleProof[i];
        merkleVerifier.pathIndices[i] <== merkleIndices[i];
    }
    
    // Verify vote commitment (Claim 9: hash verification)
    commitmentHasher.inputs[0] <== voteChoice;
    commitmentHasher.inputs[1] <== nonce;
    
    voteValidator.in[0] <== commitmentHasher.out;
    voteValidator.in[1] <== voteCommitment;
    
    // Generate random vote ID (Claim 3: random vote IDs)
    randomIDGenerator.inputs[0] <== voterSecret;
    randomIDGenerator.inputs[1] <== randomSeed;
    randomIDGenerator.inputs[2] <== voteCommitment;
    randomVoteID <== randomIDGenerator.out;
    
    // Generate nullifier to prevent double voting
    nullifierHasher.inputs[0] <== voterSecret;
    nullifierHasher.inputs[1] <== merkleRoot; // Bind to specific voting round
    nullifier <== nullifierHasher.out;
    
    // Verify nullifier matches expected value
    nullifierHash === nullifier;
    
    // Output valid vote only if all conditions met
    validVote <== merkleVerifier.valid * voteValidator.out;
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

// Main circuit with 16-level Merkle tree (supports ~65K voters)
component main = VotingCircuit(16);

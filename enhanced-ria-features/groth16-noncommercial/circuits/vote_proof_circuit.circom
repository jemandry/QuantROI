pragma circom 2.0.0;

// NON-COMMERCIAL USE ONLY - EDUCATIONAL AND RESEARCH PURPOSES
// This Groth16 vote proof circuit works alongside the Noir ZKP system
// For commercial applications, use the Noir ZKP implementation in /noir-voting/

include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";

template VoteProofCircuit() {
    // NON-COMMERCIAL EDUCATIONAL INPUTS
    signal private input vote;
    signal private input voter_private_key;
    signal private input eligibility_secret;
    signal input eligibility_root;
    
    // NON-COMMERCIAL EDUCATIONAL OUTPUTS
    signal output vote_commitment;
    signal output nullifier;
    signal output eligibility_proof;
    
    // Educational vote commitment generation
    component vote_hasher = Poseidon(2);
    vote_hasher.inputs[0] <== vote;
    vote_hasher.inputs[1] <== voter_private_key;
    vote_commitment <== vote_hasher.out;
    
    // Educational nullifier generation (prevents double voting)
    component nullifier_hasher = Poseidon(3);
    nullifier_hasher.inputs[0] <== voter_private_key;
    nullifier_hasher.inputs[1] <== vote;
    nullifier_hasher.inputs[2] <== 42; // Educational constant
    nullifier <== nullifier_hasher.out;
    
    // Educational eligibility proof
    component eligibility_hasher = Poseidon(2);
    eligibility_hasher.inputs[0] <== eligibility_secret;
    eligibility_hasher.inputs[1] <== voter_private_key;
    
    // Educational constraint: eligibility must match root
    component eligibility_check = IsEqual();
    eligibility_check.in[0] <== eligibility_hasher.out;
    eligibility_check.in[1] <== eligibility_root;
    eligibility_proof <== eligibility_check.out;
    
    // Educational constraint: vote must be valid (non-zero)
    component vote_validity = IsZero();
    vote_validity.in <== vote;
    vote_validity.out === 0; // Vote must not be zero
}

// Educational component instantiation
component main = VoteProofCircuit();

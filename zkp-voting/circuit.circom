pragma circom 2.0.0;

include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";

template VotingCircuit() {
    signal private input vote;
    signal private input stake_amount;
    signal private input voter_type;
    signal private input secret_key;
    
    signal input issue_id;
    signal input min_stake_required;
    signal input voting_deadline;
    signal input current_timestamp;
    
    signal output vote_commitment;
    signal output stake_proof;
    signal output eligibility_proof;
    
    component stake_check = GreaterEqThan(64);
    component deadline_check = LessEqThan(64);
    
    stake_check.in[0] <== stake_amount;
    stake_check.in[1] <== min_stake_required;
    stake_check.out === 1;
    
    deadline_check.in[0] <== current_timestamp;
    deadline_check.in[1] <== voting_deadline;
    deadline_check.out === 1;
    
    component hasher = Poseidon(4);
    hasher.inputs[0] <== vote;
    hasher.inputs[1] <== stake_amount;
    hasher.inputs[2] <== voter_type;
    hasher.inputs[3] <== secret_key;
    vote_commitment <== hasher.out;
    
    component stake_hasher = Poseidon(1);
    stake_hasher.inputs[0] <== stake_amount;
    stake_proof <== stake_hasher.out;
    
    component eligibility_hasher = Poseidon(2);
    eligibility_hasher.inputs[0] <== voter_type;
    eligibility_hasher.inputs[1] <== stake_amount;
    eligibility_proof <== eligibility_hasher.out;
}

component main = VotingCircuit();

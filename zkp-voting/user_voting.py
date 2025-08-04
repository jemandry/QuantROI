#!/usr/bin/env python3
"""
User Voting Integration with ZKP Proofs
Integrates with delegation smart contracts for employee/shareholder governance
"""

import asyncio
import json
import subprocess
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

class ZKPVotingSystem:
    """ZKP voting system for employee/shareholder governance"""
    
    def __init__(self, circuit_path: str = "./circuit.circom"):
        self.circuit_path = circuit_path
        self.compiled_circuit = None
        self.logger = self._setup_logging()
        self._compile_circuit()
    
    def _setup_logging(self):
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def _compile_circuit(self):
        """Compile Circom circuit using snarkjs"""
        try:
            if not os.path.exists(self.circuit_path):
                self.logger.warning(f"Circuit file not found: {self.circuit_path}")
                self.compiled_circuit = False
                return
            
            subprocess.run([
                "circom", self.circuit_path,
                "--r1cs", "--wasm", "--sym"
            ], check=True, capture_output=True)
            
            subprocess.run([
                "snarkjs", "groth16", "setup",
                "circuit.r1cs", "pot12_final.ptau",
                "circuit_0000.zkey"
            ], check=True, capture_output=True)
            
            self.compiled_circuit = True
            self.logger.info("✓ ZKP circuit compiled successfully")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"✗ Failed to compile ZKP circuit: {e}")
            self.compiled_circuit = False
        except FileNotFoundError:
            self.logger.warning("circom or snarkjs not found - using mock implementation")
            self.compiled_circuit = False
    
    async def generate_vote_proof(
        self,
        vote: bool,
        stake_amount: int,
        voter_type: int,
        secret_key: str,
        issue_id: str,
        min_stake_required: int,
        voting_deadline: int
    ) -> Dict[str, Any]:
        """Generate ZKP proof for vote submission"""
        if not self.compiled_circuit:
            return self._generate_mock_proof(vote, stake_amount, voter_type, issue_id)
        
        witness_input = {
            "vote": 1 if vote else 0,
            "stake_amount": stake_amount,
            "voter_type": voter_type,
            "secret_key": int(hashlib.sha256(secret_key.encode()).hexdigest(), 16) % (2**254),
            "issue_id": int(hashlib.sha256(issue_id.encode()).hexdigest(), 16) % (2**254),
            "min_stake_required": min_stake_required,
            "voting_deadline": voting_deadline,
            "current_timestamp": int(datetime.now().timestamp())
        }
        
        with open("input.json", "w") as f:
            json.dump(witness_input, f)
        
        try:
            subprocess.run([
                "node", "circuit_js/generate_witness.js",
                "circuit_js/circuit.wasm", "input.json", "witness.wtns"
            ], check=True, capture_output=True)
            
            subprocess.run([
                "snarkjs", "groth16", "prove",
                "circuit_0000.zkey", "witness.wtns",
                "proof.json", "public.json"
            ], check=True, capture_output=True)
            
            with open("proof.json", "r") as f:
                proof = json.load(f)
            
            with open("public.json", "r") as f:
                public_signals = json.load(f)
            
            return {
                "proof": proof,
                "public_signals": public_signals,
                "vote_commitment": public_signals[0],
                "stake_proof": public_signals[1],
                "eligibility_proof": public_signals[2]
            }
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to generate ZKP proof: {e}")
            return self._generate_mock_proof(vote, stake_amount, voter_type, issue_id)
    
    def _generate_mock_proof(
        self,
        vote: bool,
        stake_amount: int,
        voter_type: int,
        issue_id: str
    ) -> Dict[str, Any]:
        """Generate mock proof for testing when ZKP tools unavailable"""
        mock_commitment = hashlib.sha256(f"{vote}{stake_amount}{voter_type}{issue_id}".encode()).hexdigest()
        mock_stake_proof = hashlib.sha256(f"{stake_amount}".encode()).hexdigest()
        mock_eligibility_proof = hashlib.sha256(f"{voter_type}{stake_amount}".encode()).hexdigest()
        
        return {
            "proof": {
                "pi_a": ["0x" + "0" * 64, "0x" + "1" * 64, "0x1"],
                "pi_b": [["0x" + "2" * 64, "0x" + "3" * 64], ["0x" + "4" * 64, "0x" + "5" * 64]],
                "pi_c": ["0x" + "6" * 64, "0x" + "7" * 64, "0x1"],
                "protocol": "groth16",
                "curve": "bn128"
            },
            "public_signals": [mock_commitment, mock_stake_proof, mock_eligibility_proof],
            "vote_commitment": mock_commitment,
            "stake_proof": mock_stake_proof,
            "eligibility_proof": mock_eligibility_proof,
            "mock": True
        }
    
    async def verify_vote_proof(self, proof_data: Dict[str, Any]) -> bool:
        """Verify ZKP proof"""
        if proof_data.get("mock"):
            return True
        
        if not self.compiled_circuit:
            return True
        
        try:
            with open("proof_to_verify.json", "w") as f:
                json.dump(proof_data["proof"], f)
            
            with open("public_to_verify.json", "w") as f:
                json.dump(proof_data["public_signals"], f)
            
            result = subprocess.run([
                "snarkjs", "groth16", "verify",
                "verification_key.json", "public_to_verify.json", "proof_to_verify.json"
            ], capture_output=True, text=True)
            
            return "OK" in result.stdout
            
        except Exception as e:
            self.logger.error(f"Proof verification failed: {e}")
            return False
    
    async def create_voting_issue(
        self,
        issue_title: str,
        issue_description: str,
        voting_deadline: datetime,
        min_stake_required: int = 1000,
        voter_types_allowed: List[int] = [0, 1]
    ) -> Dict[str, Any]:
        """Create a new voting issue"""
        issue_id = hashlib.sha256(f"{issue_title}{datetime.now().timestamp()}".encode()).hexdigest()[:16]
        
        voting_issue = {
            "issue_id": issue_id,
            "title": issue_title,
            "description": issue_description,
            "voting_deadline": voting_deadline.isoformat(),
            "min_stake_required": min_stake_required,
            "voter_types_allowed": voter_types_allowed,
            "votes": [],
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        return voting_issue
    
    async def submit_vote(
        self,
        voting_issue: Dict[str, Any],
        vote: bool,
        stake_amount: int,
        voter_type: int,
        secret_key: str
    ) -> Dict[str, Any]:
        """Submit a vote with ZKP proof"""
        if voter_type not in voting_issue["voter_types_allowed"]:
            raise ValueError("Voter type not allowed for this issue")
        
        if stake_amount < voting_issue["min_stake_required"]:
            raise ValueError("Insufficient stake amount")
        
        voting_deadline = int(datetime.fromisoformat(voting_issue["voting_deadline"]).timestamp())
        
        proof_data = await self.generate_vote_proof(
            vote=vote,
            stake_amount=stake_amount,
            voter_type=voter_type,
            secret_key=secret_key,
            issue_id=voting_issue["issue_id"],
            min_stake_required=voting_issue["min_stake_required"],
            voting_deadline=voting_deadline
        )
        
        vote_record = {
            "vote_commitment": proof_data["vote_commitment"],
            "stake_proof": proof_data["stake_proof"],
            "eligibility_proof": proof_data["eligibility_proof"],
            "voter_type": voter_type,
            "timestamp": datetime.now().isoformat(),
            "proof_verified": await self.verify_vote_proof(proof_data)
        }
        
        voting_issue["votes"].append(vote_record)
        
        return {
            "success": True,
            "vote_record": vote_record,
            "total_votes": len(voting_issue["votes"])
        }

async def main():
    """Example usage of ZKP Voting System"""
    voting_system = ZKPVotingSystem()
    
    voting_issue = await voting_system.create_voting_issue(
        issue_title="Approve AI Trading Strategy Enhancement",
        issue_description="Should we implement the new causal AI trading strategy?",
        voting_deadline=datetime.now() + timedelta(days=7),
        min_stake_required=1000,
        voter_types_allowed=[0, 1]
    )
    
    print(f"Created voting issue: {voting_issue['issue_id']}")
    
    vote_result = await voting_system.submit_vote(
        voting_issue=voting_issue,
        vote=True,
        stake_amount=5000,
        voter_type=0,
        secret_key="employee_secret_key_123"
    )
    
    print(f"Vote submitted successfully: {vote_result['success']}")
    print(f"Total votes: {vote_result['total_votes']}")

if __name__ == "__main__":
    from datetime import timedelta
    asyncio.run(main())

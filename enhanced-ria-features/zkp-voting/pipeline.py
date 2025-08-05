#!/usr/bin/env python3
"""
ZKP Voting Pipeline - snarkjs Integration
Implements US20200258338A1 verification pipeline for RIA governance
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

@dataclass
class VoteProof:
    """ZKP vote proof structure"""
    proof: Dict
    public_signals: List[str]
    random_vote_id: str
    nullifier: str
    timestamp: int

@dataclass
class VotingConfig:
    """Voting system configuration"""
    circuit_path: str = "circuit.circom"
    circuit_wasm: str = "circuit.wasm"
    circuit_zkey: str = "circuit_final.zkey"
    merkle_depth: int = 16
    max_voters: int = 65536
    vote_timeout: int = 300  # 5 minutes

class ZKPVotingPipeline:
    """
    ZKP Voting Pipeline implementing US20200258338A1
    Provides anonymous, verifiable voting with random IDs
    """
    
    def __init__(self, config: VotingConfig):
        self.config = config
        self.circuit_dir = Path(__file__).parent
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zkp_voting_"))
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for voting pipeline"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def compile_circuit(self) -> bool:
        """
        Compile Circom circuit using Rust-based Circom 2.x
        Returns True if compilation successful
        """
        try:
            circuit_path = self.circuit_dir / self.config.circuit_path
            
            if not circuit_path.exists():
                logger.error(f"Circuit file not found: {circuit_path}")
                return False
            
            circomlib_dir = self.circuit_dir / "circomlib"
            if not circomlib_dir.exists():
                logger.info("Setting up circomlib directory...")
                circomlib_dir.mkdir(exist_ok=True)
                
                system_circomlib = Path("/tmp/circomlib/circuits")
                if system_circomlib.exists():
                    import shutil
                    shutil.copytree(system_circomlib, circomlib_dir / "circuits", dirs_exist_ok=True)
            
            circom_cmd = [
                "/tmp/circom/target/release/circom",
                str(circuit_path),
                "--r1cs",
                "--wasm",
                "--sym",
                "--output", str(self.temp_dir)
            ]
            
            logger.info(f"Compiling circuit: {' '.join(circom_cmd)}")
            result = await asyncio.create_subprocess_exec(
                *circom_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.circuit_dir
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info("✅ Circuit compilation successful")
                return True
            else:
                logger.error(f"❌ Circuit compilation failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Circuit compilation error: {e}")
            return False
    
    async def setup_trusted_setup(self) -> bool:
        """
        Setup trusted setup for Groth16 (Powers of Tau + circuit-specific)
        Returns True if setup successful
        """
        try:
            logger.info("Setting up trusted setup...")
            
            ptau_file = self.temp_dir / "pot16_final.ptau"
            
            if not ptau_file.exists():
                logger.info("Downloading Powers of Tau file...")
                ptau_cmd = [
                    "snarkjs", "powersoftau", "new", "bn128", "16",
                    str(self.temp_dir / "pot16_0000.ptau"), "-v"
                ]
                
                result = await asyncio.create_subprocess_exec(*ptau_cmd)
                await result.communicate()
                
                if result.returncode != 0:
                    logger.error("Powers of Tau setup failed")
                    return False
            
            r1cs_file = self.temp_dir / "circuit.r1cs"
            zkey_file = self.temp_dir / self.config.circuit_zkey
            
            if r1cs_file.exists():
                setup_cmd = [
                    "snarkjs", "groth16", "setup",
                    str(r1cs_file),
                    str(ptau_file),
                    str(zkey_file)
                ]
                
                result = await asyncio.create_subprocess_exec(*setup_cmd)
                await result.communicate()
                
                if result.returncode == 0:
                    logger.info("✅ Trusted setup completed")
                    return True
                else:
                    logger.error("❌ Trusted setup failed")
                    return False
            else:
                logger.error("R1CS file not found for trusted setup")
                return False
                
        except Exception as e:
            logger.error(f"Trusted setup error: {e}")
            return False
    
    async def generate_vote_proof(
        self,
        voter_secret: str,
        vote_choice: int,
        merkle_root: str,
        merkle_proof: List[str],
        merkle_indices: List[int],
        random_seed: str
    ) -> Optional[VoteProof]:
        """
        Generate ZKP proof for vote (Claim 3: random IDs, Claim 9: verification)
        """
        try:
            nonce = os.urandom(32).hex()
            
            vote_commitment = self._hash_commitment(vote_choice, nonce)
            
            nullifier_hash = self._generate_nullifier(voter_secret, merkle_root)
            
            circuit_inputs = {
                "merkleRoot": merkle_root,
                "voteCommitment": vote_commitment,
                "nullifierHash": nullifier_hash,
                "randomSeed": random_seed,
                "voterSecret": voter_secret,
                "voteChoice": str(vote_choice),
                "nonce": nonce,
                "merkleProof": merkle_proof,
                "merkleIndices": [str(idx) for idx in merkle_indices]
            }
            
            input_file = self.temp_dir / "input.json"
            async with aiofiles.open(input_file, 'w') as f:
                await f.write(json.dumps(circuit_inputs, indent=2))
            
            witness_file = self.temp_dir / "witness.wtns"
            wasm_file = self.temp_dir / "circuit.wasm"
            
            witness_cmd = [
                "node",
                str(self.temp_dir / "circuit_js" / "generate_witness.js"),
                str(wasm_file),
                str(input_file),
                str(witness_file)
            ]
            
            result = await asyncio.create_subprocess_exec(*witness_cmd)
            await result.communicate()
            
            if result.returncode != 0:
                logger.error("Witness generation failed")
                return None
            
            proof_file = self.temp_dir / "proof.json"
            public_file = self.temp_dir / "public.json"
            zkey_file = self.temp_dir / self.config.circuit_zkey
            
            proof_cmd = [
                "snarkjs", "groth16", "prove",
                str(zkey_file),
                str(witness_file),
                str(proof_file),
                str(public_file)
            ]
            
            result = await asyncio.create_subprocess_exec(*proof_cmd)
            await result.communicate()
            
            if result.returncode != 0:
                logger.error("Proof generation failed")
                return None
            
            async with aiofiles.open(proof_file, 'r') as f:
                proof_data = json.loads(await f.read())
            
            async with aiofiles.open(public_file, 'r') as f:
                public_signals = json.loads(await f.read())
            
            random_vote_id = public_signals[0] if public_signals else ""
            nullifier = public_signals[1] if len(public_signals) > 1 else ""
            
            logger.info("✅ Vote proof generated successfully")
            
            return VoteProof(
                proof=proof_data,
                public_signals=public_signals,
                random_vote_id=random_vote_id,
                nullifier=nullifier,
                timestamp=int(time.time())
            )
            
        except Exception as e:
            logger.error(f"Vote proof generation error: {e}")
            return None
    
    async def verify_vote_proof(self, vote_proof: VoteProof) -> bool:
        """
        Verify ZKP vote proof using snarkjs
        """
        try:
            proof_file = self.temp_dir / "verify_proof.json"
            public_file = self.temp_dir / "verify_public.json"
            vkey_file = self.temp_dir / "verification_key.json"
            
            async with aiofiles.open(proof_file, 'w') as f:
                await f.write(json.dumps(vote_proof.proof, indent=2))
            
            async with aiofiles.open(public_file, 'w') as f:
                await f.write(json.dumps(vote_proof.public_signals, indent=2))
            
            zkey_file = self.temp_dir / self.config.circuit_zkey
            if zkey_file.exists():
                vkey_cmd = [
                    "snarkjs", "zkey", "export", "verificationkey",
                    str(zkey_file),
                    str(vkey_file)
                ]
                
                result = await asyncio.create_subprocess_exec(*vkey_cmd)
                await result.communicate()
                
                if result.returncode != 0:
                    logger.error("Verification key export failed")
                    return False
            
            verify_cmd = [
                "snarkjs", "groth16", "verify",
                str(vkey_file),
                str(public_file),
                str(proof_file)
            ]
            
            result = await asyncio.create_subprocess_exec(
                *verify_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and b"OK" in stdout:
                logger.info("✅ Vote proof verification successful")
                return True
            else:
                logger.error(f"❌ Vote proof verification failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Vote proof verification error: {e}")
            return False
    
    def _hash_commitment(self, vote_choice: int, nonce: str) -> str:
        """Generate vote commitment hash"""
        data = f"{vote_choice}{nonce}".encode()
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data)
        return digest.finalize().hex()
    
    def _generate_nullifier(self, voter_secret: str, merkle_root: str) -> str:
        """Generate nullifier to prevent double voting"""
        data = f"{voter_secret}{merkle_root}".encode()
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data)
        return digest.finalize().hex()
    
    async def cleanup(self):
        """Cleanup temporary files"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

async def main():
    """Demo ZKP voting pipeline"""
    config = VotingConfig()
    pipeline = ZKPVotingPipeline(config)
    
    try:
        if not await pipeline.compile_circuit():
            return
        
        if not await pipeline.setup_trusted_setup():
            return
        
        vote_proof = await pipeline.generate_vote_proof(
            voter_secret="demo_secret_123",
            vote_choice=1,
            merkle_root="0x1234567890abcdef",
            merkle_proof=["0x" + "0" * 64] * 16,
            merkle_indices=[0] * 16,
            random_seed="demo_seed_456"
        )
        
        if vote_proof:
            is_valid = await pipeline.verify_vote_proof(vote_proof)
            print(f"Vote proof valid: {is_valid}")
            print(f"Random Vote ID: {vote_proof.random_vote_id}")
            print(f"Nullifier: {vote_proof.nullifier}")
        
    finally:
        await pipeline.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

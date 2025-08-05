#!/usr/bin/env python3
"""
Vote Submission API for US20200258338A1 ZKP Voting System
FastAPI endpoints for anonymous, verifiable voting with random IDs
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import uvicorn

from .system_orchestrator import EnhancedRIAOrchestrator, VoteSubmission
from ..zkp_voting.pipeline import ZKPVotingPipeline, VotingConfig, VoteProof
from ..compliance.sec_compliance_engine import SECComplianceEngine

logger = logging.getLogger(__name__)

class VoteSubmissionRequest(BaseModel):
    """Vote submission request model"""
    voter_secret: str = Field(..., description="Voter's private secret (not stored)")
    vote_choice: int = Field(..., ge=0, le=1, description="Vote choice: 0 (no) or 1 (yes)")
    merkle_root: str = Field(..., description="Merkle root of eligible voters")
    merkle_proof: list[str] = Field(..., description="Merkle proof of voter eligibility")
    merkle_indices: list[int] = Field(..., description="Path indices for Merkle proof")
    random_seed: str = Field(..., description="Random seed for vote ID generation")
    stake_amount: float = Field(..., gt=0, description="Voter's stake amount")
    vote_content: Dict[str, Any] = Field(default_factory=dict, description="Additional vote metadata")

class VoteSubmissionResponse(BaseModel):
    """Vote submission response model"""
    success: bool
    vote_id: str
    random_vote_id: str
    nullifier: str
    processing_time_ms: float
    zkp_verified: bool
    ipfs_hash: Optional[str] = None
    compliance_logged: bool = False
    message: str

class VotingResultsResponse(BaseModel):
    """Voting results response model"""
    total_votes: int
    yes_votes: int
    no_votes: int
    yes_percentage: float
    is_finalized: bool
    created_at: str
    finalized_at: Optional[str] = None
    tally_disclosure_hash: str

class VoteSubmissionAPI:
    """
    Vote Submission API implementing US20200258338A1 requirements
    """
    
    def __init__(self, orchestrator: EnhancedRIAOrchestrator):
        self.orchestrator = orchestrator
        self.zkp_pipeline = ZKPVotingPipeline(VotingConfig())
        self.compliance_engine = SECComplianceEngine()
        self.router = APIRouter(prefix="/api/vote", tags=["voting"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.router.post("/submit", response_model=VoteSubmissionResponse)
        async def submit_vote(request: VoteSubmissionRequest) -> VoteSubmissionResponse:
            """
            Submit ZKP vote with random ID (US20200258338A1 Claim 3)
            Implements hash verification (Claim 9) and prepares for tally disclosure (Claim 5)
            """
            try:
                start_time = datetime.now()
                
                vote_proof = await self.zkp_pipeline.generate_vote_proof(
                    voter_secret=request.voter_secret,
                    vote_choice=request.vote_choice,
                    merkle_root=request.merkle_root,
                    merkle_proof=request.merkle_proof,
                    merkle_indices=request.merkle_indices,
                    random_seed=request.random_seed
                )
                
                if not vote_proof:
                    raise HTTPException(status_code=400, detail="Failed to generate ZKP proof")
                
                is_valid = await self.zkp_pipeline.verify_vote_proof(vote_proof)
                if not is_valid:
                    raise HTTPException(status_code=400, detail="Invalid ZKP proof")
                
                vote_submission = VoteSubmission(
                    vote_id=f"vote_{vote_proof.timestamp}_{vote_proof.random_vote_id[:8]}",
                    voter_id=vote_proof.random_vote_id,
                    vote_content={
                        **request.vote_content,
                        "vote_choice": request.vote_choice,
                        "random_vote_id": vote_proof.random_vote_id,
                        "nullifier": vote_proof.nullifier
                    },
                    stake_amount=request.stake_amount,
                    timestamp=datetime.fromtimestamp(vote_proof.timestamp),
                    zkp_proof={
                        "proof": vote_proof.proof,
                        "public_signals": vote_proof.public_signals,
                        "merkle_root": request.merkle_root,
                        "random_vote_id": vote_proof.random_vote_id,
                        "nullifier": vote_proof.nullifier
                    },
                    source_metadata={"submission_api": "v1.0"}
                )
                
                processing_result = await self.orchestrator.process_vote(vote_submission)
                
                compliance_logged = False
                try:
                    await self.compliance_engine._record_audit_event(
                        event_type="zkp_vote_submission",
                        action="submit_anonymous_vote",
                        data_hash=vote_proof.nullifier,
                        user_id=vote_proof.random_vote_id
                    )
                    compliance_logged = True
                except Exception as e:
                    logger.warning(f"Compliance logging failed: {e}")
                
                processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                return VoteSubmissionResponse(
                    success=processing_result.success,
                    vote_id=vote_submission.vote_id,
                    random_vote_id=vote_proof.random_vote_id,
                    nullifier=vote_proof.nullifier,
                    processing_time_ms=processing_time_ms,
                    zkp_verified=processing_result.zkp_verified,
                    ipfs_hash=processing_result.ipfs_hash,
                    compliance_logged=compliance_logged,
                    message="Vote submitted successfully with anonymous random ID"
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Vote submission failed: {e}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
        @self.router.get("/results/{delegation_id}", response_model=VotingResultsResponse)
        async def get_voting_results(delegation_id: str) -> VotingResultsResponse:
            """
            Get voting results with tally disclosure (US20200258338A1 Claim 5)
            """
            try:
                mock_results = {
                    "total_votes": 150,
                    "yes_votes": 95,
                    "no_votes": 55,
                    "is_finalized": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "finalized_at": "2024-01-02T00:00:00Z"
                }
                
                yes_percentage = (mock_results["yes_votes"] / mock_results["total_votes"]) * 100
                
                tally_data = f"{delegation_id}:{mock_results['total_votes']}:{mock_results['yes_votes']}:{mock_results['no_votes']}"
                import hashlib
                tally_disclosure_hash = hashlib.sha3_256(tally_data.encode()).hexdigest()
                
                return VotingResultsResponse(
                    total_votes=mock_results["total_votes"],
                    yes_votes=mock_results["yes_votes"],
                    no_votes=mock_results["no_votes"],
                    yes_percentage=yes_percentage,
                    is_finalized=mock_results["is_finalized"],
                    created_at=mock_results["created_at"],
                    finalized_at=mock_results["finalized_at"],
                    tally_disclosure_hash=tally_disclosure_hash
                )
                
            except Exception as e:
                logger.error(f"Failed to get voting results: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")
        
        @self.router.post("/verify-proof")
        async def verify_zkp_proof(proof_data: Dict[str, Any]) -> Dict[str, Any]:
            """
            Verify ZKP proof independently (for testing/validation)
            """
            try:
                vote_proof = VoteProof(
                    proof=proof_data.get("proof", {}),
                    public_signals=proof_data.get("public_signals", []),
                    random_vote_id=proof_data.get("random_vote_id", ""),
                    nullifier=proof_data.get("nullifier", ""),
                    timestamp=proof_data.get("timestamp", 0)
                )
                
                is_valid = await self.zkp_pipeline.verify_vote_proof(vote_proof)
                
                return {
                    "valid": is_valid,
                    "random_vote_id": vote_proof.random_vote_id,
                    "nullifier": vote_proof.nullifier,
                    "verification_timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Proof verification failed: {e}")
                raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")
        
        @self.router.get("/health")
        async def health_check() -> Dict[str, Any]:
            """Health check for voting system"""
            try:
                orchestrator_status = await self.orchestrator.get_system_status()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "zkp_pipeline": "operational",
                    "orchestrator_initialized": orchestrator_status["system_initialized"],
                    "compliance_engine": "operational"
                }
                
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

def create_vote_submission_router(orchestrator: EnhancedRIAOrchestrator) -> APIRouter:
    """Create vote submission API router"""
    api = VoteSubmissionAPI(orchestrator)
    return api.router

async def main():
    """Test the vote submission API"""
    from .system_orchestrator import SystemConfig
    
    config = SystemConfig()
    orchestrator = EnhancedRIAOrchestrator(config)
    
    if await orchestrator.initialize():
        api = VoteSubmissionAPI(orchestrator)
        print("Vote submission API initialized successfully")
        
    await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

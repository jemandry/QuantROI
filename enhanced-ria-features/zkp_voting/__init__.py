"""
ZKP Voting Module with Patent Avoidance Support
Implements both existing and patent-avoiding voting methods
"""

from .pipeline import ZKPVotingPipeline, VotingConfig, VoteProof

__all__ = [
    "ZKPVotingPipeline",
    "VotingConfig", 
    "VoteProof"
]

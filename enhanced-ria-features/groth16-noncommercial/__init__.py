"""
Groth16 Non-Commercial ZKP Implementation

This module provides a non-commercial Groth16 ZKP implementation that works
in tandem with the production Noir ZKP system for educational, research,
and testing purposes.

License: Non-commercial use only
"""

from .groth16_integration import Groth16VotingSystem, Groth16StakeProof
from .circuit_compiler import Groth16Compiler

__all__ = [
    'Groth16VotingSystem',
    'Groth16StakeProof', 
    'Groth16Compiler'
]

__license__ = "Non-commercial use only"
__purpose__ = "Educational, research, and testing"

"""
Patent Avoidance System - Separate Implementation Orchestrator
Provides patent-avoiding alternatives to existing implementations
"""

from .hybrid_system import (
    PatentAvoidanceOrchestrator,
    PatentAvoidanceConfig,
    ImplementationType
)

__all__ = [
    "PatentAvoidanceOrchestrator",
    "PatentAvoidanceConfig", 
    "ImplementationType"
]

"""
QuantROI Braided Cord Data Engine
High-performance data processing with scientific rigor frameworks
"""

__version__ = "0.1.0"
__author__ = "QuantROI Team"

from .granularity_limiter import GranularityLimiter
from .braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule, DataExtractionRequest
from .causal_analysis_engine import CausalAnalysisEngine
from .audit_trail_manager import AuditTrailManager

__all__ = [
    "GranularityLimiter",
    "BraidedCordDataEngine", 
    "CordPlacementRule",
    "DataExtractionRequest",
    "CausalAnalysisEngine",
    "AuditTrailManager"
]

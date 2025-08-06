"""
Storage Granularity Module for Enhanced RIA Platform

This module implements granularity limiting and resolution guard features
for financial data storage and retrieval, preventing over-magnification
of metrics and ensuring regulatory compliance.

License: Commercial use allowed
"""

from .granularity_limiter import (
    GranularityLimiter,
    MetricRequest,
    GranularityRule,
    GranularityValidationResult,
    MetricCategory,
    EnhancedDataExtractionRequest,
    create_sample_data
)
from .timescale_audit import TimescaleAuditLogger
from .reliability_monitor import DataReliabilityMonitor
from .integration_layer import GranularityIntegrationLayer

__all__ = [
    'GranularityLimiter',
    'MetricRequest', 
    'GranularityRule',
    'GranularityValidationResult',
    'MetricCategory',
    'EnhancedDataExtractionRequest',
    'create_sample_data',
    'TimescaleAuditLogger',
    'DataReliabilityMonitor',
    'GranularityIntegrationLayer'
]

__version__ = "1.0.0"
__description__ = "Granularity limiter for financial metrics with quantitative finance principles"

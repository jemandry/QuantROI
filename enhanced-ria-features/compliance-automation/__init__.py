"""
Compliance Automation Module
Phase 4: SEC integration, Form ADV generation, real-time monitoring
"""

from .sec_integration import SECComplianceEngine, ComplianceEvent, FormADVData
from .monitoring_dashboard import ComplianceMonitoringDashboard
from .production_deployment import ProductionDeploymentManager

__all__ = [
    'SECComplianceEngine',
    'ComplianceEvent', 
    'FormADVData',
    'ComplianceMonitoringDashboard',
    'ProductionDeploymentManager'
]

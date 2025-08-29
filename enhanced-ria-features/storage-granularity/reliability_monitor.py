"""
Real-time Data Reliability Monitoring for Granularity Limiter
Monitors data quality, drift, and anomalies in financial metrics
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataReliabilityMonitor:
    """Real-time monitoring for data quality and reliability"""
    
    def __init__(self):
        self.baseline_stats = {}
        self.alert_thresholds = {
            "missing_data_ratio": 0.1,
            "kurtosis_threshold": 3.0,
            "drift_threshold": 0.2,
            "schema_change": True
        }
        
    def monitor_data_quality(self, metric_name: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Monitor data quality and detect anomalies"""
        quality_report = {
            "metric_name": metric_name,
            "timestamp": datetime.now().isoformat(),
            "data_points": len(data),
            "alerts": []
        }
        
        missing_ratio = data.isna().sum().sum() / (len(data) * len(data.columns))
        quality_report["missing_data_ratio"] = missing_ratio
        
        if missing_ratio > self.alert_thresholds["missing_data_ratio"]:
            quality_report["alerts"].append({
                "type": "high_missing_data",
                "severity": "warning",
                "message": f"Missing data ratio {missing_ratio:.2%} exceeds threshold"
            })
        
        for column in data.select_dtypes(include=[np.number]).columns:
            kurtosis = data[column].kurtosis()
            if abs(kurtosis) > self.alert_thresholds["kurtosis_threshold"]:
                quality_report["alerts"].append({
                    "type": "over_magnification",
                    "severity": "error",
                    "message": f"High kurtosis ({kurtosis:.2f}) in {column} suggests over-magnification"
                })
        
        if metric_name in self.baseline_stats:
            drift_score = self._calculate_drift(metric_name, data)
            quality_report["drift_score"] = drift_score
            
            if drift_score > self.alert_thresholds["drift_threshold"]:
                quality_report["alerts"].append({
                    "type": "statistical_drift",
                    "severity": "warning", 
                    "message": f"Statistical drift detected: {drift_score:.2f}"
                })
        else:
            self._establish_baseline(metric_name, data)
        
        return quality_report
    
    def _calculate_drift(self, metric_name: str, current_data: pd.DataFrame) -> float:
        """Calculate statistical drift from baseline"""
        baseline = self.baseline_stats[metric_name]
        
        drift_scores = []
        for column in current_data.select_dtypes(include=[np.number]).columns:
            if column in baseline:
                current_mean = current_data[column].mean()
                current_std = current_data[column].std()
                
                baseline_mean = baseline[column]["mean"]
                baseline_std = baseline[column]["std"]
                
                mean_drift = abs(current_mean - baseline_mean) / (baseline_std + 1e-8)
                std_drift = abs(current_std - baseline_std) / (baseline_std + 1e-8)
                
                drift_scores.append(max(mean_drift, std_drift))
        
        return np.mean(drift_scores) if drift_scores else 0.0
    
    def _establish_baseline(self, metric_name: str, data: pd.DataFrame):
        """Establish statistical baseline for drift detection"""
        baseline = {}
        for column in data.select_dtypes(include=[np.number]).columns:
            baseline[column] = {
                "mean": data[column].mean(),
                "std": data[column].std(),
                "min": data[column].min(),
                "max": data[column].max()
            }
        
        self.baseline_stats[metric_name] = baseline
        logger.info(f"Established baseline statistics for {metric_name}")

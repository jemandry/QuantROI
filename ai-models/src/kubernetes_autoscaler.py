#!/usr/bin/env python3
"""
Kubernetes Auto-scaler Integration for System Health Monitoring
Connects system health metrics to Kubernetes HPA and cluster auto-scaling
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

@dataclass
class ScalingDecision:
    action: str
    target: str
    current_replicas: int
    desired_replicas: int
    reason: str
    urgency: str
    timestamp: float

class KubernetesAutoscaler:
    """
    Kubernetes auto-scaler that integrates with system health monitoring
    to make intelligent scaling decisions based on performance metrics
    """
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.k8s_apps_v1 = None
        self.k8s_autoscaling_v2 = None
        self.scaling_history: List[ScalingDecision] = []
        self.last_scaling_action = {}
        self.cooldown_period = 300  # 5 minutes between scaling actions
        
        try:
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            except config.ConfigException:
                config.load_kube_config()
                logger.info("Loaded local Kubernetes configuration")
            
            self.k8s_apps_v1 = client.AppsV1Api()
            self.k8s_autoscaling_v2 = client.AutoscalingV2Api()
            
        except Exception as e:
            logger.warning(f"Could not initialize Kubernetes client: {e}")
    
    async def evaluate_scaling_decision(self, health_metrics: Dict[str, Any]) -> List[ScalingDecision]:
        """
        Evaluate whether scaling actions should be taken based on health metrics
        """
        if not self.k8s_apps_v1:
            logger.warning("Kubernetes client not available - skipping scaling evaluation")
            return []
        
        decisions = []
        current_time = time.time()
        
        try:
            deployments = await self._get_deployment_status()
            
            for deployment_name, deployment_info in deployments.items():
                last_action_time = self.last_scaling_action.get(deployment_name, 0)
                if current_time - last_action_time < self.cooldown_period:
                    continue
                
                decision = await self._evaluate_deployment_scaling(
                    deployment_name, deployment_info, health_metrics
                )
                
                if decision:
                    decisions.append(decision)
                    self.last_scaling_action[deployment_name] = current_time
            
            self.scaling_history.extend(decisions)
            
            if len(self.scaling_history) > 1000:
                self.scaling_history = self.scaling_history[-1000:]
            
            return decisions
            
        except Exception as e:
            logger.error(f"Error evaluating scaling decisions: {e}")
            return []
    
    async def _get_deployment_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current status of all deployments in namespace"""
        deployments = {}
        
        try:
            deployment_list = self.k8s_apps_v1.list_namespaced_deployment(namespace=self.namespace)
            
            for deployment in deployment_list.items:
                deployments[deployment.metadata.name] = {
                    'current_replicas': deployment.status.replicas or 0,
                    'ready_replicas': deployment.status.ready_replicas or 0,
                    'available_replicas': deployment.status.available_replicas or 0,
                    'labels': deployment.metadata.labels or {},
                    'annotations': deployment.metadata.annotations or {}
                }
                
        except ApiException as e:
            logger.error(f"Error getting deployment status: {e}")
        
        return deployments
    
    async def _evaluate_deployment_scaling(
        self, 
        deployment_name: str, 
        deployment_info: Dict[str, Any], 
        health_metrics: Dict[str, Any]
    ) -> Optional[ScalingDecision]:
        """
        Evaluate scaling decision for a specific deployment
        """
        current_replicas = deployment_info['current_replicas']
        ready_replicas = deployment_info['ready_replicas']
        
        avg_execution_time = health_metrics.get('avg_execution_time_ms', 0)
        trades_per_second = health_metrics.get('trades_per_second', 0)
        system_utilization = health_metrics.get('system_utilization_percent', 0)
        p95_execution_time = health_metrics.get('p95_execution_time_ms', 0)
        
        if avg_execution_time > 100:  # >100ms execution time
            desired_replicas = min(current_replicas + 2, 20)  # Max 20 replicas
            return ScalingDecision(
                action="scale_up",
                target=deployment_name,
                current_replicas=current_replicas,
                desired_replicas=desired_replicas,
                reason=f"High execution time: {avg_execution_time:.1f}ms",
                urgency="high" if avg_execution_time > 200 else "medium",
                timestamp=time.time()
            )
        
        if trades_per_second < 1000 and current_replicas < 10:  # Low throughput
            desired_replicas = min(current_replicas + 1, 10)
            return ScalingDecision(
                action="scale_up",
                target=deployment_name,
                current_replicas=current_replicas,
                desired_replicas=desired_replicas,
                reason=f"Low throughput: {trades_per_second:.0f} trades/sec",
                urgency="medium",
                timestamp=time.time()
            )
        
        if system_utilization > 85 and ready_replicas == current_replicas:  # High utilization
            desired_replicas = min(current_replicas + 1, 15)
            return ScalingDecision(
                action="scale_up",
                target=deployment_name,
                current_replicas=current_replicas,
                desired_replicas=desired_replicas,
                reason=f"High system utilization: {system_utilization:.1f}%",
                urgency="high" if system_utilization > 95 else "medium",
                timestamp=time.time()
            )
        
        if (avg_execution_time < 30 and 
            trades_per_second > 5000 and 
            system_utilization < 40 and 
            current_replicas > 2):  # Don't scale below 2 replicas
            
            desired_replicas = max(current_replicas - 1, 2)
            return ScalingDecision(
                action="scale_down",
                target=deployment_name,
                current_replicas=current_replicas,
                desired_replicas=desired_replicas,
                reason="Low resource utilization with good performance",
                urgency="low",
                timestamp=time.time()
            )
        
        return None
    
    async def execute_scaling_decision(self, decision: ScalingDecision) -> bool:
        """
        Execute a scaling decision by updating the deployment
        """
        if not self.k8s_apps_v1:
            logger.warning("Kubernetes client not available - cannot execute scaling")
            return False
        
        try:
            deployment = self.k8s_apps_v1.read_namespaced_deployment(
                name=decision.target,
                namespace=self.namespace
            )
            
            deployment.spec.replicas = decision.desired_replicas
            
            if not deployment.metadata.annotations:
                deployment.metadata.annotations = {}
            
            deployment.metadata.annotations['autoscaler.quantroi.com/last-scaled'] = str(decision.timestamp)
            deployment.metadata.annotations['autoscaler.quantroi.com/reason'] = decision.reason
            deployment.metadata.annotations['autoscaler.quantroi.com/urgency'] = decision.urgency
            
            self.k8s_apps_v1.patch_namespaced_deployment(
                name=decision.target,
                namespace=self.namespace,
                body=deployment
            )
            
            logger.info(f"Scaled {decision.target} from {decision.current_replicas} to {decision.desired_replicas} replicas. Reason: {decision.reason}")
            return True
            
        except ApiException as e:
            logger.error(f"Error executing scaling decision for {decision.target}: {e}")
            return False
    
    def get_scaling_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent scaling history"""
        recent_history = self.scaling_history[-limit:] if self.scaling_history else []
        
        return [
            {
                'action': decision.action,
                'target': decision.target,
                'current_replicas': decision.current_replicas,
                'desired_replicas': decision.desired_replicas,
                'reason': decision.reason,
                'urgency': decision.urgency,
                'timestamp': decision.timestamp
            }
            for decision in recent_history
        ]
    
    def get_scaling_statistics(self) -> Dict[str, Any]:
        """Get scaling statistics and patterns"""
        if not self.scaling_history:
            return {'status': 'no_scaling_history'}
        
        total_decisions = len(self.scaling_history)
        scale_up_count = sum(1 for d in self.scaling_history if d.action == 'scale_up')
        scale_down_count = sum(1 for d in self.scaling_history if d.action == 'scale_down')
        
        recent_cutoff = time.time() - 3600
        recent_decisions = [d for d in self.scaling_history if d.timestamp > recent_cutoff]
        
        return {
            'total_scaling_decisions': total_decisions,
            'scale_up_count': scale_up_count,
            'scale_down_count': scale_down_count,
            'scale_up_percentage': (scale_up_count / total_decisions) * 100 if total_decisions > 0 else 0,
            'recent_decisions_last_hour': len(recent_decisions),
            'most_scaled_targets': self._get_most_scaled_targets(),
            'average_cooldown_respected': self._calculate_cooldown_compliance()
        }
    
    def _get_most_scaled_targets(self) -> List[Dict[str, Any]]:
        """Get deployments that are scaled most frequently"""
        target_counts = {}
        for decision in self.scaling_history:
            target_counts[decision.target] = target_counts.get(decision.target, 0) + 1
        
        sorted_targets = sorted(target_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'target': target, 'scaling_count': count} for target, count in sorted_targets[:5]]
    
    def _calculate_cooldown_compliance(self) -> float:
        """Calculate percentage of scaling decisions that respected cooldown period"""
        if len(self.scaling_history) < 2:
            return 100.0
        
        compliant_decisions = 0
        total_decisions = 0
        
        target_last_action = {}
        
        for decision in self.scaling_history:
            if decision.target in target_last_action:
                time_since_last = decision.timestamp - target_last_action[decision.target]
                if time_since_last >= self.cooldown_period:
                    compliant_decisions += 1
                total_decisions += 1
            
            target_last_action[decision.target] = decision.timestamp
        
        return (compliant_decisions / total_decisions) * 100 if total_decisions > 0 else 100.0

async def main():
    """Test the Kubernetes autoscaler"""
    autoscaler = KubernetesAutoscaler()
    
    test_metrics = {
        'avg_execution_time_ms': 150,  # High execution time
        'trades_per_second': 800,     # Low throughput
        'system_utilization_percent': 90,  # High utilization
        'p95_execution_time_ms': 250
    }
    
    decisions = await autoscaler.evaluate_scaling_decision(test_metrics)
    
    for decision in decisions:
        print(f"Scaling Decision: {decision}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

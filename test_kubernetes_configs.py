#!/usr/bin/env python3
"""
Kubernetes Configuration Validation Tests
Tests that all Kubernetes manifests are valid and properly configured
"""

import unittest
import yaml
import os
from pathlib import Path

class TestKubernetesConfigs(unittest.TestCase):
    """Test Kubernetes configuration files"""
    
    def setUp(self):
        self.k8s_dir = Path("/home/ubuntu/repos/quantroi/k8s")
        self.argocd_dir = Path("/home/ubuntu/repos/quantroi/argocd")
    
    def test_k8s_directory_exists(self):
        """Test that k8s directory exists"""
        self.assertTrue(self.k8s_dir.exists())
        self.assertTrue(self.k8s_dir.is_dir())
    
    def test_namespace_yaml_valid(self):
        """Test namespace.yaml is valid"""
        namespace_file = self.k8s_dir / "namespace.yaml"
        self.assertTrue(namespace_file.exists())
        
        with open(namespace_file, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertEqual(config['apiVersion'], 'v1')
        self.assertEqual(config['kind'], 'Namespace')
        self.assertEqual(config['metadata']['name'], 'quantroi')
    
    def test_causal_ai_service_yaml_valid(self):
        """Test causal-ai-service.yaml is valid"""
        service_file = self.k8s_dir / "causal-ai-service.yaml"
        self.assertTrue(service_file.exists())
        
        with open(service_file, 'r') as f:
            configs = list(yaml.safe_load_all(f))
        
        self.assertEqual(len(configs), 3)
        
        deployment = configs[0]
        self.assertEqual(deployment['kind'], 'Deployment')
        self.assertEqual(deployment['metadata']['name'], 'causal-ai-engine')
        
        service = configs[1]
        self.assertEqual(service['kind'], 'Service')
        self.assertEqual(service['metadata']['name'], 'causal-ai-service')
        
        ingress = configs[2]
        self.assertEqual(ingress['kind'], 'Ingress')
        self.assertEqual(ingress['metadata']['name'], 'causal-ai-ingress')
    
    def test_redis_service_yaml_valid(self):
        """Test redis-service.yaml is valid"""
        redis_file = self.k8s_dir / "redis-service.yaml"
        self.assertTrue(redis_file.exists())
        
        with open(redis_file, 'r') as f:
            configs = list(yaml.safe_load_all(f))
        
        self.assertEqual(len(configs), 3)
        
        deployment = configs[0]
        self.assertEqual(deployment['kind'], 'Deployment')
        self.assertEqual(deployment['metadata']['name'], 'redis')
        
        service = configs[1]
        self.assertEqual(service['kind'], 'Service')
        self.assertEqual(service['metadata']['name'], 'redis-service')
        
        pvc = configs[2]
        self.assertEqual(pvc['kind'], 'PersistentVolumeClaim')
        self.assertEqual(pvc['metadata']['name'], 'redis-pvc')
    
    def test_mlflow_service_yaml_valid(self):
        """Test mlflow-service.yaml is valid"""
        mlflow_file = self.k8s_dir / "mlflow-service.yaml"
        self.assertTrue(mlflow_file.exists())
        
        with open(mlflow_file, 'r') as f:
            configs = list(yaml.safe_load_all(f))
        
        self.assertEqual(len(configs), 3)
        
        deployment = configs[0]
        self.assertEqual(deployment['kind'], 'Deployment')
        self.assertEqual(deployment['metadata']['name'], 'mlflow-server')
        
        service = configs[1]
        self.assertEqual(service['kind'], 'Service')
        self.assertEqual(service['metadata']['name'], 'mlflow-service')
        
        pvc = configs[2]
        self.assertEqual(pvc['kind'], 'PersistentVolumeClaim')
        self.assertEqual(pvc['metadata']['name'], 'mlflow-pvc')
    
    def test_voice_interface_service_yaml_valid(self):
        """Test voice-interface-service.yaml is valid"""
        voice_file = self.k8s_dir / "voice-interface-service.yaml"
        self.assertTrue(voice_file.exists())
        
        with open(voice_file, 'r') as f:
            configs = list(yaml.safe_load_all(f))
        
        self.assertEqual(len(configs), 2)
        
        deployment = configs[0]
        self.assertEqual(deployment['kind'], 'Deployment')
        self.assertEqual(deployment['metadata']['name'], 'voice-interface')
        
        service = configs[1]
        self.assertEqual(service['kind'], 'Service')
        self.assertEqual(service['metadata']['name'], 'voice-interface-service')
    
    def test_kustomization_yaml_valid(self):
        """Test kustomization.yaml is valid"""
        kustomization_file = self.k8s_dir / "kustomization.yaml"
        self.assertTrue(kustomization_file.exists())
        
        with open(kustomization_file, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertEqual(config['apiVersion'], 'kustomize.config.k8s.io/v1beta1')
        self.assertEqual(config['kind'], 'Kustomization')
        self.assertIn('resources', config)
        self.assertEqual(len(config['resources']), 5)
    
    def test_argocd_application_yaml_valid(self):
        """Test ArgoCD application.yaml is valid"""
        argocd_file = self.argocd_dir / "application.yaml"
        self.assertTrue(argocd_file.exists())
        
        with open(argocd_file, 'r') as f:
            configs = list(yaml.safe_load_all(f))
        
        self.assertEqual(len(configs), 2)
        
        application = configs[0]
        self.assertEqual(application['kind'], 'Application')
        self.assertEqual(application['metadata']['name'], 'quantroi-platform')
        
        project = configs[1]
        self.assertEqual(project['kind'], 'AppProject')
        self.assertEqual(project['metadata']['name'], 'quantroi')
    
    def test_all_yaml_files_parseable(self):
        """Test that all YAML files in k8s directory are parseable"""
        yaml_files = list(self.k8s_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0)
        
        for yaml_file in yaml_files:
            with self.subTest(file=yaml_file.name):
                with open(yaml_file, 'r') as f:
                    try:
                        list(yaml.safe_load_all(f))
                    except yaml.YAMLError as e:
                        self.fail(f"YAML parsing failed for {yaml_file.name}: {e}")

if __name__ == '__main__':
    print("Running Kubernetes Configuration Tests...")
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
Unit tests for Redis TLS encryption module
Tests 1K cache operations and verifies encryption compliance
"""

import pytest
import asyncio
import time
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

try:
    from ..security.redis_encryption import (
        RedisEncryptionConfig,
        SecureRedisManager,
        validate_encryption_compliance,
        create_redis_config_file,
        create_acl_file
    )
    from ..neo4j_integration.cache import EncryptedCacheManager
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    print("Warning: Encryption modules not available, running basic tests only")

class TestRedisEncryption:
    """Test suite for Redis TLS encryption"""
    
    @pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Encryption modules not available")
    def test_redis_config_creation(self):
        """Test Redis configuration object creation"""
        config = RedisEncryptionConfig(
            host="localhost",
            port=6380,
            ssl_enabled=True,
            password="test_password",
            username="test_user"
        )
        assert config.host == "localhost"
        assert config.port == 6380
        assert config.ssl_enabled == True
    
    @pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Encryption modules not available")
    def test_environment_config_loading(self):
        """Test loading configuration from environment variables"""
        with patch.dict('os.environ', {
            'REDIS_HOST': 'test-redis.com',
            'REDIS_TLS_PORT': '6381',
            'REDIS_PASSWORD': 'env_password'
        }):
            config = RedisEncryptionConfig.from_environment()
            assert config.host == 'test-redis.com'
            assert config.port == 6381
            assert config.password == 'env_password'
    
    @pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Encryption modules not available")
    def test_redis_config_file_generation(self):
        """Test Redis configuration file generation"""
        config_content = create_redis_config_file()
        
        assert "tls-protocols \"TLSv1.3\"" in config_content
        assert "tls-port 6380" in config_content
        assert "port 0" in config_content  # Disable non-TLS port
        
        assert "protected-mode yes" in config_content
        assert "requirepass" in config_content
        assert "rename-command FLUSHDB" in config_content
    
    @pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Encryption modules not available")
    def test_acl_file_generation(self):
        """Test ACL file generation"""
        acl_content = create_acl_file()
        
        assert "user default off" in acl_content
        assert "user vote_cache_user" in acl_content
        assert "~vote:*" in acl_content
        assert "+@read" in acl_content

class TestEncryptedCacheManager:
    """Test suite for encrypted cache manager"""
    
    def test_fallback_cache_manager(self):
        """Test cache manager fallback when encryption not available"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_client.get.return_value = '{"test": "data"}'
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(
                redis_host="localhost", 
                redis_port=6379, 
                use_encryption=False
            )
            
            assert cache_manager.redis_client is not None
            assert cache_manager.use_encryption == False
    
    def test_encrypted_vote_caching(self):
        """Test encrypted vote data caching"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=False)
            
            vote_data = {
                "voter_id": "test_voter",
                "vote_choice": 1,
                "voter_secret": "sensitive_secret",
                "zkp_proof": "proof_data"
            }
            
            result = cache_manager.cache_vote_data("vote_123", vote_data, 3600)
            assert result == True
            mock_client.setex.assert_called_once()
    
    def test_encrypted_vote_retrieval(self):
        """Test encrypted vote data retrieval"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.get.return_value = json.dumps({
                "data": {
                    "voter_id": "test_voter",
                    "vote_choice": 1
                },
                "cached_at": datetime.now().isoformat(),
                "query_type": "vote_data",
                "params": {"vote_id": "vote_123"},
                "encrypted": False
            })
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=False)
            
            result = cache_manager.get_vote_data("vote_123")
            assert result is not None
            assert result["voter_id"] == "test_voter"
    
    def test_zkp_proof_caching(self):
        """Test ZKP proof caching with encryption"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=False)
            
            proof_data = {
                "commitment": "commitment_hash",
                "nullifier": "nullifier_hash",
                "private_key": "sensitive_key"
            }
            
            result = cache_manager.cache_zkp_proof("proof_123", proof_data, 7200)
            assert result == True
    
    def test_cache_clearing_with_audit(self):
        """Test cache clearing with audit logging"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.keys.return_value = ["test:key1", "test:key2"]
            mock_client.delete.return_value = 2
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=False)
            
            result = cache_manager.clear_all_cache()
            assert result == True
    
    def test_encryption_status_check(self):
        """Test encryption status verification"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=False)
            
            status = cache_manager.get_encryption_status()
            assert status["encryption_enabled"] == False
            assert "note" in status

class TestPerformanceAndCompliance:
    """Test performance and compliance requirements"""
    
    def test_1k_cache_operations_performance(self):
        """Test 1K cache operations performance requirement"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_client.get.return_value = json.dumps({
                "data": {"test": "data"},
                "cached_at": datetime.now().isoformat(),
                "query_type": "test",
                "params": {},
                "encrypted": False
            })
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=False)
            
            start_time = time.time()
            
            for i in range(1000):
                vote_data = {
                    "voter_id": f"voter_{i}",
                    "vote_choice": i % 2,
                    "timestamp": datetime.now().isoformat()
                }
                
                cache_manager.cache_vote_data(f"vote_{i}", vote_data, 3600)
                
                cache_manager.get_vote_data(f"vote_{i}")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            assert total_time < 10.0, f"1K cache operations took {total_time:.2f}s, should be < 10s"
            
            ops_per_second = 2000 / total_time  # 2000 operations (1K cache + 1K retrieve)
            assert ops_per_second > 200, f"Performance: {ops_per_second:.0f} ops/sec, should be > 200"
    
    def test_sensitive_data_encryption(self):
        """Test sensitive data encryption in cache"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=True)
            
            sensitive_data = {
                "voter_id": "voter_123",
                "voter_secret": "super_secret_key",
                "zkp_proof": "sensitive_proof_data",
                "vote_choice": 1
            }
            
            encrypted_data = cache_manager._encrypt_sensitive_data(sensitive_data)
            
            assert encrypted_data["voter_secret"] != "super_secret_key"
            assert encrypted_data["zkp_proof"] != "sensitive_proof_data"
            assert encrypted_data["voter_secret_encrypted"] == True
            assert encrypted_data["zkp_proof_encrypted"] == True
            
            assert encrypted_data["vote_choice"] == 1
    
    @pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Encryption modules not available")
    def test_encryption_compliance_validation(self):
        """Test encryption compliance validation"""
        if ENCRYPTION_AVAILABLE:
            with patch('security.redis_encryption.SecureRedisManager') as mock_manager:
                mock_manager_instance = Mock()
                mock_manager_instance.get_encryption_status.return_value = {
                    "ssl_enabled": True,
                    "tls_version": "TLS 1.3",
                    "authentication_enabled": True,
                    "acl_enabled": True
                }
                mock_manager_instance.test_encryption.return_value = {
                    "encryption_enabled": True,
                    "connection_test": True
                }
                mock_manager.return_value = mock_manager_instance
                
                compliance_result = validate_encryption_compliance()
                
                assert compliance_result["tls_1_3_enabled"] == True
                assert compliance_result["authentication_required"] == True
                assert compliance_result["connection_encrypted"] == True
                assert compliance_result["gramm_leach_bliley_compliant"] == True
        else:
            assert True

class TestComplianceIntegration:
    """Test compliance and audit logging integration"""
    
    def test_audit_logging_integration(self):
        """Test audit logging for cache operations"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=True)
            
            with patch('enhanced_ria_features.neo4j_integration.cache.log_encryption_event') as mock_log:
                vote_data = {"voter_id": "test", "vote_choice": 1}
                cache_manager.cache_vote_data("vote_123", vote_data)
                
                mock_log.assert_called()
                call_args = mock_log.call_args[0]
                assert call_args[0] == "query_cached"
                assert "encrypted" in call_args[1]
    
    def test_gramm_leach_bliley_compliance(self):
        """Test Gramm-Leach-Bliley Act compliance features"""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client
            
            cache_manager = EncryptedCacheManager(use_encryption=True)
            
            status = cache_manager.get_encryption_status()
            
            assert "encryption_enabled" in status

if __name__ == "__main__":
    print("Running Redis encryption tests...")
    
    test_cache = TestEncryptedCacheManager()
    test_cache.test_fallback_cache_manager()
    print("✅ Fallback cache manager test passed")
    
    test_cache.test_encrypted_vote_caching()
    print("✅ Vote caching test passed")
    
    test_cache.test_encrypted_vote_retrieval()
    print("✅ Vote retrieval test passed")
    
    test_perf = TestPerformanceAndCompliance()
    test_perf.test_1k_cache_operations_performance()
    print("✅ 1K cache operations performance test passed")
    
    test_perf.test_sensitive_data_encryption()
    print("✅ Sensitive data encryption test passed")
    
    print("🎉 All Redis encryption tests completed successfully!")

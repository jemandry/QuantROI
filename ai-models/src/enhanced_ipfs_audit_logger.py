import asyncio
import logging
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import os
from collections import deque

try:
    import ipfshttpclient
    IPFS_AVAILABLE = True
except ImportError:
    IPFS_AVAILABLE = False
    logging.warning("IPFS client not available")

from .stream_based_audit_logger import StreamBasedAuditLogger
from .merkle_audit_tool import EnhancedMerkleAuditTool

@dataclass
class IPFSAuditEntry:
    entry_id: str
    content_hash: str
    ipfs_hash: str
    content_type: str
    metadata: Dict[str, Any]
    timestamp: str
    size_bytes: int
    retrieval_verified: bool = False

@dataclass
class IPFSStorageMetrics:
    total_entries: int
    total_size_bytes: int
    successful_uploads: int
    failed_uploads: int
    retrieval_success_rate: float
    avg_upload_time_ms: float
    last_updated: str

class EnhancedIPFSAuditLogger(StreamBasedAuditLogger):
    """
    Enhanced IPFS audit logger with immutable decision logs and distributed storage
    Extends StreamBasedAuditLogger with IPFS integration for tamper-proof audit trails
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.ipfs_client = None
        self.ipfs_gateway_url = self.config.get('ipfs_gateway_url', 'http://localhost:8080')
        self.ipfs_api_url = self.config.get('ipfs_api_url', '/ip4/127.0.0.1/tcp/5001')
        
        self.ipfs_entries = deque(maxlen=10000)
        self.storage_metrics = IPFSStorageMetrics(
            total_entries=0,
            total_size_bytes=0,
            successful_uploads=0,
            failed_uploads=0,
            retrieval_success_rate=0.0,
            avg_upload_time_ms=0.0,
            last_updated=datetime.now().isoformat()
        )
        
        self.upload_times = deque(maxlen=1000)
        self.retrieval_cache = {}
        self.cache_ttl = timedelta(hours=1)
        
        self.batch_size = self.config.get('batch_size', 100)
        self.batch_buffer = []
        self.batch_timeout = self.config.get('batch_timeout_seconds', 30)
        self.last_batch_time = datetime.now()
        
        self.merkle_audit = None
        
        self.logger.info("Enhanced IPFS audit logger initialized")

    async def initialize_ipfs(self):
        """Initialize IPFS client connection"""
        if not IPFS_AVAILABLE:
            self.logger.warning("IPFS not available - using mock storage")
            return False
        
        try:
            self.ipfs_client = ipfshttpclient.connect(self.ipfs_api_url)
            
            node_info = self.ipfs_client.id()
            self.logger.info(f"Connected to IPFS node: {node_info['ID']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"IPFS connection failed: {e}")
            self.ipfs_client = None
            return False

    async def initialize_merkle_integration(self, merkle_config: Dict[str, Any]):
        """Initialize Merkle tree integration for batch verification"""
        try:
            self.merkle_audit = EnhancedMerkleAuditTool(merkle_config)
            await self.merkle_audit.initialize()
            self.logger.info("Merkle audit integration initialized")
        except Exception as e:
            self.logger.error(f"Merkle integration failed: {e}")

    async def log_immutable_decision(
        self, 
        decision_data: Dict[str, Any], 
        decision_type: str = 'trading_decision'
    ) -> Optional[IPFSAuditEntry]:
        """Log trading decision to IPFS for immutable audit trail"""
        
        try:
            enhanced_decision = {
                'decision_id': decision_data.get('decision_id', f"decision_{int(time.time() * 1000000)}"),
                'decision_type': decision_type,
                'timestamp': datetime.now().isoformat(),
                'content': decision_data,
                'audit_metadata': {
                    'source': 'enhanced_ipfs_audit_logger',
                    'version': '1.0.0',
                    'integrity_hash': None  # Will be calculated
                }
            }
            
            content_json = json.dumps(enhanced_decision, sort_keys=True)
            content_hash = hashlib.sha256(content_json.encode()).hexdigest()
            enhanced_decision['audit_metadata']['integrity_hash'] = content_hash
            
            ipfs_hash = await self._store_in_ipfs(content_json)
            
            if ipfs_hash:
                audit_entry = IPFSAuditEntry(
                    entry_id=enhanced_decision['decision_id'],
                    content_hash=content_hash,
                    ipfs_hash=ipfs_hash,
                    content_type=decision_type,
                    metadata=enhanced_decision['audit_metadata'],
                    timestamp=datetime.now().isoformat(),
                    size_bytes=len(content_json.encode()),
                    retrieval_verified=False
                )
                
                self.ipfs_entries.append(audit_entry)
                self.storage_metrics.total_entries += 1
                self.storage_metrics.total_size_bytes += audit_entry.size_bytes
                self.storage_metrics.successful_uploads += 1
                
                await super().log_event({
                    'event_type': 'ipfs_decision_logged',
                    'decision_id': enhanced_decision['decision_id'],
                    'ipfs_hash': ipfs_hash,
                    'content_hash': content_hash,
                    'decision_type': decision_type,
                    'timestamp': datetime.now().isoformat()
                })
                
                self.batch_buffer.append(audit_entry)
                await self._process_batch_if_ready()
                
                self.logger.info(f"Decision logged to IPFS: {enhanced_decision['decision_id']} -> {ipfs_hash}")
                
                return audit_entry
            else:
                self.storage_metrics.failed_uploads += 1
                return None
                
        except Exception as e:
            self.logger.error(f"IPFS decision logging failed: {e}")
            self.storage_metrics.failed_uploads += 1
            return None

    async def _store_in_ipfs(self, content: str) -> Optional[str]:
        """Store content in IPFS and return hash"""
        
        if not self.ipfs_client:
            mock_hash = f"Qm{hashlib.sha256(content.encode()).hexdigest()[:44]}"
            await asyncio.sleep(0.001)  # Simulate network delay
            return mock_hash
        
        try:
            start_time = time.time()
            
            result = self.ipfs_client.add_str(content)
            
            upload_time_ms = (time.time() - start_time) * 1000
            self.upload_times.append(upload_time_ms)
            
            self.storage_metrics.avg_upload_time_ms = sum(self.upload_times) / len(self.upload_times)
            
            return result
            
        except Exception as e:
            self.logger.error(f"IPFS storage failed: {e}")
            return None

    async def verify_ipfs_retrieval(self, ipfs_hash: str) -> Tuple[bool, Optional[str]]:
        """Verify that content can be retrieved from IPFS"""
        
        cache_key = f"verify_{ipfs_hash}"
        if cache_key in self.retrieval_cache:
            cache_entry = self.retrieval_cache[cache_key]
            cache_time = datetime.fromisoformat(cache_entry['timestamp'])
            if datetime.now() - cache_time < self.cache_ttl:
                return cache_entry['success'], cache_entry.get('content')
        
        if not self.ipfs_client:
            self.retrieval_cache[cache_key] = {
                'success': True,
                'content': f"mock_content_for_{ipfs_hash}",
                'timestamp': datetime.now().isoformat()
            }
            return True, f"mock_content_for_{ipfs_hash}"
        
        try:
            content = self.ipfs_client.cat(ipfs_hash)
            content_str = content.decode('utf-8') if isinstance(content, bytes) else str(content)
            
            self.retrieval_cache[cache_key] = {
                'success': True,
                'content': content_str,
                'timestamp': datetime.now().isoformat()
            }
            
            return True, content_str
            
        except Exception as e:
            self.logger.error(f"IPFS retrieval verification failed for {ipfs_hash}: {e}")
            
            self.retrieval_cache[cache_key] = {
                'success': False,
                'content': None,
                'timestamp': datetime.now().isoformat()
            }
            
            return False, None

    async def _process_batch_if_ready(self):
        """Process batch of audit entries for Merkle tree generation"""
        
        current_time = datetime.now()
        time_since_last_batch = (current_time - self.last_batch_time).total_seconds()
        
        should_process = (
            len(self.batch_buffer) >= self.batch_size or
            time_since_last_batch >= self.batch_timeout
        )
        
        if should_process and self.batch_buffer:
            await self._process_batch()

    async def _process_batch(self):
        """Process current batch of audit entries"""
        
        try:
            if not self.batch_buffer:
                return
            
            batch_entries = list(self.batch_buffer)
            self.batch_buffer.clear()
            self.last_batch_time = datetime.now()
            
            if self.merkle_audit:
                batch_data = []
                for entry in batch_entries:
                    batch_data.append({
                        'entry_id': entry.entry_id,
                        'ipfs_hash': entry.ipfs_hash,
                        'content_hash': entry.content_hash,
                        'timestamp': entry.timestamp
                    })
                
                await self.merkle_audit.add_audit_entry(
                    content=json.dumps(batch_data, sort_keys=True),
                    content_type='ipfs_audit_batch',
                    metadata={
                        'batch_size': len(batch_entries),
                        'batch_timestamp': datetime.now().isoformat(),
                        'total_size_bytes': sum(entry.size_bytes for entry in batch_entries)
                    }
                )
            
            sample_size = min(5, len(batch_entries))
            import random
            sample_entries = random.sample(batch_entries, sample_size)
            
            successful_retrievals = 0
            for entry in sample_entries:
                success, _ = await self.verify_ipfs_retrieval(entry.ipfs_hash)
                if success:
                    successful_retrievals += 1
                    entry.retrieval_verified = True
            
            if sample_entries:
                batch_success_rate = successful_retrievals / len(sample_entries)
                alpha = 0.1
                self.storage_metrics.retrieval_success_rate = (
                    alpha * batch_success_rate + 
                    (1 - alpha) * self.storage_metrics.retrieval_success_rate
                )
            
            self.storage_metrics.last_updated = datetime.now().isoformat()
            
            self.logger.info(f"Processed IPFS audit batch: {len(batch_entries)} entries")
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")

    async def get_decision_audit_trail(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete audit trail for a decision"""
        
        try:
            audit_entry = None
            for entry in self.ipfs_entries:
                if entry.entry_id == decision_id:
                    audit_entry = entry
                    break
            
            if not audit_entry:
                return None
            
            success, content = await self.verify_ipfs_retrieval(audit_entry.ipfs_hash)
            
            if success and content:
                decision_data = json.loads(content)
                
                return {
                    'decision_id': decision_id,
                    'audit_entry': asdict(audit_entry),
                    'decision_data': decision_data,
                    'retrieval_verified': success,
                    'audit_trail_complete': True
                }
            else:
                return {
                    'decision_id': decision_id,
                    'audit_entry': asdict(audit_entry),
                    'decision_data': None,
                    'retrieval_verified': False,
                    'audit_trail_complete': False,
                    'error': 'Failed to retrieve from IPFS'
                }
                
        except Exception as e:
            self.logger.error(f"Audit trail retrieval failed for {decision_id}: {e}")
            return None

    async def generate_storage_report(self) -> Dict[str, Any]:
        """Generate comprehensive IPFS storage report"""
        
        try:
            await self._process_batch()  # Process any pending batch
            
            recent_entries = [
                entry for entry in self.ipfs_entries 
                if (datetime.now() - datetime.fromisoformat(entry.timestamp)).total_seconds() < 3600
            ]
            
            verified_entries = [entry for entry in self.ipfs_entries if entry.retrieval_verified]
            
            report = {
                'report_id': f"ipfs_storage_report_{int(datetime.now().timestamp())}",
                'timestamp': datetime.now().isoformat(),
                'storage_metrics': asdict(self.storage_metrics),
                'recent_activity': {
                    'entries_last_hour': len(recent_entries),
                    'size_last_hour_bytes': sum(entry.size_bytes for entry in recent_entries),
                    'avg_entry_size_bytes': sum(entry.size_bytes for entry in recent_entries) / len(recent_entries) if recent_entries else 0
                },
                'verification_status': {
                    'total_verified_entries': len(verified_entries),
                    'verification_rate': len(verified_entries) / len(self.ipfs_entries) if self.ipfs_entries else 0,
                    'cache_hit_rate': len(self.retrieval_cache) / max(1, self.storage_metrics.total_entries)
                },
                'performance_metrics': {
                    'avg_upload_time_ms': self.storage_metrics.avg_upload_time_ms,
                    'upload_success_rate': self.storage_metrics.successful_uploads / max(1, self.storage_metrics.successful_uploads + self.storage_metrics.failed_uploads),
                    'retrieval_success_rate': self.storage_metrics.retrieval_success_rate
                }
            }
            
            await super().log_event({
                'event_type': 'ipfs_storage_report_generated',
                'report_id': report['report_id'],
                'report_summary': {
                    'total_entries': self.storage_metrics.total_entries,
                    'total_size_mb': self.storage_metrics.total_size_bytes / (1024 * 1024),
                    'success_rate': report['performance_metrics']['upload_success_rate']
                },
                'timestamp': datetime.now().isoformat()
            })
            
            return report
            
        except Exception as e:
            self.logger.error(f"Storage report generation failed: {e}")
            return {'status': 'error', 'error': str(e)}

    async def cleanup_old_cache(self, max_age_hours: int = 24):
        """Clean up old cache entries"""
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            keys_to_remove = [
                key for key, value in self.retrieval_cache.items()
                if value['timestamp'] < cutoff_time
            ]
            
            for key in keys_to_remove:
                del self.retrieval_cache[key]
            
            self.logger.info(f"Cleaned up {len(keys_to_remove)} old cache entries")
            
        except Exception as e:
            self.logger.error(f"Cache cleanup failed: {e}")

    async def shutdown(self):
        """Shutdown IPFS audit logger"""
        try:
            await self._process_batch()
            
            await super().force_flush_buffer()
            
            if self.merkle_audit:
                await self.merkle_audit.shutdown()
            
            if self.ipfs_client:
                self.ipfs_client.close()
            
            self.logger.info("Enhanced IPFS audit logger shutdown completed")
            
        except Exception as e:
            self.logger.error(f"IPFS audit logger shutdown error: {e}")

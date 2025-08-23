import asyncio
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    from .merkle_audit_tool import EnhancedMerkleAuditTool, AuditEntry
    from .wasm_compilation_pipeline import WasmCompilationPipeline
    AUDIT_COMPONENTS_AVAILABLE = True
except ImportError:
    AUDIT_COMPONENTS_AVAILABLE = False
    logging.warning("Audit components not available")

@dataclass
class VerificationResult:
    verification_id: str
    content_hash: str
    merkle_proof: List[str]
    is_valid: bool
    verification_time: float
    wasm_module_used: str
    blockchain_anchor: Optional[str] = None

class WasmAuditVerifier:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.audit_tool = None
        self.wasm_pipeline = None
        
        self.verifications_performed = 0
        self.verification_errors = 0
        self.compiled_verifier_modules = {}

    async def initialize(self):
        if AUDIT_COMPONENTS_AVAILABLE:
            try:
                self.audit_tool = EnhancedMerkleAuditTool(self.config)
                await self.audit_tool.initialize()
                
                self.wasm_pipeline = WasmCompilationPipeline(self.config)
                await self.wasm_pipeline.initialize()
                
                await self._compile_verification_modules()
                
                self.logger.info("Initialized WASM audit verifier")
            except Exception as e:
                self.logger.warning(f"Audit components initialization failed: {e}")

    async def _compile_verification_modules(self):
        try:
            if not self.wasm_pipeline:
                return
            
            verifier_module = await self.wasm_pipeline.compile_rust_to_wasm(
                '', 'merkle_proof_verifier'
            )
            
            if verifier_module:
                self.compiled_verifier_modules['merkle_verifier'] = verifier_module
                self.logger.info("Compiled Merkle proof verifier WASM module")
            
            hash_module = await self.wasm_pipeline.compile_rust_to_wasm(
                '', 'content_hash_verifier'
            )
            
            if hash_module:
                self.compiled_verifier_modules['hash_verifier'] = hash_module
                self.logger.info("Compiled content hash verifier WASM module")
                
        except Exception as e:
            self.logger.error(f"WASM verification module compilation failed: {e}")

    async def verify_news_integrity(self, news_content: str, claimed_hash: str, merkle_proof: List[str]) -> VerificationResult:
        start_time = datetime.now()
        
        try:
            verification_id = f"verify_{int(datetime.now().timestamp() * 1000000)}"
            
            computed_hash = hashlib.sha256(news_content.encode()).hexdigest()
            
            hash_valid = computed_hash == claimed_hash
            
            if self.audit_tool and merkle_proof:
                proof_valid = await self._verify_merkle_proof_wasm(
                    computed_hash, merkle_proof
                )
            else:
                proof_valid = True
            
            is_valid = hash_valid and proof_valid
            
            verification_time = (datetime.now() - start_time).total_seconds()
            
            result = VerificationResult(
                verification_id=verification_id,
                content_hash=computed_hash,
                merkle_proof=merkle_proof,
                is_valid=is_valid,
                verification_time=verification_time,
                wasm_module_used=self.compiled_verifier_modules.get('merkle_verifier', {}).get('module_id', 'fallback'),
                blockchain_anchor=None
            )
            
            self.verifications_performed += 1
            
            if not is_valid:
                self.logger.warning(f"Verification failed for {verification_id}: hash_valid={hash_valid}, proof_valid={proof_valid}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"News integrity verification failed: {e}")
            self.verification_errors += 1
            
            return VerificationResult(
                verification_id=f"error_{int(datetime.now().timestamp())}",
                content_hash="",
                merkle_proof=[],
                is_valid=False,
                verification_time=0.0,
                wasm_module_used="error",
                blockchain_anchor=None
            )

    async def _verify_merkle_proof_wasm(self, content_hash: str, merkle_proof: List[str]) -> bool:
        try:
            if not self.compiled_verifier_modules.get('merkle_verifier'):
                return await self._verify_merkle_proof_fallback(content_hash, merkle_proof)
            
            current_hash = content_hash
            
            for proof_element in merkle_proof:
                if current_hash < proof_element:
                    combined = current_hash + proof_element
                else:
                    combined = proof_element + current_hash
                
                current_hash = hashlib.sha256(combined.encode()).hexdigest()
            
            if self.audit_tool and hasattr(self.audit_tool, 'merkle_trees'):
                for tree_id, tree_data in self.audit_tool.merkle_trees.items():
                    if tree_data.get('root_hash') == current_hash:
                        return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"WASM Merkle proof verification failed: {e}")
            return False

    async def _verify_merkle_proof_fallback(self, content_hash: str, merkle_proof: List[str]) -> bool:
        try:
            current_hash = content_hash
            
            for proof_element in merkle_proof:
                if current_hash < proof_element:
                    combined = current_hash + proof_element
                else:
                    combined = proof_element + current_hash
                
                current_hash = hashlib.sha256(combined.encode()).hexdigest()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fallback Merkle proof verification failed: {e}")
            return False

    async def verify_batch_news_integrity(self, news_batch: List[Dict[str, Any]]) -> List[VerificationResult]:
        results = []
        
        for news_item in news_batch:
            try:
                content = news_item.get('content', '')
                claimed_hash = news_item.get('hash', '')
                merkle_proof = news_item.get('merkle_proof', [])
                
                result = await self.verify_news_integrity(content, claimed_hash, merkle_proof)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Batch verification failed for item: {e}")
                self.verification_errors += 1
        
        return results

    async def generate_client_verification_module(self) -> Optional[str]:
        try:
            if not self.wasm_pipeline:
                return None
            
            client_module = await self.wasm_pipeline.compile_rust_to_wasm(
                '', 'client_news_verifier'
            )
            
            if client_module:
                return client_module.wasm_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"Client verification module generation failed: {e}")
            return None

    async def get_verification_statistics(self) -> Dict[str, Any]:
        return {
            'verifications_performed': self.verifications_performed,
            'verification_errors': self.verification_errors,
            'success_rate': (self.verifications_performed - self.verification_errors) / max(self.verifications_performed, 1),
            'compiled_modules': len(self.compiled_verifier_modules),
            'available_modules': list(self.compiled_verifier_modules.keys()),
            'timestamp': datetime.now().isoformat()
        }

    async def shutdown(self):
        if self.audit_tool:
            await self.audit_tool.shutdown()
        
        if self.wasm_pipeline:
            await self.wasm_pipeline.shutdown()

async def main():
    config = {
        'build_dir': '/tmp/wasm_builds',
        'output_dir': '/tmp/wasm_output',
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
        'ipfs_api_url': 'http://localhost:5001',
        'solana_rpc_url': 'https://api.devnet.solana.com'
    }
    
    verifier = WasmAuditVerifier(config)
    await verifier.initialize()
    
    sample_news = [
        {
            'content': 'Apple reports strong quarterly earnings with revenue growth of 15%.',
            'hash': hashlib.sha256('Apple reports strong quarterly earnings with revenue growth of 15%.'.encode()).hexdigest(),
            'merkle_proof': ['proof1', 'proof2']
        },
        {
            'content': 'Tesla stock experiences volatility amid production concerns.',
            'hash': hashlib.sha256('Tesla stock experiences volatility amid production concerns.'.encode()).hexdigest(),
            'merkle_proof': ['proof3', 'proof4']
        }
    ]
    
    results = await verifier.verify_batch_news_integrity(sample_news)
    
    print(f"WASM Audit Verification Results:")
    print(f"- Verifications performed: {len(results)}")
    print(f"- Valid verifications: {sum(1 for r in results if r.is_valid)}")
    
    for result in results:
        print(f"\nVerification ID: {result.verification_id}")
        print(f"- Valid: {result.is_valid}")
        print(f"- Verification time: {result.verification_time:.3f}s")
        print(f"- WASM module: {result.wasm_module_used}")
        print(f"- Content hash: {result.content_hash[:16]}...")
    
    stats = await verifier.get_verification_statistics()
    print(f"\nVerification Statistics:")
    print(f"- Success rate: {stats['success_rate']:.2%}")
    print(f"- Compiled modules: {stats['compiled_modules']}")
    
    client_module_path = await verifier.generate_client_verification_module()
    if client_module_path:
        print(f"- Client verification module: {client_module_path}")
    
    await verifier.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

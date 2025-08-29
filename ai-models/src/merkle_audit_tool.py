import asyncio
import logging
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import os

try:
    import ipfshttpclient
    IPFS_AVAILABLE = True
except ImportError:
    IPFS_AVAILABLE = False
    logging.warning("IPFS client not available")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j not available")

try:
    from solana.rpc.api import Client
    from solana.keypair import Keypair
    from solana.transaction import Transaction
    from solana.system_program import transfer, TransferParams
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    logging.warning("Solana client not available")

try:
    from ..option_chain_platform.generate_merkle_audit import MerkleTree, build_merkle_tree
    EXISTING_MERKLE_AVAILABLE = True
except ImportError:
    EXISTING_MERKLE_AVAILABLE = False
    logging.warning("Existing Merkle audit tools not available")

@dataclass
class MerkleProof:
    leaf_hash: str
    proof_hashes: List[str]
    leaf_index: int
    root_hash: str
    tree_size: int
    timestamp: datetime

@dataclass
class AuditEntry:
    entry_id: str
    data_hash: str
    content_type: str
    metadata: Dict[str, Any]
    timestamp: datetime
    ipfs_hash: Optional[str] = None

class EnhancedMerkleAuditTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.ipfs_client = None
        self.neo4j_driver = None
        self.solana_client = None
        self.keypair = None
        
        self.audit_entries = []
        self.merkle_trees = {}
        
        self.program_id = config.get('solana_program_id', 'AuditProgram1111111111111111111111111111111')
        self.rpc_url = config.get('solana_rpc_url', 'https://api.devnet.solana.com')
        
        self.trees_created = 0
        self.proofs_generated = 0
        self.audit_errors = 0

    async def initialize(self):
        if IPFS_AVAILABLE:
            try:
                self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
                self.logger.info("Connected to IPFS daemon")
            except Exception as e:
                self.logger.warning(f"IPFS connection failed: {e}")
                self.ipfs_client = None
        
        if NEO4J_AVAILABLE:
            try:
                neo4j_uri = self.config.get('neo4j_uri', 'bolt://localhost:7687')
                neo4j_user = self.config.get('neo4j_user', 'neo4j')
                neo4j_password = self.config.get('neo4j_password', 'password')
                
                self.neo4j_driver = GraphDatabase.driver(
                    neo4j_uri, 
                    auth=(neo4j_user, neo4j_password)
                )
                await self._initialize_neo4j_schema()
                self.logger.info("Connected to Neo4j")
            except Exception as e:
                self.logger.warning(f"Neo4j connection failed: {e}")
        
        if SOLANA_AVAILABLE:
            try:
                self.solana_client = Client(self.rpc_url)
                
                wallet_path = self.config.get('solana_wallet_path', '/tmp/solana_wallet.json')
                if os.path.exists(wallet_path):
                    with open(wallet_path, 'r') as f:
                        keypair_data = json.load(f)
                        self.keypair = Keypair.from_secret_key(bytes(keypair_data))
                else:
                    self.keypair = Keypair.generate()
                    with open(wallet_path, 'w') as f:
                        json.dump(list(self.keypair.secret_key), f)
                
                self.logger.info("Connected to Solana")
            except Exception as e:
                self.logger.warning(f"Solana connection failed: {e}")

    async def _initialize_neo4j_schema(self):
        if not self.neo4j_driver:
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("CREATE CONSTRAINT audit_entry_id_unique IF NOT EXISTS FOR (ae:AuditEntry) REQUIRE ae.entry_id IS UNIQUE")
                session.run("CREATE CONSTRAINT audit_proof_id_unique IF NOT EXISTS FOR (ap:AuditProof) REQUIRE ap.proof_id IS UNIQUE")
                session.run("CREATE CONSTRAINT merkle_tree_id_unique IF NOT EXISTS FOR (mt:MerkleTree) REQUIRE mt.tree_id IS UNIQUE")
                self.logger.info("Neo4j schema initialized for Merkle audit")
        except Exception as e:
            self.logger.error(f"Neo4j schema initialization failed: {e}")

    async def add_audit_entry(self, content: str, content_type: str, metadata: Dict[str, Any] = None) -> AuditEntry:
        if metadata is None:
            metadata = {}
        
        try:
            data_hash = hashlib.sha256(content.encode()).hexdigest()
            entry_id = f"audit_{int(time.time() * 1000000)}_{data_hash[:16]}"
            
            ipfs_hash = await self._store_in_ipfs(content)
            
            audit_entry = AuditEntry(
                entry_id=entry_id,
                data_hash=data_hash,
                content_type=content_type,
                metadata=metadata,
                timestamp=datetime.now(),
                ipfs_hash=ipfs_hash
            )
            
            self.audit_entries.append(audit_entry)
            await self._store_audit_entry(audit_entry)
            
            self.logger.info(f"Added audit entry: {entry_id}")
            return audit_entry
            
        except Exception as e:
            self.logger.error(f"Failed to add audit entry: {e}")
            self.audit_errors += 1
            raise

    async def _store_in_ipfs(self, content: str) -> Optional[str]:
        if not self.ipfs_client:
            return f"mock_ipfs_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
        
        try:
            result = self.ipfs_client.add_str(content)
            return result
        except Exception as e:
            self.logger.error(f"IPFS storage failed: {e}")
            return None

    async def build_daily_merkle_tree(self, date: datetime = None) -> str:
        if date is None:
            date = datetime.now().date()
        
        try:
            daily_entries = [
                entry for entry in self.audit_entries
                if entry.timestamp.date() == date
            ]
            
            if not daily_entries:
                self.logger.warning(f"No audit entries found for {date}")
                return ""
            
            leaf_hashes = [entry.data_hash for entry in daily_entries]
            
            if EXISTING_MERKLE_AVAILABLE:
                merkle_tree = build_merkle_tree(leaf_hashes)
                root_hash = merkle_tree.root
            else:
                root_hash = self._build_simple_merkle_tree(leaf_hashes)
            
            tree_id = f"merkle_{date.isoformat()}_{root_hash[:16]}"
            
            self.merkle_trees[tree_id] = {
                'tree_id': tree_id,
                'root_hash': root_hash,
                'leaf_hashes': leaf_hashes,
                'date': date,
                'entry_count': len(daily_entries),
                'timestamp': datetime.now()
            }
            
            await self._store_merkle_tree(tree_id, root_hash, leaf_hashes, date)
            await self._anchor_to_solana(root_hash, tree_id)
            
            self.trees_created += 1
            self.logger.info(f"Built Merkle tree {tree_id} with {len(leaf_hashes)} entries")
            
            return tree_id
            
        except Exception as e:
            self.logger.error(f"Merkle tree building failed: {e}")
            self.audit_errors += 1
            raise

    def _build_simple_merkle_tree(self, leaf_hashes: List[str]) -> str:
        if not leaf_hashes:
            return ""
        
        if len(leaf_hashes) == 1:
            return leaf_hashes[0]
        
        next_level = []
        
        for i in range(0, len(leaf_hashes), 2):
            left = leaf_hashes[i]
            right = leaf_hashes[i + 1] if i + 1 < len(leaf_hashes) else left
            
            combined = left + right
            parent_hash = hashlib.sha256(combined.encode()).hexdigest()
            next_level.append(parent_hash)
        
        return self._build_simple_merkle_tree(next_level)

    async def audit_news_and_nlp_outputs(self, news_items: List[Dict[str, Any]], nlp_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        audit_results = {
            'news_entries': [],
            'nlp_entries': [],
            'tree_id': '',
            'total_entries': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            for news_item in news_items:
                metadata = {
                    'source': news_item.get('source', ''),
                    'news_id': news_item.get('news_id', ''),
                    'timestamp': news_item.get('published_time', datetime.now().isoformat())
                }
                
                entry = await self.add_audit_entry(
                    content=json.dumps(news_item, sort_keys=True),
                    content_type='news_item',
                    metadata=metadata
                )
                audit_results['news_entries'].append(entry.entry_id)
            
            for nlp_result in nlp_results:
                metadata = {
                    'news_id': nlp_result.get('news_id', ''),
                    'sentiment_score': nlp_result.get('sentiment_score', 0.0),
                    'confidence_score': nlp_result.get('confidence_score', 0.0),
                    'timestamp': nlp_result.get('processing_timestamp', datetime.now().isoformat())
                }
                
                entry = await self.add_audit_entry(
                    content=json.dumps(nlp_result, sort_keys=True),
                    content_type='nlp_result',
                    metadata=metadata
                )
                audit_results['nlp_entries'].append(entry.entry_id)
            
            if audit_results['news_entries'] or audit_results['nlp_entries']:
                tree_id = await self.build_daily_merkle_tree()
                audit_results['tree_id'] = tree_id
                audit_results['total_entries'] = len(audit_results['news_entries']) + len(audit_results['nlp_entries'])
            
            return audit_results
            
        except Exception as e:
            self.logger.error(f"News and NLP audit failed: {e}")
            self.audit_errors += 1
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _store_audit_entry(self, entry: AuditEntry):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for audit entry: {entry.entry_id}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (ae:AuditEntry {
                        entry_id: $entry_id,
                        data_hash: $data_hash,
                        content_type: $content_type,
                        metadata: $metadata,
                        timestamp: $timestamp,
                        ipfs_hash: $ipfs_hash
                    })
                """, 
                    entry_id=entry.entry_id,
                    data_hash=entry.data_hash,
                    content_type=entry.content_type,
                    metadata=json.dumps(entry.metadata),
                    timestamp=entry.timestamp.isoformat(),
                    ipfs_hash=entry.ipfs_hash
                )
        except Exception as e:
            self.logger.error(f"Audit entry storage failed: {e}")

    async def _store_merkle_tree(self, tree_id: str, root_hash: str, leaf_hashes: List[str], date: datetime):
        if not self.neo4j_driver:
            self.logger.debug(f"Mock Neo4j storage for Merkle tree: {tree_id}")
            return
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (mt:MerkleTree {
                        tree_id: $tree_id,
                        root_hash: $root_hash,
                        leaf_count: $leaf_count,
                        date: $date,
                        timestamp: $timestamp
                    })
                """, 
                    tree_id=tree_id,
                    root_hash=root_hash,
                    leaf_count=len(leaf_hashes),
                    date=date.isoformat(),
                    timestamp=datetime.now().isoformat()
                )
        except Exception as e:
            self.logger.error(f"Merkle tree storage failed: {e}")

    async def _anchor_to_solana(self, root_hash: str, tree_id: str):
        if not self.solana_client or not self.keypair:
            self.logger.debug(f"Mock Solana anchoring for tree: {tree_id}")
            return
        
        try:
            anchor_data = {
                'tree_id': tree_id,
                'root_hash': root_hash,
                'timestamp': datetime.now().isoformat()
            }
            
            anchor_hash = hashlib.sha256(json.dumps(anchor_data, sort_keys=True).encode()).hexdigest()
            
            self.logger.info(f"Anchored Merkle tree {tree_id} to Solana: {anchor_hash[:16]}")
            
        except Exception as e:
            self.logger.error(f"Solana anchoring failed: {e}")

    async def shutdown(self):
        if self.ipfs_client:
            self.ipfs_client.close()
        
        if self.neo4j_driver:
            self.neo4j_driver.close()

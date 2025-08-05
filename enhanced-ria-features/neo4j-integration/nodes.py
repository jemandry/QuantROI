from neo4j import GraphDatabase
from datetime import datetime
import logging
from typing import Dict, Any
import json
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NodeManager:
    def __init__(self, driver: GraphDatabase.driver):
        """Initialize with Neo4j driver."""
        self.driver = driver

    def upload_to_ipfs(self, data: Dict[str, Any]) -> str:
        """Upload data to IPFS and return hash (placeholder)."""
        try:
            data_json = json.dumps(data, sort_keys=True)
            ipfs_hash = hashlib.sha256(data_json.encode()).hexdigest()
            logger.info(f"Mock IPFS upload: {ipfs_hash}")
            return ipfs_hash
        except Exception as e:
            logger.error(f"IPFS upload failed: {e}")
            return "mock_ipfs_hash"

    def create_causal_node(self, event: str, impact: str, confidence: float, source: str, date: str) -> Dict[str, Any]:
        """Create CausalNode and NewsNode with CAUSED_BY relationship."""
        query = """
        CREATE (c:CausalNode {event: $event, impact: $impact, confidence: $confidence, created_at: datetime()})
        CREATE (n:NewsNode {source: $source, date: $date, first_published_timestamp: datetime()})
        CREATE (c)-[:CAUSED_BY]->(n)
        RETURN c, n
        """
        data = {"event": event, "impact": impact, "confidence": confidence, "source": source, "date": date}
        ipfs_hash = self.upload_to_ipfs(data)
        
        with self.driver.session() as session:
            try:
                result = session.run(query, **data)
                record = result.single()
                logger.info(f"Created CausalNode: {event}")
                return {
                    "causal_node": dict(record["c"]),
                    "news_node": dict(record["n"]),
                    "ipfs_hash": ipfs_hash
                }
            except Exception as e:
                logger.error(f"Failed to create CausalNode: {e}")
                raise

    def create_vote_node(self, voter_id: str, suggestion: str, timestamp: str, zkp_proof: str) -> Dict[str, Any]:
        """Create VoteNode with ZKP proof."""
        zkp_data = {"voter_id": voter_id, "suggestion": suggestion, "zkp_proof": zkp_proof}
        zkp_proof_hash = self.upload_to_ipfs(zkp_data)
        
        data = {
            "voter_id": voter_id,
            "suggestion": suggestion,
            "timestamp": timestamp,
            "zkp_proof_hash": zkp_proof_hash,
            "created_at": datetime.now().isoformat()
        }
        
        query = """
        CREATE (v:VoteNode {
            voter_id: $voter_id, 
            suggestion: $suggestion, 
            timestamp: $timestamp, 
            zkp_proof_hash: $zkp_proof_hash,
            created_at: datetime()
        })
        RETURN v
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, **data)
                record = result.single()
                logger.info(f"Created VoteNode for voter: {voter_id}")
                return {
                    "vote_node": dict(record["v"]),
                    "zkp_proof_hash": zkp_proof_hash
                }
            except Exception as e:
                logger.error(f"Failed to create VoteNode: {e}")
                raise

    def create_news_node(self, source: str, content_summary: str, first_published_timestamp: str) -> Dict[str, Any]:
        """Create NewsNode with source attribution and first occurrence detection."""
        data = {
            "source": source,
            "content_summary": content_summary,
            "first_published_timestamp": first_published_timestamp,
            "created_at": datetime.now().isoformat()
        }
        
        query = """
        CREATE (n:NewsNode {
            source: $source,
            content_summary: $content_summary,
            first_published_timestamp: $first_published_timestamp,
            created_at: datetime()
        })
        RETURN n
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, **data)
                record = result.single()
                logger.info(f"Created NewsNode from source: {source}")
                return {"news_node": dict(record["n"])}
            except Exception as e:
                logger.error(f"Failed to create NewsNode: {e}")
                raise

    def get_node_by_id(self, node_type: str, node_id: str) -> Dict[str, Any]:
        """Get node by ID and type."""
        query = f"""
        MATCH (n:{node_type})
        WHERE n.voter_id = $node_id OR n.event = $node_id OR n.source = $node_id
        RETURN n
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, node_id=node_id)
                record = result.single()
                if record:
                    return dict(record["n"])
                return None
            except Exception as e:
                logger.error(f"Failed to get {node_type} node: {e}")
                raise

    def create_identity_node(self, random_vote_id: str, nullifier: str, stake_amount: float) -> Dict[str, Any]:
        """Create IdentityNode with anonymous random ID (US20200258338A1 Claim 3)"""
        query = """
        CREATE (i:IdentityNode {
            random_vote_id: $random_vote_id,
            nullifier: $nullifier,
            stake_amount: $stake_amount,
            created_at: datetime(),
            ipfs_hash: $ipfs_hash
        })
        RETURN i
        """
        
        try:
            identity_data = {
                "random_vote_id": random_vote_id,
                "nullifier": nullifier,
                "stake_amount": stake_amount
            }
            
            ipfs_hash = self.upload_to_ipfs(identity_data)
            
            with self.driver.session() as session:
                result = session.run(query, 
                    random_vote_id=random_vote_id,
                    nullifier=nullifier, 
                    stake_amount=stake_amount,
                    ipfs_hash=ipfs_hash
                )
                record = result.single()
                if record:
                    logger.info(f"Created IdentityNode with random vote ID: {random_vote_id}")
                    return {
                        "node": dict(record["i"]),
                        "ipfs_hash": ipfs_hash
                    }
                else:
                    logger.warning("Failed to create IdentityNode")
                    return None
        except Exception as e:
            logger.error(f"Failed to create IdentityNode: {e}")
            raise

    def create_delegation_node(self, delegation_id: str, authority: str, voting_period: int, 
                             min_stake_threshold: float, description: str = "") -> Dict[str, Any]:
        """Create DelegationNode for governance delegation tracking"""
        query = """
        CREATE (d:DelegationNode {
            delegation_id: $delegation_id,
            authority: $authority,
            voting_period: $voting_period,
            min_stake_threshold: $min_stake_threshold,
            description: $description,
            created_at: datetime(),
            is_active: true,
            total_votes: 0,
            ipfs_hash: $ipfs_hash
        })
        RETURN d
        """
        
        try:
            delegation_data = {
                "delegation_id": delegation_id,
                "authority": authority,
                "voting_period": voting_period,
                "min_stake_threshold": min_stake_threshold,
                "description": description
            }
            
            ipfs_hash = self.upload_to_ipfs(delegation_data)
            
            with self.driver.session() as session:
                result = session.run(query,
                    delegation_id=delegation_id,
                    authority=authority,
                    voting_period=voting_period,
                    min_stake_threshold=min_stake_threshold,
                    description=description,
                    ipfs_hash=ipfs_hash
                )
                record = result.single()
                if record:
                    logger.info(f"Created DelegationNode: {delegation_id}")
                    return {
                        "node": dict(record["d"]),
                        "ipfs_hash": ipfs_hash
                    }
                else:
                    logger.warning("Failed to create DelegationNode")
                    return None
        except Exception as e:
            logger.error(f"Failed to create DelegationNode: {e}")
            raise

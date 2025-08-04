#!/usr/bin/env python3
"""
Neo4j Integration for Smart Contract Delegation Relationships
Stores and queries delegation relationships in graph database
"""

import os
import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime

try: 
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("Warning: neo4j package not available. Install with: pip install neo4j")

class DelegationGraphIntegration:
    """Integration with Neo4j for delegation relationship management"""
    
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        
    def init_delegation_schema(self) -> bool:
        """Initialize Neo4j schema for delegation relationships"""
        if not NEO4J_AVAILABLE:
            return False
            
        try:
            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            with driver.session() as session:
                constraints = [
                    "CREATE CONSTRAINT delegation_unique IF NOT EXISTS FOR (d:Delegation) REQUIRE d.delegation_id IS UNIQUE",
                    "CREATE CONSTRAINT duty_unique IF NOT EXISTS FOR (duty:Duty) REQUIRE (duty.delegation_id, duty.duty_id) IS UNIQUE",
                    "CREATE CONSTRAINT user_unique IF NOT EXISTS FOR (u:User) REQUIRE u.pubkey IS UNIQUE",
                    "CREATE CONSTRAINT vote_unique IF NOT EXISTS FOR (v:Vote) REQUIRE (v.issue_id, v.voter_pubkey) IS UNIQUE",
                ]
                
                for constraint in constraints:
                    try:
                        session.run(constraint)
                        print(f"✓ Created constraint: {constraint}")
                    except Exception as e:
                        print(f"⚠ Constraint may already exist: {e}")
                
                indexes = [
                    "CREATE INDEX delegation_type_idx IF NOT EXISTS FOR (d:Delegation) ON (d.delegation_type)",
                    "CREATE INDEX duty_status_idx IF NOT EXISTS FOR (duty:Duty) ON (duty.status)",
                    "CREATE INDEX user_role_idx IF NOT EXISTS FOR (u:User) ON (u.role)",
                    "CREATE INDEX vote_type_idx IF NOT EXISTS FOR (v:Vote) ON (v.voter_type)",
                    "CREATE INDEX audit_type_idx IF NOT EXISTS FOR (a:Audit) ON (a.audit_type)",
                ]
                
                for index in indexes:
                    try:
                        session.run(index)
                        print(f"✓ Created index: {index}")
                    except Exception as e:
                        print(f"⚠ Index may already exist: {e}")
            
            driver.close()
            return True
            
        except Exception as e:
            print(f"✗ Failed to initialize delegation schema: {e}")
            return False
    
    def store_delegation_relationship(
        self,
        delegation_id: str,
        delegator_pubkey: str,
        delegatee_pubkey: str,
        delegation_type: str,
        contract_terms: Dict,
        audit_config: Dict,
        voting_config: Optional[Dict] = None
    ) -> bool:
        """Store delegation relationship in Neo4j"""
        if not NEO4J_AVAILABLE:
            return False
            
        try:
            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            with driver.session() as session:
                query = """
                MERGE (delegator:User {pubkey: $delegator_pubkey})
                MERGE (delegatee:User {pubkey: $delegatee_pubkey})
                MERGE (delegation:Delegation {
                    delegation_id: $delegation_id,
                    delegation_type: $delegation_type,
                    created_at: $timestamp,
                    contract_terms_hash: $contract_terms_hash,
                    audit_frequency: $audit_frequency,
                    payment_on_delivery: $payment_on_delivery,
                    vrf_enabled: $vrf_enabled,
                    oracle_verification: $oracle_verification,
                    voting_enabled: $voting_enabled
                })
                CREATE (delegator)-[:DELEGATES_TO {
                    delegation_id: $delegation_id,
                    created_at: $timestamp,
                    active: true
                }]->(delegatee)
                CREATE (delegation)-[:INVOLVES]->(delegator)
                CREATE (delegation)-[:INVOLVES]->(delegatee)
                """
                
                session.run(query,
                    delegation_id=delegation_id,
                    delegator_pubkey=delegator_pubkey,
                    delegatee_pubkey=delegatee_pubkey,
                    delegation_type=delegation_type,
                    timestamp=datetime.now().isoformat(),
                    contract_terms_hash=hashlib.sha256(json.dumps(contract_terms, sort_keys=True).encode()).hexdigest(),
                    audit_frequency=audit_config.get('frequency', 'monthly'),
                    payment_on_delivery=contract_terms.get('payment_on_delivery', True),
                    vrf_enabled=audit_config.get('vrf_enabled', False),
                    oracle_verification=contract_terms.get('oracle_verification_required', False),
                    voting_enabled=voting_config is not None if voting_config else False
                )
            
            driver.close()
            print(f"✓ Stored delegation relationship: {delegation_id}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to store delegation relationship: {e}")
            return False

    def store_ai_audit_result(
        self,
        delegation_id: str,
        duty_id: str,
        ai_auditor_pubkey: str,
        completeness_score: int,
        sincerity_score: int,
        findings: List[str]
    ) -> bool:
        """Store AI audit results for completeness/sincerity measurement"""
        if not NEO4J_AVAILABLE:
            return False
            
        try:
            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            with driver.session() as session:
                query = """
                MATCH (delegation:Delegation {delegation_id: $delegation_id})
                MERGE (auditor:User {pubkey: $ai_auditor_pubkey, role: 'ai_auditor'})
                CREATE (audit:Audit {
                    audit_id: $audit_id,
                    delegation_id: $delegation_id,
                    duty_id: $duty_id,
                    audit_type: 'ai_driven',
                    completeness_score: $completeness_score,
                    sincerity_score: $sincerity_score,
                    overall_score: $overall_score,
                    findings: $findings,
                    timestamp: $timestamp
                })
                CREATE (auditor)-[:CONDUCTED]->(audit)
                CREATE (audit)-[:AUDITS]->(delegation)
                """
                
                overall_score = (completeness_score + sincerity_score) / 2
                
                session.run(query,
                    delegation_id=delegation_id,
                    duty_id=duty_id,
                    ai_auditor_pubkey=ai_auditor_pubkey,
                    audit_id=f"{delegation_id}_{duty_id}_{datetime.now().timestamp()}",
                    completeness_score=completeness_score,
                    sincerity_score=sincerity_score,
                    overall_score=overall_score,
                    findings=findings,
                    timestamp=datetime.now().isoformat()
                )
            
            driver.close()
            print(f"✓ Stored AI audit result for duty: {duty_id}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to store AI audit result: {e}")
            return False

    def store_voting_result(
        self,
        delegation_id: str,
        issue_id: str,
        voter_pubkey: str,
        vote: bool,
        voter_type: str,
        vote_weight: int,
        is_major_issue: bool,
        ai_classification_score: Optional[float] = None
    ) -> bool:
        """Store voting results for employee/shareholder governance"""
        if not NEO4J_AVAILABLE:
            return False
            
        try:
            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            with driver.session() as session:
                query = """
                MATCH (delegation:Delegation {delegation_id: $delegation_id})
                MERGE (voter:User {pubkey: $voter_pubkey})
                CREATE (vote:Vote {
                    vote_id: $vote_id,
                    issue_id: $issue_id,
                    delegation_id: $delegation_id,
                    voter_pubkey: $voter_pubkey,
                    vote: $vote,
                    voter_type: $voter_type,
                    vote_weight: $vote_weight,
                    is_major_issue: $is_major_issue,
                    ai_classification_score: $ai_classification_score,
                    timestamp: $timestamp
                })
                CREATE (voter)-[:CAST]->(vote)
                CREATE (vote)-[:CONCERNS]->(delegation)
                """
                
                session.run(query,
                    delegation_id=delegation_id,
                    issue_id=issue_id,
                    voter_pubkey=voter_pubkey,
                    vote_id=f"{issue_id}_{voter_pubkey}_{datetime.now().timestamp()}",
                    vote=vote,
                    voter_type=voter_type,
                    vote_weight=vote_weight,
                    is_major_issue=is_major_issue,
                    ai_classification_score=ai_classification_score,
                    timestamp=datetime.now().isoformat()
                )
            
            driver.close()
            print(f"✓ Stored voting result for issue: {issue_id}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to store voting result: {e}")
            return False

    def query_delegation_analytics(
        self,
        delegation_id: str = None,
        delegation_type: str = None
    ) -> Dict:
        """Query delegation analytics including AI audit scores and voting patterns"""
        if not NEO4J_AVAILABLE:
            return {}
            
        try:
            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            with driver.session() as session:
                where_clauses = []
                params = {}
                
                if delegation_id:
                    where_clauses.append("d.delegation_id = $delegation_id")
                    params['delegation_id'] = delegation_id
                
                if delegation_type:
                    where_clauses.append("d.delegation_type = $delegation_type")
                    params['delegation_type'] = delegation_type
                
                where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                
                query = f"""
                MATCH (d:Delegation)
                {where_clause}
                OPTIONAL MATCH (a:Audit)-[:AUDITS]->(d)
                OPTIONAL MATCH (v:Vote)-[:CONCERNS]->(d)
                RETURN d,
                       collect(DISTINCT a) as audits,
                       collect(DISTINCT v) as votes,
                       avg(a.completeness_score) as avg_completeness,
                       avg(a.sincerity_score) as avg_sincerity,
                       count(DISTINCT a) as total_audits,
                       count(DISTINCT v) as total_votes
                """
                
                result = session.run(query, **params)
                analytics = {}
                
                for record in result:
                    delegation = dict(record['d'])
                    analytics[delegation['delegation_id']] = {
                        'delegation_info': delegation,
                        'audit_analytics': {
                            'total_audits': record['total_audits'],
                            'avg_completeness_score': record['avg_completeness'] or 0,
                            'avg_sincerity_score': record['avg_sincerity'] or 0,
                        },
                        'voting_analytics': {
                            'total_votes': record['total_votes'],
                        }
                    }
            
            driver.close()
            return analytics
            
        except Exception as e:
            print(f"✗ Failed to query delegation analytics: {e}")
            return {}

if __name__ == "__main__":
    integration = DelegationGraphIntegration()
    integration.init_delegation_schema()

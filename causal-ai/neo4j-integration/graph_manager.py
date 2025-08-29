#!/usr/bin/env python3
"""
Neo4j Graph Manager for Causal AI Integration
Manages market relationships, news correlations, and delegation networks
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from neo4j import GraphDatabase
import json

class CausalGraphManager:
    """Manages Neo4j graph database for causal relationships"""
    
    def __init__(self, uri: str = 'bolt://localhost:7687', user: str = 'neo4j', password: str = 'password'):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = logging.getLogger(__name__)
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize Neo4j schema with constraints and indexes"""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT causal_link_unique IF NOT EXISTS FOR (c:CausalLinkNode) REQUIRE c.link_id IS UNIQUE",
                "CREATE CONSTRAINT market_correlation_unique IF NOT EXISTS FOR (m:MarketCorrelationNode) REQUIRE (m.symbol_pair, m.timeframe) IS UNIQUE",
                "CREATE CONSTRAINT news_unique IF NOT EXISTS FOR (n:News) REQUIRE n.news_id IS UNIQUE",
                "CREATE CONSTRAINT delegation_unique IF NOT EXISTS FOR (d:DelegationNode) REQUIRE d.delegation_id IS UNIQUE",
                "CREATE CONSTRAINT vote_unique IF NOT EXISTS FOR (v:VoteNode) REQUIRE v.vote_id IS UNIQUE"
            ]
            
            indexes = [
                "CREATE INDEX causal_link_symbols IF NOT EXISTS FOR (c:CausalLinkNode) ON (c.source_symbol, c.target_symbol)",
                "CREATE INDEX news_timestamp IF NOT EXISTS FOR (n:News) ON n.first_published_timestamp",
                "CREATE INDEX delegation_status IF NOT EXISTS FOR (d:DelegationNode) ON d.status"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    self.logger.warning(f"Constraint may already exist: {e}")
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    self.logger.warning(f"Index may already exist: {e}")
    
    async def create_causal_relationship(
        self,
        source_symbol: str,
        target_symbol: str,
        causal_strength: float,
        confidence_score: float,
        timeframe: str = "1h",
        evidence: Dict[str, Any] = None
    ) -> str:
        """Create causal relationship between market entities"""
        with self.driver.session() as session:
            query = """
            MERGE (source:MarketEntity {symbol: $source_symbol})
            MERGE (target:MarketEntity {symbol: $target_symbol})
            CREATE (causal:CausalLinkNode {
                link_id: $link_id,
                source_symbol: $source_symbol,
                target_symbol: $target_symbol,
                causal_strength: $causal_strength,
                confidence_score: $confidence_score,
                timeframe: $timeframe,
                evidence: $evidence,
                created_at: $timestamp
            })
            CREATE (source)-[:CAUSES {strength: $causal_strength, confidence: $confidence_score}]->(target)
            CREATE (causal)-[:LINKS_FROM]->(source)
            CREATE (causal)-[:LINKS_TO]->(target)
            RETURN causal.link_id as link_id
            """
            
            link_id = f"{source_symbol}_{target_symbol}_{timeframe}_{datetime.now().timestamp()}"
            result = session.run(query,
                link_id=link_id,
                source_symbol=source_symbol,
                target_symbol=target_symbol,
                causal_strength=causal_strength,
                confidence_score=confidence_score,
                timeframe=timeframe,
                evidence=json.dumps(evidence or {}),
                timestamp=datetime.now().isoformat()
            )
            
            return result.single()['link_id']
    
    async def store_news_event(
        self,
        news_id: str,
        source: str,
        first_published_timestamp: datetime,
        content_summary: str,
        market_impact_symbols: List[str],
        sentiment_score: float = 0.0
    ) -> bool:
        """Store news event with market impact relationships"""
        with self.driver.session() as session:
            query = """
            CREATE (news:News {
                news_id: $news_id,
                source: $source,
                first_published_timestamp: $first_published_timestamp,
                content_summary: $content_summary,
                market_impact_symbols: $market_impact_symbols,
                sentiment_score: $sentiment_score,
                created_at: $timestamp
            })
            WITH news
            UNWIND $market_impact_symbols as symbol
            MERGE (market:MarketEntity {symbol: symbol})
            CREATE (news)-[:IMPACTS {sentiment: $sentiment_score}]->(market)
            """
            
            session.run(query,
                news_id=news_id,
                source=source,
                first_published_timestamp=first_published_timestamp.isoformat(),
                content_summary=content_summary,
                market_impact_symbols=market_impact_symbols,
                sentiment_score=sentiment_score,
                timestamp=datetime.now().isoformat()
            )
            
            return True
    
    async def create_delegation_network(
        self,
        delegation_id: str,
        delegator: str,
        delegatee: str,
        delegation_type: str,
        duties: List[str],
        status: str = "active"
    ) -> str:
        """Create delegation network node"""
        with self.driver.session() as session:
            query = """
            MERGE (delegator_node:Person {id: $delegator})
            MERGE (delegatee_node:Person {id: $delegatee})
            CREATE (delegation:DelegationNode {
                delegation_id: $delegation_id,
                delegator: $delegator,
                delegatee: $delegatee,
                delegation_type: $delegation_type,
                duties: $duties,
                status: $status,
                created_at: $timestamp
            })
            CREATE (delegator_node)-[:DELEGATES_TO {type: $delegation_type}]->(delegatee_node)
            CREATE (delegation)-[:FROM]->(delegator_node)
            CREATE (delegation)-[:TO]->(delegatee_node)
            RETURN delegation.delegation_id as delegation_id
            """
            
            result = session.run(query,
                delegation_id=delegation_id,
                delegator=delegator,
                delegatee=delegatee,
                delegation_type=delegation_type,
                duties=duties,
                status=status,
                timestamp=datetime.now().isoformat()
            )
            
            return result.single()['delegation_id']
    
    async def query_causal_paths(
        self,
        source_symbol: str,
        target_symbol: str,
        max_depth: int = 3,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Query causal paths between market entities"""
        with self.driver.session() as session:
            query = """
            MATCH path = (source:MarketEntity {symbol: $source_symbol})
                        -[:CAUSES*1..$max_depth]->
                        (target:MarketEntity {symbol: $target_symbol})
            WHERE ALL(rel in relationships(path) WHERE rel.confidence >= $min_confidence)
            RETURN path,
                   [rel in relationships(path) | rel.strength] as strengths,
                   [rel in relationships(path) | rel.confidence] as confidences,
                   length(path) as path_length
            ORDER BY path_length ASC, 
                     reduce(total = 1.0, conf in confidences | total * conf) DESC
            LIMIT 10
            """
            
            result = session.run(query,
                source_symbol=source_symbol,
                target_symbol=target_symbol,
                max_depth=max_depth,
                min_confidence=min_confidence
            )
            
            paths = []
            for record in result:
                paths.append({
                    'path_length': record['path_length'],
                    'strengths': record['strengths'],
                    'confidences': record['confidences'],
                    'overall_confidence': sum(record['confidences']) / len(record['confidences']),
                    'path_strength': sum(record['strengths']) / len(record['strengths'])
                })
            
            return paths
    
    async def get_market_influence_network(
        self,
        symbol: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Get market influence network for a symbol"""
        with self.driver.session() as session:
            query = """
            MATCH (center:MarketEntity {symbol: $symbol})
            OPTIONAL MATCH (center)-[out_rel:CAUSES]->(influenced)
            OPTIONAL MATCH (influencer)-[in_rel:CAUSES]->(center)
            OPTIONAL MATCH (center)<-[:IMPACTS]-(news:News)
            RETURN center,
                   collect(DISTINCT {symbol: influenced.symbol, strength: out_rel.strength, confidence: out_rel.confidence}) as influences,
                   collect(DISTINCT {symbol: influencer.symbol, strength: in_rel.strength, confidence: in_rel.confidence}) as influenced_by,
                   collect(DISTINCT {news_id: news.news_id, source: news.source, sentiment: news.sentiment_score}) as news_events
            """
            
            result = session.run(query, symbol=symbol)
            record = result.single()
            
            if not record:
                return {}
            
            return {
                'symbol': symbol,
                'influences': [inf for inf in record['influences'] if inf['symbol']],
                'influenced_by': [inf for inf in record['influenced_by'] if inf['symbol']],
                'news_events': record['news_events'],
                'network_size': len(record['influences']) + len(record['influenced_by'])
            }
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()

async def main():
    """Example usage of Causal Graph Manager"""
    graph_manager = CausalGraphManager()
    
    try:
        link_id = await graph_manager.create_causal_relationship(
            source_symbol="AAPL",
            target_symbol="MSFT",
            causal_strength=0.75,
            confidence_score=0.92,
            timeframe="1d",
            evidence={"granger_test": 0.001, "correlation": 0.68}
        )
        print(f"Created causal link: {link_id}")
        
        await graph_manager.store_news_event(
            news_id="news_001",
            source="Reuters",
            first_published_timestamp=datetime.now(),
            content_summary="Apple reports strong quarterly earnings",
            market_impact_symbols=["AAPL", "MSFT"],
            sentiment_score=0.8
        )
        print("Stored news event")
        
        delegation_id = await graph_manager.create_delegation_network(
            delegation_id="del_001",
            delegator="CEO",
            delegatee="Assistant",
            delegation_type="ceo_to_assistant",
            duties=["Complete market analysis", "Prepare quarterly report"]
        )
        print(f"Created delegation network: {delegation_id}")
        
        paths = await graph_manager.query_causal_paths("AAPL", "MSFT")
        print(f"Found {len(paths)} causal paths")
        
        network = await graph_manager.get_market_influence_network("AAPL")
        print(f"Market network size: {network.get('network_size', 0)}")
        
    finally:
        graph_manager.close()

if __name__ == "__main__":
    asyncio.run(main())

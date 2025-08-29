import asyncio
import logging
import networkx as nx
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class CausalNode:
    node_id: str
    node_type: str
    influence_strength: float
    temporal_lag_minutes: int
    confidence_score: float

@dataclass
class CausalEdge:
    source_id: str
    target_id: str
    causal_strength: float
    mechanism: str
    evidence_sources: List[str]

class CausalDriverGraph:
    """Causal influence graph for price drivers with news/macro integration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.graph = nx.DiGraph()
        self.causal_chains = {}
        self.event_history = []
        
        self._initialize_core_relationships()
    
    def _initialize_core_relationships(self):
        """Initialize fundamental economic causal relationships"""
        fed_node = CausalNode("fed_decisions", "macro_event", 0.9, 0, 0.95)
        bond_node = CausalNode("bond_yields", "market_indicator", 0.8, 15, 0.90)
        tech_node = CausalNode("tech_etf", "asset_price", 0.7, 30, 0.85)
        vix_node = CausalNode("vix_volatility", "market_indicator", 0.85, 5, 0.88)
        dollar_node = CausalNode("dollar_index", "market_indicator", 0.75, 20, 0.82)
        
        nodes = [fed_node, bond_node, tech_node, vix_node, dollar_node]
        for node in nodes:
            self.graph.add_node(node.node_id, **node.__dict__)
        
        fed_to_bonds = CausalEdge(
            "fed_decisions", "bond_yields", 0.85,
            "interest_rate_transmission", ["fed_minutes", "treasury_data"]
        )
        bonds_to_tech = CausalEdge(
            "bond_yields", "tech_etf", -0.75,
            "discount_rate_valuation", ["yield_curves", "sector_flows"]
        )
        fed_to_dollar = CausalEdge(
            "fed_decisions", "dollar_index", 0.70,
            "monetary_policy_transmission", ["fed_statements", "rate_expectations"]
        )
        bonds_to_vix = CausalEdge(
            "bond_yields", "vix_volatility", -0.60,
            "risk_sentiment_transmission", ["volatility_data", "options_flow"]
        )
        vix_to_tech = CausalEdge(
            "vix_volatility", "tech_etf", -0.80,
            "risk_aversion_mechanism", ["volatility_indices", "sector_rotation"]
        )
        
        edges = [fed_to_bonds, bonds_to_tech, fed_to_dollar, bonds_to_vix, vix_to_tech]
        for edge in edges:
            self.graph.add_edge(edge.source_id, edge.target_id, **edge.__dict__)
        
        self.causal_chains["fed_tech_transmission"] = [
            fed_node.node_id, bond_node.node_id, tech_node.node_id
        ]
        self.causal_chains["fed_volatility_tech"] = [
            fed_node.node_id, bond_node.node_id, vix_node.node_id, tech_node.node_id
        ]
    
    async def ingest_news_event(self, event: Dict[str, Any]) -> bool:
        """Ingest news events and update causal graph"""
        try:
            event_type = self._classify_news_event(event)
            if not event_type:
                return False
            
            news_node = CausalNode(
                f"news_{event.get('id', int(datetime.now().timestamp()))}",
                "news_event",
                self._assess_news_influence(event),
                0,
                event.get('confidence', 0.7)
            )
            
            self.graph.add_node(news_node.node_id, **news_node.__dict__)
            
            affected_nodes = self._identify_affected_nodes(event, event_type)
            for target_node in affected_nodes:
                edge = CausalEdge(
                    news_node.node_id,
                    target_node,
                    self._calculate_news_impact(event, target_node),
                    "information_transmission",
                    [event.get('source', 'unknown')]
                )
                self.graph.add_edge(edge.source_id, edge.target_id, **edge.__dict__)
            
            self.event_history.append({
                'event': event,
                'node_id': news_node.node_id,
                'affected_nodes': affected_nodes,
                'timestamp': datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error ingesting news event: {e}")
            return False
    
    def _classify_news_event(self, event: Dict[str, Any]) -> Optional[str]:
        """Classify news event type for causal analysis"""
        summary = event.get('summary', '').lower()
        
        if any(word in summary for word in ['fed', 'federal reserve', 'interest rate', 'monetary policy']):
            return 'monetary_policy'
        elif any(word in summary for word in ['earnings', 'revenue', 'profit', 'guidance']):
            return 'earnings'
        elif any(word in summary for word in ['merger', 'acquisition', 'partnership', 'deal']):
            return 'corporate_action'
        elif any(word in summary for word in ['regulation', 'policy', 'government', 'congress']):
            return 'regulatory'
        elif any(word in summary for word in ['oil', 'energy', 'crude', 'gas']):
            return 'energy'
        elif any(word in summary for word in ['inflation', 'cpi', 'ppi', 'employment']):
            return 'economic_data'
        
        return None
    
    def _assess_news_influence(self, event: Dict[str, Any]) -> float:
        """Assess the influence strength of a news event"""
        base_influence = 0.5
        
        summary = event.get('summary', '').lower()
        source = event.get('source', '').lower()
        
        if 'fed' in summary or 'federal reserve' in summary:
            base_influence = 0.9
        elif 'earnings' in summary:
            base_influence = 0.7
        elif 'breaking' in summary:
            base_influence += 0.2
        
        if source in ['reuters', 'bloomberg', 'wsj']:
            base_influence += 0.1
        elif source in ['twitter', 'reddit']:
            base_influence -= 0.2
        
        return min(1.0, max(0.1, base_influence))
    
    def _identify_affected_nodes(self, event: Dict[str, Any], event_type: str) -> List[str]:
        """Identify which nodes are affected by the news event"""
        affected = []
        
        if event_type == 'monetary_policy':
            affected.extend(['fed_decisions', 'bond_yields', 'dollar_index'])
        elif event_type == 'earnings':
            symbol = event.get('symbol', '').upper()
            if symbol in ['QQQ', 'XLK', 'AAPL', 'MSFT', 'GOOGL']:
                affected.append('tech_etf')
        elif event_type == 'economic_data':
            affected.extend(['bond_yields', 'vix_volatility', 'dollar_index'])
        elif event_type == 'energy':
            affected.extend(['dollar_index'])
        
        return affected
    
    def _calculate_news_impact(self, event: Dict[str, Any], target_node: str) -> float:
        """Calculate the impact strength of news on a target node"""
        base_impact = 0.3
        
        summary = event.get('summary', '').lower()
        
        if target_node == 'fed_decisions' and 'fed' in summary:
            base_impact = 0.8
        elif target_node == 'bond_yields' and any(word in summary for word in ['yield', 'bond', 'treasury']):
            base_impact = 0.7
        elif target_node == 'tech_etf' and any(word in summary for word in ['tech', 'technology', 'ai']):
            base_impact = 0.6
        
        sentiment = event.get('sentiment', 0)
        if abs(sentiment) > 0.5:
            base_impact += 0.2
        
        return min(1.0, base_impact)
    
    def analyze_causal_pathway(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        """Analyze causal pathway between two nodes"""
        try:
            if not self.graph.has_node(source) or not self.graph.has_node(target):
                return None
            
            try:
                path = nx.shortest_path(self.graph, source, target)
            except nx.NetworkXNoPath:
                return None
            
            total_strength = 1.0
            mechanisms = []
            evidence_sources = []
            
            for i in range(len(path) - 1):
                edge_data = self.graph.edges[path[i], path[i+1]]
                total_strength *= abs(edge_data['causal_strength'])
                mechanisms.append(edge_data['mechanism'])
                evidence_sources.extend(edge_data['evidence_sources'])
            
            return {
                'pathway': path,
                'total_strength': total_strength,
                'mechanisms': mechanisms,
                'evidence_sources': list(set(evidence_sources)),
                'pathway_length': len(path) - 1,
                'estimated_lag_minutes': sum(
                    self.graph.nodes[node]['temporal_lag_minutes'] for node in path
                ),
                'confidence_score': min(
                    self.graph.nodes[node]['confidence_score'] for node in path
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing causal pathway: {e}")
            return None
    
    def get_node_influences(self, node_id: str) -> Dict[str, Any]:
        """Get all influences affecting a specific node"""
        try:
            if not self.graph.has_node(node_id):
                return {}
            
            incoming_edges = list(self.graph.in_edges(node_id, data=True))
            outgoing_edges = list(self.graph.out_edges(node_id, data=True))
            
            influences = {
                'incoming_influences': [
                    {
                        'source': edge[0],
                        'strength': edge[2]['causal_strength'],
                        'mechanism': edge[2]['mechanism']
                    }
                    for edge in incoming_edges
                ],
                'outgoing_influences': [
                    {
                        'target': edge[1],
                        'strength': edge[2]['causal_strength'],
                        'mechanism': edge[2]['mechanism']
                    }
                    for edge in outgoing_edges
                ],
                'node_properties': dict(self.graph.nodes[node_id])
            }
            
            return influences
            
        except Exception as e:
            self.logger.error(f"Error getting node influences: {e}")
            return {}
    
    def detect_causal_anomalies(self, recent_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in causal relationships"""
        anomalies = []
        
        try:
            for event in recent_events:
                expected_pathway = self._get_expected_pathway(event)
                actual_impact = event.get('market_impact', {})
                
                for target, expected_strength in expected_pathway.items():
                    actual_strength = actual_impact.get(target, 0)
                    
                    if abs(actual_strength - expected_strength) > 0.3:
                        anomalies.append({
                            'event_id': event.get('id'),
                            'target_node': target,
                            'expected_strength': expected_strength,
                            'actual_strength': actual_strength,
                            'anomaly_magnitude': abs(actual_strength - expected_strength),
                            'anomaly_type': 'pathway_deviation'
                        })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting causal anomalies: {e}")
            return []
    
    def _get_expected_pathway(self, event: Dict[str, Any]) -> Dict[str, float]:
        """Get expected causal pathway impacts for an event"""
        event_type = self._classify_news_event(event)
        expected = {}
        
        if event_type == 'monetary_policy':
            expected = {
                'bond_yields': 0.7,
                'tech_etf': -0.5,
                'vix_volatility': -0.4,
                'dollar_index': 0.6
            }
        elif event_type == 'earnings':
            expected = {
                'tech_etf': 0.6,
                'vix_volatility': -0.3
            }
        
        return expected
    
    def export_graph_data(self) -> Dict[str, Any]:
        """Export graph data for visualization and analysis"""
        try:
            nodes_data = []
            for node_id, node_data in self.graph.nodes(data=True):
                nodes_data.append({
                    'id': node_id,
                    **node_data
                })
            
            edges_data = []
            for source, target, edge_data in self.graph.edges(data=True):
                edges_data.append({
                    'source': source,
                    'target': target,
                    **edge_data
                })
            
            return {
                'nodes': nodes_data,
                'edges': edges_data,
                'causal_chains': self.causal_chains,
                'event_history': self.event_history[-50:],
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting graph data: {e}")
            return {}

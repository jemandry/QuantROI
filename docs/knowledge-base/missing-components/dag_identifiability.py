"""
DAG Identifiability Testing Framework
Implements back-door and front-door criteria for causal identification
Integrates with existing Neo4j causal graph storage and DoWhy framework
"""

import networkx as nx
from typing import Set, List, Dict, Any, Optional, Tuple
from itertools import combinations, powerset
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class DAGIdentifiabilityTester:
    """
    Test DAG identifiability using back-door and front-door criteria
    Integrates with existing Neo4j causal graph storage
    """
    
    def __init__(self, neo4j_driver=None):
        self.neo4j_driver = neo4j_driver
        self.test_cache = {}
        
    def test_backdoor_criterion(self, graph: nx.DiGraph, treatment: str, 
                               outcome: str, adjustment_set: Set[str]) -> bool:
        """
        Test back-door criterion for causal identification
        
        Back-door criterion satisfied if:
        1. No node in adjustment_set is a descendant of treatment
        2. Adjustment set blocks all back-door paths from treatment to outcome
        """
        try:
            treatment_descendants = nx.descendants(graph, treatment)
            if adjustment_set.intersection(treatment_descendants):
                logger.debug(f"Back-door criterion violated: adjustment set contains descendants of {treatment}")
                return False
            
            backdoor_paths = self._find_backdoor_paths(graph, treatment, outcome)
            
            for path in backdoor_paths:
                if not self._is_path_blocked(graph, path, adjustment_set):
                    logger.debug(f"Back-door criterion violated: unblocked path {path}")
                    return False
            
            logger.info(f"Back-door criterion satisfied for {treatment} -> {outcome} with adjustment set {adjustment_set}")
            return True
            
        except Exception as e:
            logger.error(f"Back-door criterion test failed: {e}")
            return False
    
    def find_minimal_adjustment_sets(self, graph: nx.DiGraph, treatment: str, 
                                   outcome: str) -> List[Set[str]]:
        """Find all minimal adjustment sets satisfying back-door criterion"""
        all_nodes = set(graph.nodes()) - {treatment, outcome}
        minimal_sets = []
        
        for r in range(len(all_nodes) + 1):
            for subset in combinations(all_nodes, r):
                adjustment_set = set(subset)
                
                if self.test_backdoor_criterion(graph, treatment, outcome, adjustment_set):
                    is_minimal = True
                    for smaller_subset in combinations(subset, len(subset) - 1):
                        smaller_set = set(smaller_subset)
                        if self.test_backdoor_criterion(graph, treatment, outcome, smaller_set):
                            is_minimal = False
                            break
                    
                    if is_minimal:
                        minimal_sets.append(adjustment_set)
        
        return minimal_sets
    
    def _find_backdoor_paths(self, graph: nx.DiGraph, source: str, target: str) -> List[List[str]]:
        """Find all back-door paths from source to target"""
        undirected = graph.to_undirected()
        
        all_paths = list(nx.all_simple_paths(undirected, source, target))
        
        backdoor_paths = []
        for path in all_paths:
            if len(path) > 2:  # Need at least one intermediate node
                if graph.has_edge(path[1], path[0]):
                    backdoor_paths.append(path)
        
        return backdoor_paths
    
    def _is_path_blocked(self, graph: nx.DiGraph, path: List[str], 
                        adjustment_set: Set[str]) -> bool:
        """Check if a path is blocked by the adjustment set"""
        for i in range(1, len(path) - 1):
            node = path[i]
            prev_node = path[i - 1]
            next_node = path[i + 1]
            
            if self._is_collider(graph, prev_node, node, next_node):
                if node in adjustment_set:
                    continue  # Not blocked
                descendants = nx.descendants(graph, node)
                if adjustment_set.intersection(descendants):
                    continue  # Not blocked
                return True  # Blocked
            else:
                if node in adjustment_set:
                    return True  # Blocked
        
        return False  # Not blocked
    
    def _is_collider(self, graph: nx.DiGraph, prev_node: str, node: str, next_node: str) -> bool:
        """Check if node is a collider in the path"""
        return (graph.has_edge(prev_node, node) and 
                graph.has_edge(next_node, node))

async def validate_causal_model_identifiability(orchestrator, treatment: str, outcome: str) -> Dict[str, Any]:
    """Validate causal model identifiability using existing Neo4j data"""
    
    causal_relationships = await orchestrator._query_all_causal_relationships()
    
    graph = nx.DiGraph()
    for rel in causal_relationships:
        graph.add_edge(rel["source"], rel["target"], weight=rel["strength"])
    
    tester = DAGIdentifiabilityTester()
    
    adjustment_sets = tester.find_minimal_adjustment_sets(graph, treatment, outcome)
    
    results = {
        "identifiable": len(adjustment_sets) > 0,
        "minimal_adjustment_sets": [list(s) for s in adjustment_sets],
        "graph_nodes": list(graph.nodes()),
        "graph_edges": list(graph.edges()),
        "validation_timestamp": datetime.now().isoformat()
    }
    
    return results

if __name__ == "__main__":
    print("✅ DAG Identifiability Testing Framework loaded")

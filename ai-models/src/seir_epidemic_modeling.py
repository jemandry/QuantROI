import asyncio
import logging
import numpy as np
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j driver not available - using mock implementation")

try:
    from .neo4j_spatio_temporal_graph import Neo4jSpatioTemporalGraph, SpatioTemporalNode, TemporalEdge
    SPATIO_TEMPORAL_AVAILABLE = True
except ImportError:
    SPATIO_TEMPORAL_AVAILABLE = False
    logging.warning("Spatio-temporal graph not available - using mock implementation")

@dataclass
class SEIRParameters:
    """Parameters for SEIR epidemic model"""
    beta: float  # Transmission rate
    sigma: float  # Incubation rate (1/incubation period)
    gamma: float  # Recovery rate (1/infectious period)
    population: int  # Total population
    initial_infected: int  # Initial number of infected
    initial_exposed: int = 0  # Initial number of exposed
    initial_recovered: int = 0  # Initial number of recovered
    
    @property
    def initial_susceptible(self) -> int:
        """Calculate initial susceptible population"""
        return self.population - self.initial_infected - self.initial_exposed - self.initial_recovered
    
    @property
    def r0(self) -> float:
        """Calculate basic reproduction number"""
        return self.beta / self.gamma

class SEIREpidemicModel:
    """SEIR epidemic model with Neo4j integration for PAU spatiotemporal modeling"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.neo4j_graph = Neo4jSpatioTemporalGraph() if SPATIO_TEMPORAL_AVAILABLE else None
        
    async def simulate_epidemic(self, 
                              params: SEIRParameters, 
                              days: int = 100, 
                              dt: float = 0.1,
                              location: str = "GLOBAL") -> Dict[str, Any]:
        """
        Simulate SEIR epidemic model and store results in Neo4j
        
        Args:
            params: SEIR model parameters
            days: Number of days to simulate
            dt: Time step in days
            location: Geographic location for spatial analysis
            
        Returns:
            Dictionary with simulation results
        """
        try:
            t = np.linspace(0, days, int(days/dt) + 1)
            S = np.zeros(len(t))
            E = np.zeros(len(t))
            I = np.zeros(len(t))
            R = np.zeros(len(t))
            
            S[0] = params.initial_susceptible
            E[0] = params.initial_exposed
            I[0] = params.initial_infected
            R[0] = params.initial_recovered
            
            for i in range(1, len(t)):
                dSdt = -params.beta * S[i-1] * I[i-1] / params.population
                dEdt = params.beta * S[i-1] * I[i-1] / params.population - params.sigma * E[i-1]
                dIdt = params.sigma * E[i-1] - params.gamma * I[i-1]
                dRdt = params.gamma * I[i-1]
                
                S[i] = S[i-1] + dSdt * dt
                E[i] = E[i-1] + dEdt * dt
                I[i] = I[i-1] + dIdt * dt
                R[i] = R[i-1] + dRdt * dt
            
            if self.neo4j_graph and SPATIO_TEMPORAL_AVAILABLE:
                await self._store_epidemic_in_neo4j(t, S, E, I, R, params, location)
            
            peak_infected = np.max(I)
            peak_day = t[np.argmax(I)]
            total_infected = params.initial_infected + params.initial_exposed + peak_infected
            
            return {
                "time": t.tolist(),
                "susceptible": S.tolist(),
                "exposed": E.tolist(),
                "infected": I.tolist(),
                "recovered": R.tolist(),
                "peak_infected": float(peak_infected),
                "peak_day": float(peak_day),
                "total_infected": float(total_infected),
                "r0": params.r0,
                "neo4j_stored": self.neo4j_graph is not None
            }
            
        except Exception as e:
            self.logger.error(f"Error in SEIR simulation: {e}")
            return {"error": str(e)}
    
    async def _store_epidemic_in_neo4j(self, 
                                     t: np.ndarray, 
                                     S: np.ndarray, 
                                     E: np.ndarray, 
                                     I: np.ndarray, 
                                     R: np.ndarray,
                                     params: SEIRParameters,
                                     location: str) -> bool:
        """Store epidemic simulation results in Neo4j"""
        try:
            epidemic_id = f"epidemic_{int(datetime.now().timestamp())}"
            epidemic_node = SpatioTemporalNode(
                node_id=epidemic_id,
                node_type="epidemic_event",
                timestamp=datetime.now(),
                location=location,
                influence_strength=0.9,
                decay_rate=0.05  # Slower decay for epidemic events
            )
            
            await self.neo4j_graph.add_causal_node(epidemic_node)
            
            sample_indices = np.linspace(0, len(t)-1, min(50, len(t))).astype(int)
            
            for idx in sample_indices:
                day = t[idx]
                time_point = datetime.now() + timedelta(days=float(day))
                
                day_node = SpatioTemporalNode(
                    node_id=f"{epidemic_id}_day_{int(day)}",
                    node_type="epidemic_timepoint",
                    timestamp=time_point,
                    location=location,
                    influence_strength=float(I[idx] / params.population),  # Influence proportional to infected percentage
                    decay_rate=0.1
                )
                
                await self.neo4j_graph.add_causal_node(day_node)
                
                edge = TemporalEdge(
                    source_id=epidemic_id,
                    target_id=f"{epidemic_id}_day_{int(day)}",
                    relationship_type="epidemic_progression",
                    causal_strength=0.9,
                    temporal_lag_minutes=int(day * 24 * 60),  # Convert days to minutes
                    confidence_score=0.95,
                    created_at=datetime.now()
                )
                
                await self.neo4j_graph.add_temporal_edge(edge)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing epidemic in Neo4j: {e}")
            return False
    
    async def analyze_epidemic_impact(self, epidemic_id: str, target_node_id: str) -> Dict[str, Any]:
        """Analyze causal impact of epidemic on target node (e.g., market event)"""
        try:
            if not self.neo4j_graph:
                return {"error": "Neo4j graph not available"}
            
            pathway = await self.neo4j_graph.find_causal_pathway_with_decay(epidemic_id, target_node_id)
            
            if not pathway:
                return {"impact": "none", "confidence": 0.0}
            
            return {
                "impact": "significant" if pathway["pathway_strength"] > 0.5 else "moderate",
                "strength": pathway["pathway_strength"],
                "confidence": pathway["confidence"],
                "lag_minutes": pathway["total_lag_minutes"],
                "pathway": pathway["pathway_nodes"]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing epidemic impact: {e}")
            return {"error": str(e)}

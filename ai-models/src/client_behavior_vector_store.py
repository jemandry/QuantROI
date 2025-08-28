"""
Client Behavior Vector Store using Weaviate for Semantic Profiling
Integrates with AutomatedStrandCreator for behavioral pattern analysis
"""

import asyncio
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    import weaviate
    from sentence_transformers import SentenceTransformer
    WEAVIATE_AVAILABLE = True
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False
    TRANSFORMERS_AVAILABLE = False

@dataclass
class ClientProfile:
    client_id: str
    risk_tolerance: float
    investment_goals: List[str]
    behavioral_patterns: Dict[str, float]
    regime_preferences: Dict[str, float]
    timestamp_ns: int
    confidence_score: float = 1.0

@dataclass
class BehavioralPattern:
    pattern_id: str
    pattern_type: str
    description: str
    frequency: float
    correlation_strength: float
    regime_context: str
    client_segments: List[str]

class ClientBehaviorVectorStore:
    """Weaviate-based vector store for client behavioral analysis"""
    
    def __init__(self, weaviate_url: str, openai_api_key: Optional[str] = None):
        self.weaviate_url = weaviate_url
        self.client = None
        self.embedder = None
        self.logger = logging.getLogger(__name__)
        self.openai_api_key = openai_api_key
        
    async def initialize(self):
        """Initialize Weaviate client and embedding model"""
        if not WEAVIATE_AVAILABLE:
            self.logger.error("Weaviate not available - install weaviate-client")
            return False
            
        try:
            auth_config = None
            if self.openai_api_key:
                auth_config = weaviate.AuthApiKey(api_key=self.openai_api_key)
                
            self.client = weaviate.Client(
                url=self.weaviate_url,
                auth_client_secret=auth_config,
                additional_headers={
                    "X-OpenAI-Api-Key": self.openai_api_key
                } if self.openai_api_key else None
            )
            
            if TRANSFORMERS_AVAILABLE:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            
            await self._setup_schema()
            self.logger.info("ClientBehaviorVectorStore initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            return False
    
    async def _setup_schema(self):
        """Create optimized schema for client behavior storage"""
        client_schema = {
            "class": "ClientProfile",
            "description": "Client profiles for behavioral analysis",
            "vectorIndexType": "hnsw",
            "vectorIndexConfig": {
                "maxConnections": 64,
                "efConstruction": 128,
                "ef": 64,
                "cleanupIntervalSeconds": 300
            },
            "properties": [
                {
                    "name": "client_id",
                    "dataType": ["string"],
                    "description": "Unique client identifier"
                },
                {
                    "name": "risk_tolerance",
                    "dataType": ["number"],
                    "description": "Client risk tolerance score (0-1)"
                },
                {
                    "name": "investment_goals",
                    "dataType": ["text[]"],
                    "description": "List of investment goals"
                },
                {
                    "name": "behavioral_summary",
                    "dataType": ["text"],
                    "description": "Behavioral pattern summary for semantic search"
                },
                {
                    "name": "regime_preferences",
                    "dataType": ["object"],
                    "description": "Preferences by market regime"
                },
                {
                    "name": "timestamp_ns",
                    "dataType": ["number"],
                    "description": "Profile timestamp in nanoseconds"
                },
                {
                    "name": "confidence_score",
                    "dataType": ["number"],
                    "description": "Confidence in profile accuracy"
                }
            ]
        }
        
        pattern_schema = {
            "class": "BehavioralPattern",
            "description": "Behavioral patterns for client segmentation",
            "vectorIndexType": "hnsw",
            "vectorIndexConfig": {
                "maxConnections": 32,
                "efConstruction": 64,
                "ef": 32
            },
            "properties": [
                {
                    "name": "pattern_id",
                    "dataType": ["string"],
                    "description": "Unique pattern identifier"
                },
                {
                    "name": "pattern_type",
                    "dataType": ["string"],
                    "description": "Type of behavioral pattern"
                },
                {
                    "name": "description",
                    "dataType": ["text"],
                    "description": "Pattern description for semantic search"
                },
                {
                    "name": "frequency",
                    "dataType": ["number"],
                    "description": "Pattern occurrence frequency"
                },
                {
                    "name": "correlation_strength",
                    "dataType": ["number"],
                    "description": "Correlation with market outcomes"
                },
                {
                    "name": "regime_context",
                    "dataType": ["string"],
                    "description": "Market regime context"
                },
                {
                    "name": "client_segments",
                    "dataType": ["string[]"],
                    "description": "Applicable client segments"
                }
            ]
        }
        
        try:
            if not self.client.schema.exists("ClientProfile"):
                self.client.schema.create_class(client_schema)
                self.logger.info("Created ClientProfile schema")
                
            if not self.client.schema.exists("BehavioralPattern"):
                self.client.schema.create_class(pattern_schema)
                self.logger.info("Created BehavioralPattern schema")
                
        except Exception as e:
            self.logger.error(f"Schema creation failed: {e}")
    
    async def store_client_profile(self, profile: ClientProfile) -> str:
        """Store client profile with auto-generated embedding"""
        if not self.client or not self.embedder:
            self.logger.error("Vector store not initialized")
            return None
            
        try:
            behavioral_summary = self._create_behavioral_summary(profile)
            
            embedding = self.embedder.encode(behavioral_summary).tolist()
            
            profile_object = {
                "client_id": profile.client_id,
                "risk_tolerance": profile.risk_tolerance,
                "investment_goals": profile.investment_goals,
                "behavioral_summary": behavioral_summary,
                "regime_preferences": profile.regime_preferences,
                "timestamp_ns": profile.timestamp_ns,
                "confidence_score": profile.confidence_score
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.data_object.create(
                    profile_object,
                    "ClientProfile",
                    vector=embedding
                )
            )
            
            self.logger.debug(f"Stored client profile: {profile.client_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to store client profile: {e}")
            return None
    
    def _create_behavioral_summary(self, profile: ClientProfile) -> str:
        """Create textual summary for semantic embedding"""
        goals_text = ", ".join(profile.investment_goals)
        
        behavioral_text = []
        for pattern, strength in profile.behavioral_patterns.items():
            if strength > 0.5:
                behavioral_text.append(f"{pattern} (strong)")
            elif strength > 0.3:
                behavioral_text.append(f"{pattern} (moderate)")
        
        regime_text = []
        for regime, preference in profile.regime_preferences.items():
            if preference > 0.6:
                regime_text.append(f"prefers {regime}")
            elif preference < 0.4:
                regime_text.append(f"avoids {regime}")
        
        summary = f"Risk tolerance: {profile.risk_tolerance:.2f}. "
        summary += f"Goals: {goals_text}. "
        if behavioral_text:
            summary += f"Behaviors: {', '.join(behavioral_text)}. "
        if regime_text:
            summary += f"Market preferences: {', '.join(regime_text)}."
            
        return summary
    
    async def find_similar_clients(self, query_profile: ClientProfile, limit: int = 10) -> List[Dict[str, Any]]:
        """Find clients with similar behavioral patterns"""
        if not self.client or not self.embedder:
            return []
            
        try:
            behavioral_summary = self._create_behavioral_summary(query_profile)
            query_embedding = self.embedder.encode(behavioral_summary).tolist()
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.client.query.get("ClientProfile", [
                    "client_id", "risk_tolerance", "investment_goals", 
                    "behavioral_summary", "regime_preferences", "confidence_score"
                ]).with_near_vector({
                    "vector": query_embedding,
                    "certainty": 0.7
                }).with_limit(limit).do()
            )
            
            return results.get('data', {}).get('Get', {}).get('ClientProfile', [])
            
        except Exception as e:
            self.logger.error(f"Similar client search failed: {e}")
            return []
    
    async def store_behavioral_pattern(self, pattern: BehavioralPattern) -> str:
        """Store behavioral pattern for client segmentation"""
        if not self.client or not self.embedder:
            return None
            
        try:
            embedding = self.embedder.encode(pattern.description).tolist()
            
            pattern_object = {
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type,
                "description": pattern.description,
                "frequency": pattern.frequency,
                "correlation_strength": pattern.correlation_strength,
                "regime_context": pattern.regime_context,
                "client_segments": pattern.client_segments
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.data_object.create(
                    pattern_object,
                    "BehavioralPattern",
                    vector=embedding
                )
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to store behavioral pattern: {e}")
            return None
    
    async def search_patterns_by_regime(self, regime: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search behavioral patterns by market regime"""
        if not self.client:
            return []
            
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.client.query.get("BehavioralPattern", [
                    "pattern_id", "pattern_type", "description", 
                    "frequency", "correlation_strength", "client_segments"
                ]).with_where({
                    "path": ["regime_context"],
                    "operator": "Equal",
                    "valueString": regime
                }).with_limit(limit).do()
            )
            
            return results.get('data', {}).get('Get', {}).get('BehavioralPattern', [])
            
        except Exception as e:
            self.logger.error(f"Pattern search by regime failed: {e}")
            return []
    
    async def get_client_recommendations(self, client_id: str, current_regime: str) -> Dict[str, Any]:
        """Get personalized recommendations based on client profile and current regime"""
        try:
            loop = asyncio.get_event_loop()
            client_results = await loop.run_in_executor(
                None,
                lambda: self.client.query.get("ClientProfile", [
                    "client_id", "risk_tolerance", "investment_goals",
                    "regime_preferences", "behavioral_summary"
                ]).with_where({
                    "path": ["client_id"],
                    "operator": "Equal", 
                    "valueString": client_id
                }).with_limit(1).do()
            )
            
            profiles = client_results.get('data', {}).get('Get', {}).get('ClientProfile', [])
            if not profiles:
                return {"error": "Client profile not found"}
            
            profile = profiles[0]
            
            patterns = await self.search_patterns_by_regime(current_regime)
            
            recommendations = {
                "client_id": client_id,
                "current_regime": current_regime,
                "risk_tolerance": profile.get("risk_tolerance", 0.5),
                "regime_preference": profile.get("regime_preferences", {}).get(current_regime, 0.5),
                "applicable_patterns": [],
                "recommendations": []
            }
            
            for pattern in patterns:
                if pattern.get("correlation_strength", 0) > 0.6:
                    recommendations["applicable_patterns"].append({
                        "pattern_type": pattern.get("pattern_type"),
                        "description": pattern.get("description"),
                        "frequency": pattern.get("frequency")
                    })
            
            risk_tolerance = profile.get("risk_tolerance", 0.5)
            if risk_tolerance > 0.7:
                recommendations["recommendations"].append("Consider aggressive growth strategies")
            elif risk_tolerance < 0.3:
                recommendations["recommendations"].append("Focus on capital preservation")
            else:
                recommendations["recommendations"].append("Balanced approach recommended")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to get client recommendations: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.logger.info("ClientBehaviorVectorStore cleanup completed")
    
    def get_store_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.client:
            return {"error": "Store not initialized"}
            
        try:
            client_count = self.client.query.aggregate("ClientProfile").with_meta_count().do()
            pattern_count = self.client.query.aggregate("BehavioralPattern").with_meta_count().do()
            
            return {
                "client_profiles": client_count.get('data', {}).get('Aggregate', {}).get('ClientProfile', [{}])[0].get('meta', {}).get('count', 0),
                "behavioral_patterns": pattern_count.get('data', {}).get('Aggregate', {}).get('BehavioralPattern', [{}])[0].get('meta', {}).get('count', 0),
                "store_url": self.weaviate_url,
                "embedder_model": "all-MiniLM-L6-v2" if self.embedder else "none"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get store statistics: {e}")
            return {"error": str(e)}

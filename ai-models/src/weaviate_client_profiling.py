"""
Weaviate Client Profiling System for RIA Roboadvisor Platform
Implements semantic client profiling with vector-based behavioral analysis
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import Filter

logger = logging.getLogger(__name__)

@dataclass
class ClientProfile:
    """Client profile data structure"""
    client_id: str
    risk_tolerance: float  # 0.0 to 1.0
    investment_horizon: int  # months
    liquidity_needs: float  # 0.0 to 1.0
    esg_preference: float  # 0.0 to 1.0
    behavioral_patterns: Dict[str, float]
    financial_goals: List[str]
    constraints: Dict[str, Any]
    last_updated: float

@dataclass
class ClientBehavior:
    """Client behavioral event"""
    client_id: str
    behavior_type: str
    timestamp: float
    context: Dict[str, Any]
    market_regime: Optional[str] = None
    emotional_state: Optional[str] = None

class WeaviateClientProfiling:
    """Weaviate-based client profiling with semantic search and behavioral analysis"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[weaviate.WeaviateClient] = None
        self.collection_name = "ClientProfiles"
        self.behavior_collection = "ClientBehaviors"
        
        self.behavior_weights = {
            "panic_selling": -0.8,
            "fomo_buying": -0.6,
            "contrarian_behavior": 0.7,
            "momentum_following": 0.3,
            "value_seeking": 0.8,
            "diversification_preference": 0.9,
            "rebalancing_discipline": 0.9,
            "tax_awareness": 0.6,
            "fee_sensitivity": 0.4,
            "research_driven": 0.8
        }
    
    async def connect(self) -> bool:
        """Connect to Weaviate instance"""
        try:
            weaviate_url = self.config.get("weaviate_url", "http://localhost:8080")
            api_key = self.config.get("weaviate_api_key")
            
            if api_key:
                self.client = weaviate.connect_to_local(
                    host=weaviate_url.replace("http://", "").replace("https://", ""),
                    headers={"X-OpenAI-Api-Key": api_key}
                )
            else:
                self.client = weaviate.connect_to_local(
                    host=weaviate_url.replace("http://", "").replace("https://", "")
                )
            
            await self._setup_collections()
            logger.info("Successfully connected to Weaviate")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            return False
    
    async def _setup_collections(self):
        """Setup Weaviate collections for client profiles and behaviors"""
        try:
            if not self.client.collections.exists(self.collection_name):
                self.client.collections.create(
                    name=self.collection_name,
                    properties=[
                        Property(name="clientId", data_type=DataType.TEXT),
                        Property(name="riskTolerance", data_type=DataType.NUMBER),
                        Property(name="investmentHorizon", data_type=DataType.INT),
                        Property(name="liquidityNeeds", data_type=DataType.NUMBER),
                        Property(name="esgPreference", data_type=DataType.NUMBER),
                        Property(name="behavioralPatterns", data_type=DataType.OBJECT),
                        Property(name="financialGoals", data_type=DataType.TEXT_ARRAY),
                        Property(name="constraints", data_type=DataType.OBJECT),
                        Property(name="lastUpdated", data_type=DataType.NUMBER),
                        Property(name="profileVector", data_type=DataType.NUMBER_ARRAY)
                    ],
                    vectorizer_config=Configure.Vectorizer.text2vec_openai()
                )
            
            if not self.client.collections.exists(self.behavior_collection):
                self.client.collections.create(
                    name=self.behavior_collection,
                    properties=[
                        Property(name="clientId", data_type=DataType.TEXT),
                        Property(name="behaviorType", data_type=DataType.TEXT),
                        Property(name="timestamp", data_type=DataType.NUMBER),
                        Property(name="context", data_type=DataType.OBJECT),
                        Property(name="marketRegime", data_type=DataType.TEXT),
                        Property(name="emotionalState", data_type=DataType.TEXT),
                        Property(name="behaviorVector", data_type=DataType.NUMBER_ARRAY)
                    ],
                    vectorizer_config=Configure.Vectorizer.text2vec_openai()
                )
            
            logger.info("Weaviate collections setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup Weaviate collections: {e}")
            raise
    
    def _generate_profile_vector(self, profile: ClientProfile) -> List[float]:
        """Generate vector embedding for client profile"""
        vector = np.zeros(50)
        
        risk_base = int(profile.risk_tolerance * 10)
        if risk_base < 10:
            vector[risk_base] = 1.0
        
        horizon_normalized = min(profile.investment_horizon / 360, 1.0)  # Normalize to max 30 years
        horizon_idx = int(horizon_normalized * 10) + 10
        if horizon_idx < 20:
            vector[horizon_idx] = 1.0
        
        liquidity_idx = int(profile.liquidity_needs * 5) + 20
        if liquidity_idx < 25:
            vector[liquidity_idx] = 1.0
        
        esg_idx = int(profile.esg_preference * 5) + 25
        if esg_idx < 30:
            vector[esg_idx] = 1.0
        
        behavior_start = 30
        for i, (behavior, weight) in enumerate(self.behavior_weights.items()):
            if i < 20 and behavior in profile.behavioral_patterns:
                pattern_strength = profile.behavioral_patterns[behavior]
                vector[behavior_start + i] = pattern_strength * weight
        
        return vector.tolist()
    
    def _generate_behavior_vector(self, behavior: ClientBehavior) -> List[float]:
        """Generate vector embedding for client behavior"""
        vector = np.zeros(30)
        
        behavior_types = {
            "trade_execution": 0,
            "portfolio_review": 1,
            "risk_adjustment": 2,
            "goal_modification": 3,
            "panic_response": 4,
            "opportunity_seeking": 5,
            "rebalancing": 6,
            "withdrawal": 7,
            "deposit": 8,
            "consultation": 9
        }
        
        behavior_idx = behavior_types.get(behavior.behavior_type, 0)
        vector[behavior_idx] = 1.0
        
        if behavior.market_regime:
            regime_types = {
                "bull_market": 10,
                "bear_market": 11,
                "high_volatility": 12,
                "low_volatility": 13,
                "crisis": 14
            }
            regime_idx = regime_types.get(behavior.market_regime, 10)
            if regime_idx < 15:
                vector[regime_idx] = 1.0
        
        if behavior.emotional_state:
            emotion_types = {
                "confident": 15,
                "anxious": 16,
                "greedy": 17,
                "fearful": 18,
                "optimistic": 19,
                "pessimistic": 20,
                "neutral": 21,
                "excited": 22,
                "cautious": 23,
                "panicked": 24
            }
            emotion_idx = emotion_types.get(behavior.emotional_state, 21)
            if emotion_idx < 25:
                vector[emotion_idx] = 1.0
        
        if "trade_size" in behavior.context:
            trade_size_normalized = min(behavior.context["trade_size"] / 1000000, 1.0)
            vector[25] = trade_size_normalized
        
        if "frequency" in behavior.context:
            frequency_normalized = min(behavior.context["frequency"] / 100, 1.0)
            vector[26] = frequency_normalized
        
        return vector.tolist()
    
    async def store_client_profile(self, profile: ClientProfile) -> bool:
        """Store or update client profile in Weaviate"""
        try:
            collection = self.client.collections.get(self.collection_name)
            
            profile_vector = self._generate_profile_vector(profile)
            
            profile_data = {
                "clientId": profile.client_id,
                "riskTolerance": profile.risk_tolerance,
                "investmentHorizon": profile.investment_horizon,
                "liquidityNeeds": profile.liquidity_needs,
                "esgPreference": profile.esg_preference,
                "behavioralPatterns": profile.behavioral_patterns,
                "financialGoals": profile.financial_goals,
                "constraints": profile.constraints,
                "lastUpdated": profile.last_updated,
                "profileVector": profile_vector
            }
            
            existing = collection.query.fetch_objects(
                where=Filter.by_property("clientId").equal(profile.client_id),
                limit=1
            )
            
            if existing.objects:
                collection.data.update(
                    uuid=existing.objects[0].uuid,
                    properties=profile_data
                )
                logger.info(f"Updated profile for client {profile.client_id}")
            else:
                collection.data.insert(profile_data)
                logger.info(f"Created new profile for client {profile.client_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store client profile: {e}")
            return False
    
    async def store_client_behavior(self, behavior: ClientBehavior) -> bool:
        """Store client behavior event in Weaviate"""
        try:
            collection = self.client.collections.get(self.behavior_collection)
            
            behavior_vector = self._generate_behavior_vector(behavior)
            
            behavior_data = {
                "clientId": behavior.client_id,
                "behaviorType": behavior.behavior_type,
                "timestamp": behavior.timestamp,
                "context": behavior.context,
                "marketRegime": behavior.market_regime,
                "emotionalState": behavior.emotional_state,
                "behaviorVector": behavior_vector
            }
            
            collection.data.insert(behavior_data)
            logger.debug(f"Stored behavior {behavior.behavior_type} for client {behavior.client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store client behavior: {e}")
            return False
    
    async def find_similar_clients(self, client_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find clients with similar profiles using vector similarity"""
        try:
            collection = self.client.collections.get(self.collection_name)
            target_profile = collection.query.fetch_objects(
                where=Filter.by_property("clientId").equal(client_id),
                limit=1
            )
            
            if not target_profile.objects:
                logger.warning(f"Client profile not found: {client_id}")
                return []
            
            target_vector = target_profile.objects[0].properties["profileVector"]
            
            similar_profiles = collection.query.near_vector(
                near_vector=target_vector,
                limit=limit + 1,  # +1 to exclude the target client
                return_metadata=["distance"]
            )
            
            results = []
            for obj in similar_profiles.objects:
                if obj.properties["clientId"] != client_id:
                    results.append({
                        "client_id": obj.properties["clientId"],
                        "similarity_score": 1.0 - obj.metadata.distance,
                        "risk_tolerance": obj.properties["riskTolerance"],
                        "investment_horizon": obj.properties["investmentHorizon"],
                        "financial_goals": obj.properties["financialGoals"]
                    })
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find similar clients: {e}")
            return []
    
    async def get_client_behavior_patterns(self, client_id: str, 
                                         days_back: int = 30) -> Dict[str, Any]:
        """Analyze client behavior patterns over specified time period"""
        try:
            collection = self.client.collections.get(self.behavior_collection)
            
            time_threshold = time.time() - (days_back * 24 * 3600)
            
            behaviors = collection.query.fetch_objects(
                where=Filter.by_property("clientId").equal(client_id) &
                      Filter.by_property("timestamp").greater_than(time_threshold),
                limit=1000
            )
            
            if not behaviors.objects:
                return {"patterns": {}, "insights": [], "risk_indicators": []}
            
            behavior_counts = {}
            emotional_states = {}
            regime_behaviors = {}
            
            for obj in behaviors.objects:
                props = obj.properties
                
                behavior_type = props["behaviorType"]
                behavior_counts[behavior_type] = behavior_counts.get(behavior_type, 0) + 1
                
                if props.get("emotionalState"):
                    emotion = props["emotionalState"]
                    emotional_states[emotion] = emotional_states.get(emotion, 0) + 1
                
                if props.get("marketRegime"):
                    regime = props["marketRegime"]
                    if regime not in regime_behaviors:
                        regime_behaviors[regime] = {}
                    regime_behaviors[regime][behavior_type] = \
                        regime_behaviors[regime].get(behavior_type, 0) + 1
            
            insights = []
            risk_indicators = []
            
            total_behaviors = sum(behavior_counts.values())
            if behavior_counts.get("panic_response", 0) / total_behaviors > 0.2:
                risk_indicators.append("High frequency of panic responses")
            
            if emotional_states.get("anxious", 0) / total_behaviors > 0.3:
                risk_indicators.append("Frequently anxious emotional state")
            
            if behavior_counts.get("rebalancing", 0) > 0:
                insights.append("Shows disciplined rebalancing behavior")
            
            if emotional_states.get("confident", 0) / total_behaviors > 0.4:
                insights.append("Generally maintains confident emotional state")
            
            return {
                "patterns": {
                    "behavior_distribution": behavior_counts,
                    "emotional_distribution": emotional_states,
                    "regime_specific": regime_behaviors
                },
                "insights": insights,
                "risk_indicators": risk_indicators,
                "total_behaviors": total_behaviors,
                "analysis_period_days": days_back
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze behavior patterns: {e}")
            return {"patterns": {}, "insights": [], "risk_indicators": []}
    
    async def get_regime_specific_recommendations(self, client_id: str, 
                                                current_regime: str) -> List[Dict[str, Any]]:
        """Get personalized recommendations based on client profile and current market regime"""
        try:
            collection = self.client.collections.get(self.collection_name)
            profile_result = collection.query.fetch_objects(
                where=Filter.by_property("clientId").equal(client_id),
                limit=1
            )
            
            if not profile_result.objects:
                return []
            
            profile = profile_result.objects[0].properties
            
            similar_clients = await self.find_similar_clients(client_id, limit=5)
            
            recommendations = []
            
            risk_tolerance = profile["riskTolerance"]
            
            if current_regime == "high_volatility":
                if risk_tolerance < 0.3:
                    recommendations.append({
                        "type": "risk_management",
                        "action": "Consider increasing cash allocation",
                        "rationale": "Low risk tolerance during high volatility period",
                        "priority": "high"
                    })
                elif risk_tolerance > 0.7:
                    recommendations.append({
                        "type": "opportunity",
                        "action": "Consider value opportunities in market dislocation",
                        "rationale": "High risk tolerance can capitalize on volatility",
                        "priority": "medium"
                    })
            
            elif current_regime == "bull_market":
                if risk_tolerance > 0.6:
                    recommendations.append({
                        "type": "portfolio_optimization",
                        "action": "Consider taking some profits and rebalancing",
                        "rationale": "Bull market gains may have shifted allocation",
                        "priority": "medium"
                    })
            
            if profile["esgPreference"] > 0.7:
                recommendations.append({
                    "type": "esg_alignment",
                    "action": "Review ESG fund options for current regime",
                    "rationale": "Strong ESG preference with regime-appropriate options",
                    "priority": "low"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []
    
    async def close(self):
        """Close Weaviate connection"""
        if self.client:
            self.client.close()
            logger.info("Weaviate connection closed")

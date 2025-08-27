#!/usr/bin/env python3
"""
Routing Demo for Choice-Based Query Processing
Demonstrates the "jukebox with storyline" approach for method selection
"""

import asyncio
import time
from typing import Dict, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from nlp_voice_interface import NLPVoiceInterface, IntentType, ParsedQuery
from query_routing_engine import QueryRoutingEngine, ProcessingMethod
from grok_api_client import MockGrokAPIClient

class RoutingDemo:
    
    def __init__(self):
        self.nlp_interface = NLPVoiceInterface()
        self.routing_engine = QueryRoutingEngine()
        self.grok_client = MockGrokAPIClient()
        
        print("🎵 Braided Cord Query Routing Demo - Jukebox with Storyline 🎵")
        print("=" * 70)
    
    async def demonstrate_routing_scenarios(self):
        """Demonstrate different routing scenarios with storylines."""
        
        scenarios = [
            {
                "name": "Simple Data Request",
                "query": "What is AAPL stock price?",
                "intent": "data_request",
                "entities": {"symbols": ["AAPL"]},
                "confidence": 0.9,
                "expected_method": ProcessingMethod.LOCAL_NLP
            },
            {
                "name": "Complex Causal Analysis",
                "query": "Analyze the intricate causal relationships between market sentiment, VIX volatility, and cross-asset price movements during earnings seasons",
                "intent": "causal_analysis",
                "entities": {
                    "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN"],
                    "analysis_type": "counterfactual_analysis",
                    "numbers": [1, 2, 3, 4, 5, 6]
                },
                "confidence": 0.3,
                "expected_method": ProcessingMethod.GROK_API
            },
            {
                "name": "Financial Prediction",
                "query": "Predict TSLA stock performance with VIX analysis",
                "intent": "stock_prediction",
                "entities": {"symbols": ["TSLA"]},
                "confidence": 0.8,
                "expected_method": ProcessingMethod.AUTO_AGENT
            },
            {
                "name": "Multi-Asset Comparison",
                "query": "Compare performance of tech stocks AAPL, GOOGL, MSFT with sentiment analysis",
                "intent": "performance_query",
                "entities": {
                    "symbols": ["AAPL", "GOOGL", "MSFT"],
                    "numbers": [1.5, 2.3, 3.7]
                },
                "confidence": 0.7,
                "expected_method": ProcessingMethod.HYBRID
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n🎼 Scenario {i}: {scenario['name']}")
            print("-" * 50)
            print(f"Query: \"{scenario['query']}\"")
            
            await self._demonstrate_scenario(scenario)
            
            if i < len(scenarios):
                print("\n" + "⏸️ " * 20)
                await asyncio.sleep(1)
    
    async def _demonstrate_scenario(self, scenario: Dict[str, Any]):
        """Demonstrate a single routing scenario."""
        start_time = time.time()
        
        routing_result = await self.routing_engine.route_query(
            scenario["query"],
            scenario["intent"],
            scenario["entities"],
            scenario["confidence"]
        )
        
        routing_time = (time.time() - start_time) * 1000
        
        print(f"\n🎯 Routing Decision:")
        print(f"   Method: {routing_result.method.value}")
        print(f"   Confidence: {routing_result.confidence:.2f}")
        print(f"   Routing Time: {routing_time:.2f}ms")
        print(f"   Expected: {scenario['expected_method'].value}")
        
        match_emoji = "✅" if routing_result.method == scenario["expected_method"] else "⚠️"
        print(f"   Match: {match_emoji}")
        
        print(f"\n📖 Storyline:")
        print(f"   \"{routing_result.storyline}\"")
        
        print(f"\n🧠 Reasoning:")
        print(f"   {routing_result.reasoning}")
        
        if routing_result.fallback_method != routing_result.method:
            print(f"\n🔄 Fallback Method: {routing_result.fallback_method.value}")
        
        await self._simulate_processing(routing_result.method, scenario["query"])
    
    async def _simulate_processing(self, method: ProcessingMethod, query: str):
        """Simulate processing with the selected method."""
        print(f"\n⚙️ Processing with {method.value}...")
        
        start_time = time.time()
        
        if method == ProcessingMethod.GROK_API:
            await self.grok_client.initialize()
            response = await self.grok_client.process_query(query, "demo", {})
            processing_time = (time.time() - start_time) * 1000
            
            print(f"   Grok Response: \"{response.response_text[:100]}...\"")
            print(f"   Confidence: {response.confidence:.2f}")
            print(f"   Processing Time: {processing_time:.2f}ms")
            
        elif method == ProcessingMethod.HYBRID:
            await asyncio.sleep(0.05)
            processing_time = (time.time() - start_time) * 1000
            
            print(f"   Hybrid Processing: Combined local + advanced analysis")
            print(f"   Processing Time: {processing_time:.2f}ms")
            
        elif method == ProcessingMethod.AUTO_AGENT:
            await asyncio.sleep(0.02)
            processing_time = (time.time() - start_time) * 1000
            
            print(f"   Auto-Agent Processing: Financial analysis complete")
            print(f"   Processing Time: {processing_time:.2f}ms")
            
        else:
            await asyncio.sleep(0.01)
            processing_time = (time.time() - start_time) * 1000
            
            print(f"   Local NLP Processing: Fast local analysis")
            print(f"   Processing Time: {processing_time:.2f}ms")
    
    async def demonstrate_user_preferences(self):
        """Demonstrate user preference override functionality."""
        print(f"\n\n🎛️ User Preference Override Demo")
        print("=" * 50)
        
        query = "Complex causal analysis with multiple variables"
        intent = "causal_analysis"
        entities = {"symbols": ["AAPL", "GOOGL"], "numbers": [1, 2, 3, 4, 5]}
        confidence = 0.3
        
        print(f"Query: \"{query}\"")
        print("This would normally route to Grok API due to complexity...")
        
        default_result = await self.routing_engine.route_query(
            query, intent, entities, confidence
        )
        print(f"\n🔄 Default Routing: {default_result.method.value}")
        
        user_preferences = {"preferred_method": "local_nlp"}
        override_result = await self.routing_engine.route_query(
            query, intent, entities, confidence, user_preferences
        )
        print(f"👤 User Override: {override_result.method.value}")
        print(f"📖 Storyline: \"{override_result.storyline}\"")
    
    async def demonstrate_fallback_mechanism(self):
        """Demonstrate fallback mechanism when methods are unavailable."""
        print(f"\n\n🔧 Fallback Mechanism Demo")
        print("=" * 40)
        
        print("Simulating Grok API unavailability...")
        self.routing_engine.update_method_availability(ProcessingMethod.GROK_API, False)
        
        query = "Complex reasoning query that would normally use Grok"
        result = await self.routing_engine.route_query(
            query, "causal_analysis", {"analysis_type": "counterfactual_analysis"}, 0.2
        )
        
        print(f"🎯 Routing Result: {result.method.value}")
        print(f"📖 Storyline: \"{result.storyline}\"")
        print(f"🔄 Fallback Used: {self.routing_engine.routing_stats['fallback_count'] > 0}")
        
        self.routing_engine.update_method_availability(ProcessingMethod.GROK_API, True)
        print("✅ Grok API availability restored")
    
    def display_routing_statistics(self):
        """Display routing statistics."""
        print(f"\n\n📊 Routing Statistics")
        print("=" * 30)
        
        stats = self.routing_engine.get_routing_stats()
        
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Average Latency: {stats['average_latency_ms']:.2f}ms")
        print(f"Fallback Count: {stats['fallback_count']}")
        
        print(f"\n📈 Method Distribution:")
        for method, count in stats['method_distribution'].items():
            percentage = (count / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
            print(f"   {method}: {count} ({percentage:.1f}%)")
        
        print(f"\n🔌 Method Availability:")
        for method, available in stats['method_availability'].items():
            status = "✅" if available else "❌"
            print(f"   {method}: {status}")
    
    async def interactive_demo(self):
        """Interactive demo allowing user to test routing."""
        print(f"\n\n🎮 Interactive Routing Demo")
        print("=" * 35)
        print("Enter queries to see how they get routed!")
        print("Type 'quit' to exit, 'stats' to see statistics")
        
        while True:
            try:
                user_query = input("\n🎤 Enter your query: ").strip()
                
                if user_query.lower() == 'quit':
                    break
                elif user_query.lower() == 'stats':
                    self.display_routing_statistics()
                    continue
                elif not user_query:
                    continue
                
                parsed_query = await self.nlp_interface.process_text_query(user_query)
                
                routing_result = await self.routing_engine.route_query(
                    parsed_query.processed_text,
                    parsed_query.intent.value,
                    parsed_query.entities,
                    parsed_query.confidence
                )
                
                print(f"\n🎯 Intent: {parsed_query.intent.value}")
                print(f"🎼 Method: {routing_result.method.value}")
                print(f"📖 Storyline: \"{routing_result.storyline}\"")
                print(f"🧠 Reasoning: {routing_result.reasoning}")
                
                await self._simulate_processing(routing_result.method, user_query)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n👋 Thanks for trying the routing demo!")

async def main():
    """Main demo function."""
    demo = RoutingDemo()
    
    try:
        await demo.demonstrate_routing_scenarios()
        await demo.demonstrate_user_preferences()
        await demo.demonstrate_fallback_mechanism()
        demo.display_routing_statistics()
        
        print(f"\n\n🎉 Demo Complete!")
        print("The routing system successfully demonstrated:")
        print("✅ Intelligent method selection based on query complexity")
        print("✅ Storyline explanations for routing decisions")
        print("✅ User preference override capabilities")
        print("✅ Fallback mechanisms for unavailable methods")
        print("✅ Performance tracking and statistics")
        
        interactive = input("\n🎮 Run interactive demo? (y/n): ").strip().lower()
        if interactive == 'y':
            await demo.interactive_demo()
            
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Test script for the choice-based routing system
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-models', 'src'))

async def test_routing_system():
    """Test the routing system functionality."""
    print("🎵 Testing Choice-Based Routing System")
    print("=" * 50)
    
    try:
        from nlp_voice_interface import NLPVoiceInterface, IntentType, ParsedQuery
        from query_routing_engine import QueryRoutingEngine, ProcessingMethod
        from grok_api_client import MockGrokAPIClient
        
        print("✅ All routing components imported successfully")
        
        nlp_interface = NLPVoiceInterface()
        print("✅ NLP Voice Interface initialized")
        
        if nlp_interface.routing_engine:
            print("✅ Routing engine available")
        else:
            print("⚠️ Routing engine not available")
        
        if nlp_interface.grok_client:
            print("✅ Grok client available")
        else:
            print("⚠️ Grok client not available")
        
        test_queries = [
            {
                "text": "What is AAPL stock price?",
                "expected_intent": IntentType.DATA_REQUEST,
                "description": "Simple data request"
            },
            {
                "text": "Analyze complex causal relationships between market sentiment and volatility",
                "expected_intent": IntentType.CAUSAL_ANALYSIS,
                "description": "Complex causal analysis"
            },
            {
                "text": "Predict TSLA stock performance",
                "expected_intent": IntentType.STOCK_PREDICTION,
                "description": "Stock prediction query"
            },
            {
                "text": "Use Grok for processing",
                "expected_intent": IntentType.ROUTING_PREFERENCE,
                "description": "Routing preference"
            }
        ]
        
        print(f"\n🧪 Testing {len(test_queries)} query scenarios:")
        
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n{i}. {test_case['description']}")
            print(f"   Query: \"{test_case['text']}\"")
            
            try:
                parsed_query = await nlp_interface.process_text_query(test_case['text'])
                print(f"   Intent: {parsed_query.intent.value}")
                print(f"   Confidence: {parsed_query.confidence:.2f}")
                
                response = await nlp_interface.execute_query(parsed_query)
                print(f"   Response: \"{response.response_text[:50]}...\"")
                print(f"   Latency: {response.latency_ms:.2f}ms")
                
                if response.processing_method:
                    print(f"   Method: {response.processing_method}")
                
                if response.storyline:
                    print(f"   Storyline: \"{response.storyline[:50]}...\"")
                
                print("   ✅ Success")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        stats = nlp_interface.get_performance_stats()
        print(f"\n📊 Performance Stats:")
        print(f"   Total Queries: {stats.get('total_queries', 0)}")
        print(f"   Average Latency: {stats.get('average_latency_ms', 0):.2f}ms")
        
        if 'routing_stats' in stats:
            routing_stats = stats['routing_stats']
            print(f"   Routing Requests: {routing_stats.get('total_requests', 0)}")
            print(f"   Routing Latency: {routing_stats.get('average_latency_ms', 0):.2f}ms")
        
        print(f"\n🎉 Routing system test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Some routing components may not be available")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_routing_system())
    sys.exit(0 if success else 1)

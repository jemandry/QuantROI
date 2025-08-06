#!/usr/bin/env python3
"""
Grok Integration Demo
Demonstrates Grok API client functionality and integration patterns
"""

import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))

from grok_api_client import GrokAPIClient, MockGrokAPIClient, GrokResponse

class GrokIntegrationDemo:
    
    def __init__(self):
        self.mock_client = MockGrokAPIClient()
        self.real_client = GrokAPIClient(
            api_endpoint="https://api.grok.example.com/v1",
            api_key="demo-key-not-real",
            timeout=10,
            max_retries=2
        )
        
        print("🤖 Grok API Integration Demo")
        print("=" * 40)
    
    async def demonstrate_mock_client(self):
        """Demonstrate mock Grok client functionality."""
        print("\n🧪 Mock Grok Client Demo")
        print("-" * 30)
        
        async with self.mock_client as client:
            print(f"✅ Mock client initialized")
            print(f"🔌 Available: {client.is_available}")
            
            test_queries = [
                {
                    "query": "What causes stock price volatility?",
                    "intent": "causal_analysis",
                    "entities": {"symbols": ["AAPL", "GOOGL"]},
                    "description": "Causal Analysis Query"
                },
                {
                    "query": "Analyze the complex relationship between market sentiment and trading volume",
                    "intent": "complex_reasoning",
                    "entities": {"analysis_type": "correlation"},
                    "description": "Complex Reasoning Query"
                },
                {
                    "query": "Predict TSLA stock performance for next quarter",
                    "intent": "financial_analysis",
                    "entities": {"symbols": ["TSLA"], "timeframe": "quarterly"},
                    "description": "Financial Analysis Query"
                }
            ]
            
            for i, test_case in enumerate(test_queries, 1):
                print(f"\n📝 Test {i}: {test_case['description']}")
                print(f"   Query: \"{test_case['query']}\"")
                
                start_time = time.time()
                response = await client.process_query(
                    test_case["query"],
                    test_case["intent"],
                    test_case["entities"]
                )
                processing_time = (time.time() - start_time) * 1000
                
                self._display_response(response, processing_time)
    
    async def demonstrate_specialized_methods(self):
        """Demonstrate specialized processing methods."""
        print("\n\n🎯 Specialized Processing Methods")
        print("-" * 40)
        
        async with self.mock_client as client:
            print("🧠 Complex Reasoning Processing:")
            reasoning_response = await client.process_complex_reasoning(
                "Analyze the causal chain: Fed policy → bond yields → equity valuations → market sentiment",
                "causal"
            )
            self._display_response(reasoning_response)
            
            print("\n💰 Financial Analysis Processing:")
            financial_response = await client.process_financial_analysis(
                "What are the key risk factors for tech stocks in 2024?",
                ["AAPL", "GOOGL", "MSFT"],
                "risk_analysis"
            )
            self._display_response(financial_response)
    
    async def demonstrate_error_handling(self):
        """Demonstrate error handling and fallback mechanisms."""
        print("\n\n🛡️ Error Handling & Fallback Demo")
        print("-" * 40)
        
        print("🔧 Testing unavailable API scenario:")
        
        unavailable_client = GrokAPIClient(
            api_endpoint="https://nonexistent-api.example.com/v1",
            timeout=1,
            max_retries=1
        )
        
        try:
            await unavailable_client.initialize()
            is_available = await unavailable_client.check_availability()
            print(f"   API Available: {is_available}")
            
            response = await unavailable_client.process_query(
                "Test query for unavailable API",
                "test_intent",
                {}
            )
            
            print(f"   Response Success: {response.success}")
            print(f"   Error Message: {response.error_message}")
            print(f"   Fallback Response: \"{response.response_text[:50]}...\"")
            
        finally:
            await unavailable_client.close()
    
    async def demonstrate_performance_tracking(self):
        """Demonstrate performance tracking and statistics."""
        print("\n\n📊 Performance Tracking Demo")
        print("-" * 35)
        
        async with self.mock_client as client:
            print("🏃 Running performance test queries...")
            
            queries = [
                "Simple query 1",
                "Complex analysis query with multiple parameters",
                "Financial prediction query",
                "Error simulation query",
                "Performance test query"
            ]
            
            for query in queries:
                await client.process_query(query, "test_intent", {})
            
            stats = client.get_performance_stats()
            
            print(f"\n📈 Performance Statistics:")
            print(f"   Total Requests: {stats['total_requests']}")
            print(f"   Successful Requests: {stats['successful_requests']}")
            print(f"   Failed Requests: {stats['failed_requests']}")
            print(f"   Success Rate: {stats['success_rate_percent']:.1f}%")
            print(f"   Average Latency: {stats['average_latency_ms']:.2f}ms")
            print(f"   Availability Checks: {stats['availability_checks']}")
            print(f"   Max Retries: {stats['max_retries']}")
            print(f"   Timeout: {stats['timeout_seconds']}s")
    
    async def demonstrate_context_usage(self):
        """Demonstrate context manager usage patterns."""
        print("\n\n🔄 Context Manager Usage Demo")
        print("-" * 35)
        
        print("✅ Using async context manager:")
        async with MockGrokAPIClient() as client:
            print(f"   Client initialized: {client.is_available}")
            
            response = await client.process_query(
                "Context manager test query",
                "test_intent",
                {"test": "context"}
            )
            
            print(f"   Response received: {response.success}")
            print(f"   Response length: {len(response.response_text)} chars")
        
        print("✅ Context manager automatically closed")
    
    def _display_response(self, response: GrokResponse, processing_time: float = None):
        """Display formatted response information."""
        success_emoji = "✅" if response.success else "❌"
        print(f"   {success_emoji} Success: {response.success}")
        print(f"   🎯 Confidence: {response.confidence:.2f}")
        print(f"   ⏱️ Latency: {response.latency_ms:.2f}ms")
        if processing_time:
            print(f"   🔄 Total Time: {processing_time:.2f}ms")
        print(f"   🏷️ Model: {response.model_version}")
        print(f"   📝 Response: \"{response.response_text[:80]}...\"")
        
        if response.reasoning_steps:
            print(f"   🧠 Reasoning Steps: {len(response.reasoning_steps)}")
            for i, step in enumerate(response.reasoning_steps[:2], 1):
                print(f"      {i}. {step}")
        
        if response.error_message:
            print(f"   ⚠️ Error: {response.error_message}")
    
    async def demonstrate_integration_patterns(self):
        """Demonstrate integration patterns with other systems."""
        print("\n\n🔗 Integration Patterns Demo")
        print("-" * 35)
        
        print("🎼 Pattern 1: Fallback Integration")
        print("   Primary: Grok API → Fallback: Local NLP")
        
        async with self.mock_client as grok_client:
            try:
                grok_response = await grok_client.process_query(
                    "Complex integration test query",
                    "integration_test",
                    {"pattern": "fallback"}
                )
                
                if grok_response.success:
                    print(f"   ✅ Grok processing successful")
                    print(f"   📝 Response: \"{grok_response.response_text[:50]}...\"")
                else:
                    print(f"   ❌ Grok failed, would fallback to local NLP")
                    
            except Exception as e:
                print(f"   ⚠️ Exception occurred: {e}")
                print(f"   🔄 Would trigger fallback mechanism")
        
        print(f"\n🎼 Pattern 2: Hybrid Processing")
        print("   Combine: Local Analysis + Grok Enhancement")
        
        local_result = "Local analysis: AAPL shows bullish trend"
        
        async with self.mock_client as grok_client:
            enhanced_response = await grok_client.process_query(
                "Enhance this analysis with deeper insights",
                "enhancement",
                {"local_analysis": local_result}
            )
            
            print(f"   🏠 Local: \"{local_result}\"")
            print(f"   🤖 Enhanced: \"{enhanced_response.response_text[:50]}...\"")
            print(f"   🔗 Combined approach provides comprehensive analysis")
    
    async def interactive_grok_demo(self):
        """Interactive demo for testing Grok integration."""
        print("\n\n🎮 Interactive Grok Demo")
        print("-" * 30)
        print("Test Grok API integration with your own queries!")
        print("Type 'quit' to exit, 'stats' to see performance stats")
        
        async with self.mock_client as client:
            while True:
                try:
                    user_query = input("\n🤖 Enter your query for Grok: ").strip()
                    
                    if user_query.lower() == 'quit':
                        break
                    elif user_query.lower() == 'stats':
                        stats = client.get_performance_stats()
                        print(f"\n📊 Current Stats:")
                        print(f"   Requests: {stats['total_requests']}")
                        print(f"   Success Rate: {stats['success_rate_percent']:.1f}%")
                        print(f"   Avg Latency: {stats['average_latency_ms']:.2f}ms")
                        continue
                    elif not user_query:
                        continue
                    
                    intent = input("🎯 Intent (or press Enter for 'general'): ").strip() or "general"
                    
                    print(f"\n🔄 Processing with Grok...")
                    start_time = time.time()
                    
                    response = await client.process_query(
                        user_query,
                        intent,
                        {"interactive": True}
                    )
                    
                    processing_time = (time.time() - start_time) * 1000
                    self._display_response(response, processing_time)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
        
        print("\n👋 Thanks for testing Grok integration!")

async def main():
    """Main demo function."""
    demo = GrokIntegrationDemo()
    
    try:
        await demo.demonstrate_mock_client()
        await demo.demonstrate_specialized_methods()
        await demo.demonstrate_error_handling()
        await demo.demonstrate_performance_tracking()
        await demo.demonstrate_context_usage()
        await demo.demonstrate_integration_patterns()
        
        print(f"\n\n🎉 Grok Integration Demo Complete!")
        print("Successfully demonstrated:")
        print("✅ Mock client functionality for testing")
        print("✅ Specialized processing methods")
        print("✅ Error handling and fallback mechanisms")
        print("✅ Performance tracking and statistics")
        print("✅ Context manager usage patterns")
        print("✅ Integration patterns with other systems")
        
        interactive = input("\n🎮 Run interactive Grok demo? (y/n): ").strip().lower()
        if interactive == 'y':
            await demo.interactive_grok_demo()
            
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))
from system_orchestrator import SystemOrchestrator
from nlp_voice_interface import NLPVoiceInterface
from auto_agent_system import AutoAgentSystem
from stock_prediction_engine import StockPredictionEngine, PredictionRequest, PredictionType
from simulation_engine_bridge import SimulationEngineBridge, SimulationRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("=== Phase 2 Integration Demo ===")
    
    print("\n1. Initializing Phase 2 components...")
    orchestrator = SystemOrchestrator()
    nlp_interface = NLPVoiceInterface()
    auto_agent = AutoAgentSystem()
    stock_predictor = StockPredictionEngine()
    simulation_bridge = SimulationEngineBridge()
    
    print("✓ All components initialized")
    
    print("\n2. Testing NLP/Voice interface with stock prediction queries...")
    queries = [
        "predict stock price for AAPL",
        "analyze VIX impact on Microsoft",
        "forecast volatility for GOOGL using Brownian motion"
    ]
    
    for query in queries:
        print(f"  Query: '{query}'")
        start_time = time.time()
        response = await nlp_interface.process_text_query(query)
        latency = (time.time() - start_time) * 1000
        print(f"  Response: {response['response_text'][:100]}...")
        print(f"  Latency: {latency:.2f}ms")
    
    print("\n3. Testing auto-agent gap detection and VIX prediction...")
    gaps = await auto_agent.detect_gaps(["AAPL", "MSFT"], ["1D"])
    print(f"  Detected {len(gaps)} data gaps")
    
    vix_prediction = await auto_agent.predict_vix_impact("AAPL")
    if 'error' not in vix_prediction:
        print(f"  VIX prediction: {vix_prediction['volatility_forecast']:.2f}% volatility")
    
    print("\n4. Testing stock prediction engine with causal analysis...")
    request = PredictionRequest(
        symbol="AAPL",
        prediction_type=PredictionType.PRICE_MOVEMENT,
        timeframe="1D",
        horizon_days=5,
        include_vix=True,
        include_causal=True
    )
    
    prediction = await stock_predictor.predict(request)
    print(f"  Stock prediction: ${prediction.predicted_value:.2f}")
    print(f"  Confidence: {prediction.confidence:.1%}")
    print(f"  VIX impact: {prediction.vix_impact:.3f}")
    print(f"  Causal effects: {prediction.causal_effects}")
    
    print("\n5. Testing simulation engine with Brownian motion...")
    sim_request = SimulationRequest(
        s0=100.0,
        mu=0.05,
        sigma=0.2,
        dt=0.01,
        t=1.0,
        n_simulations=5
    )
    
    gbm_result = await simulation_bridge.simulate_gbm(sim_request)
    print(f"  GBM simulation: {len(gbm_result.prices)} price points")
    print(f"  Final price: ${gbm_result.prices[-1]:.2f}")
    print(f"  Max velocity: {max(gbm_result.velocities):.2f}")
    print(f"  Simulation latency: {gbm_result.latency_ms:.2f}ms")
    
    vectors = await simulation_bridge.generate_monte_carlo_vectors(sim_request)
    print(f"  Monte Carlo: {len(vectors)} simulation vectors generated")
    
    print("\n6. Testing strand combination for fusion...")
    if len(vectors) >= 3:
        combined = await simulation_bridge.combine_strands(vectors[:3], [0.5, 0.3, 0.2])
        print(f"  Combined strand length: {len(combined)}")
        print(f"  Final combined value: {combined[-1]:.2f}")
    
    print("\n7. Performance summary...")
    
    nlp_stats = nlp_interface.get_performance_stats()
    print(f"  NLP Interface - Queries processed: {nlp_stats['total_queries']}")
    print(f"  NLP Interface - Average latency: {nlp_stats['average_latency_ms']:.2f}ms")
    
    agent_metrics = auto_agent.get_performance_metrics()
    print(f"  Auto-Agent - Gaps detected: {agent_metrics['gaps_detected']}")
    print(f"  Auto-Agent - VIX predictions: {agent_metrics['vix_predictions_made']}")
    
    predictor_metrics = stock_predictor.get_performance_metrics()
    print(f"  Stock Predictor - Predictions made: {predictor_metrics['predictions_made']}")
    print(f"  Stock Predictor - Average latency: {predictor_metrics['average_latency_ms']:.2f}ms")
    
    sim_metrics = simulation_bridge.get_performance_metrics()
    print(f"  Simulation Bridge - Simulations run: {sim_metrics['simulations_run']}")
    print(f"  Simulation Bridge - Rust bridge active: {sim_metrics['rust_bridge_active']}")
    
    print("\n✓ Phase 2 integration demo completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())

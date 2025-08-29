import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logging.warning("Docker not available")

try:
    from .wasm_compilation_pipeline import WasmCompilationPipeline
    from .temporal_causal_gnn import TemporalCausalGNN
    from .high_performance_option_analyzer import HighPerformanceOptionAnalyzer
    INFERENCE_COMPONENTS_AVAILABLE = True
except ImportError:
    INFERENCE_COMPONENTS_AVAILABLE = False
    logging.warning("Inference components not available")

@dataclass
class EdgeInferenceResult:
    inference_id: str
    model_type: str
    input_data: Dict[str, Any]
    predictions: Dict[str, Any]
    inference_time_ms: float
    edge_node_id: str
    wasm_module_used: str
    confidence_score: float

class EdgeAIInference:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.docker_client = None
        self.wasm_pipeline = None
        self.causal_gnn = None
        self.option_analyzer = None
        
        self.edge_nodes = {}
        self.deployed_models = {}
        
        self.inferences_performed = 0
        self.inference_errors = 0
        self.offline_cache = {}

    async def initialize(self):
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
                self.logger.info("Connected to Docker daemon")
            except Exception as e:
                self.logger.warning(f"Docker connection failed: {e}")
        
        if INFERENCE_COMPONENTS_AVAILABLE:
            try:
                self.wasm_pipeline = WasmCompilationPipeline(self.config)
                await self.wasm_pipeline.initialize()
                
                self.causal_gnn = TemporalCausalGNN(self.config)
                await self.causal_gnn.initialize()
                
                self.option_analyzer = HighPerformanceOptionAnalyzer(self.config)
                await self.option_analyzer.initialize()
                
                await self._compile_inference_models()
                await self._deploy_edge_inference_nodes()
                
                self.logger.info("Initialized edge AI inference")
            except Exception as e:
                self.logger.warning(f"Inference components initialization failed: {e}")

    async def _compile_inference_models(self):
        try:
            if not self.wasm_pipeline:
                return
            
            causal_model = await self.wasm_pipeline.compile_rust_to_wasm(
                '', 'causal_inference_model'
            )
            
            if causal_model:
                self.deployed_models['causal_gnn'] = causal_model
                self.logger.info("Compiled causal GNN inference model to WASM")
            
            option_model = await self.wasm_pipeline.compile_rust_to_wasm(
                '', 'option_analysis_model'
            )
            
            if option_model:
                self.deployed_models['option_analyzer'] = option_model
                self.logger.info("Compiled option analysis model to WASM")
            
            sentiment_model = await self.wasm_pipeline.compile_python_to_wasm(
                '', 'sentiment_inference_model'
            )
            
            if sentiment_model:
                self.deployed_models['sentiment_analyzer'] = sentiment_model
                self.logger.info("Compiled sentiment analysis model to WASM")
                
        except Exception as e:
            self.logger.error(f"Model compilation failed: {e}")

    async def _deploy_edge_inference_nodes(self):
        try:
            if not self.docker_client or not self.deployed_models:
                return
            
            for i in range(3):
                node_id = f"edge_inference_node_{i:03d}"
                
                container = self.docker_client.containers.run(
                    'wasmedge/wasmedge:latest',
                    'sleep infinity',
                    name=node_id,
                    detach=True,
                    volumes={
                        self.wasm_pipeline.output_dir: {
                            'bind': '/inference_models',
                            'mode': 'ro'
                        }
                    },
                    environment={
                        'WASMEDGE_INFERENCE_NODE': 'true',
                        'NODE_ID': node_id
                    }
                )
                
                self.edge_nodes[node_id] = {
                    'container_id': container.id,
                    'status': 'active',
                    'models': list(self.deployed_models.keys()),
                    'inferences_performed': 0,
                    'last_activity': datetime.now()
                }
                
                self.logger.info(f"Deployed edge inference node: {node_id}")
                
        except Exception as e:
            self.logger.error(f"Edge inference node deployment failed: {e}")

    async def perform_causal_inference_at_edge(self, market_data: Dict[str, Any], edge_node_id: Optional[str] = None) -> EdgeInferenceResult:
        start_time = time.time()
        
        try:
            if not edge_node_id:
                edge_node_id = self._select_optimal_inference_node('causal_gnn')
            
            inference_id = f"causal_{int(datetime.now().timestamp() * 1000000)}"
            
            if edge_node_id and edge_node_id in self.edge_nodes:
                predictions = await self._execute_causal_inference_wasm(market_data, edge_node_id)
                wasm_module_used = self.deployed_models.get('causal_gnn', {}).get('module_id', 'unknown')
            else:
                predictions = await self._fallback_causal_inference(market_data)
                wasm_module_used = 'fallback_local'
                edge_node_id = 'local_fallback'
            
            inference_time_ms = (time.time() - start_time) * 1000
            
            result = EdgeInferenceResult(
                inference_id=inference_id,
                model_type='causal_gnn',
                input_data=market_data,
                predictions=predictions,
                inference_time_ms=inference_time_ms,
                edge_node_id=edge_node_id,
                wasm_module_used=wasm_module_used,
                confidence_score=predictions.get('confidence_score', 0.5)
            )
            
            self.inferences_performed += 1
            
            if edge_node_id in self.edge_nodes:
                self.edge_nodes[edge_node_id]['inferences_performed'] += 1
                self.edge_nodes[edge_node_id]['last_activity'] = datetime.now()
            
            await self._cache_for_offline_use(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Causal inference at edge failed: {e}")
            self.inference_errors += 1
            
            return EdgeInferenceResult(
                inference_id=f"error_{int(datetime.now().timestamp())}",
                model_type='causal_gnn',
                input_data=market_data,
                predictions={'error': str(e)},
                inference_time_ms=(time.time() - start_time) * 1000,
                edge_node_id='error',
                wasm_module_used='error',
                confidence_score=0.0
            )

    async def perform_option_analysis_at_edge(self, option_data: Dict[str, Any], edge_node_id: Optional[str] = None) -> EdgeInferenceResult:
        start_time = time.time()
        
        try:
            if not edge_node_id:
                edge_node_id = self._select_optimal_inference_node('option_analyzer')
            
            inference_id = f"option_{int(datetime.now().timestamp() * 1000000)}"
            
            if edge_node_id and edge_node_id in self.edge_nodes:
                predictions = await self._execute_option_analysis_wasm(option_data, edge_node_id)
                wasm_module_used = self.deployed_models.get('option_analyzer', {}).get('module_id', 'unknown')
            else:
                predictions = await self._fallback_option_analysis(option_data)
                wasm_module_used = 'fallback_local'
                edge_node_id = 'local_fallback'
            
            inference_time_ms = (time.time() - start_time) * 1000
            
            result = EdgeInferenceResult(
                inference_id=inference_id,
                model_type='option_analyzer',
                input_data=option_data,
                predictions=predictions,
                inference_time_ms=inference_time_ms,
                edge_node_id=edge_node_id,
                wasm_module_used=wasm_module_used,
                confidence_score=predictions.get('confidence_score', 0.5)
            )
            
            self.inferences_performed += 1
            
            if edge_node_id in self.edge_nodes:
                self.edge_nodes[edge_node_id]['inferences_performed'] += 1
                self.edge_nodes[edge_node_id]['last_activity'] = datetime.now()
            
            await self._cache_for_offline_use(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Option analysis at edge failed: {e}")
            self.inference_errors += 1
            
            return EdgeInferenceResult(
                inference_id=f"error_{int(datetime.now().timestamp())}",
                model_type='option_analyzer',
                input_data=option_data,
                predictions={'error': str(e)},
                inference_time_ms=(time.time() - start_time) * 1000,
                edge_node_id='error',
                wasm_module_used='error',
                confidence_score=0.0
            )

    def _select_optimal_inference_node(self, model_type: str) -> Optional[str]:
        available_nodes = [
            node_id for node_id, node_info in self.edge_nodes.items()
            if node_info['status'] == 'active' and model_type in node_info['models']
        ]
        
        if not available_nodes:
            return None
        
        best_node = min(
            available_nodes,
            key=lambda node_id: self.edge_nodes[node_id]['inferences_performed']
        )
        
        return best_node

    async def _execute_causal_inference_wasm(self, market_data: Dict[str, Any], edge_node_id: str) -> Dict[str, Any]:
        try:
            if not self.docker_client:
                return await self._fallback_causal_inference(market_data)
            
            container = self.docker_client.containers.get(
                self.edge_nodes[edge_node_id]['container_id']
            )
            
            input_json = json.dumps(market_data)
            
            exec_result = container.exec_run(
                f'echo \'{input_json}\' | wasmedge /inference_models/causal_inference_model.wasm',
                capture_output=True
            )
            
            if exec_result.exit_code == 0:
                return json.loads(exec_result.output.decode())
            else:
                return await self._fallback_causal_inference(market_data)
                
        except Exception as e:
            self.logger.error(f"WASM causal inference execution failed: {e}")
            return await self._fallback_causal_inference(market_data)

    async def _execute_option_analysis_wasm(self, option_data: Dict[str, Any], edge_node_id: str) -> Dict[str, Any]:
        try:
            if not self.docker_client:
                return await self._fallback_option_analysis(option_data)
            
            container = self.docker_client.containers.get(
                self.edge_nodes[edge_node_id]['container_id']
            )
            
            input_json = json.dumps(option_data)
            
            exec_result = container.exec_run(
                f'echo \'{input_json}\' | wasmedge /inference_models/option_analysis_model.wasm',
                capture_output=True
            )
            
            if exec_result.exit_code == 0:
                return json.loads(exec_result.output.decode())
            else:
                return await self._fallback_option_analysis(option_data)
                
        except Exception as e:
            self.logger.error(f"WASM option analysis execution failed: {e}")
            return await self._fallback_option_analysis(option_data)

    async def _fallback_causal_inference(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.causal_gnn:
                result = await self.causal_gnn.predict_causal_relationships(market_data)
                return {
                    'causal_strength': result.get('causal_strength', 0.5),
                    'confidence_score': result.get('confidence_score', 0.5),
                    'gnn_predictions': result.get('predictions', {}),
                    'processing_method': 'fallback_local'
                }
            else:
                return {
                    'causal_strength': 0.5,
                    'confidence_score': 0.5,
                    'gnn_predictions': {'mock': 'prediction'},
                    'processing_method': 'mock_fallback'
                }
                
        except Exception as e:
            self.logger.error(f"Fallback causal inference failed: {e}")
            return {
                'error': str(e),
                'processing_method': 'error_fallback'
            }

    async def _fallback_option_analysis(self, option_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.option_analyzer:
                result = await self.option_analyzer.analyze_option_chain(option_data)
                return {
                    'greeks_summary': result.get('greeks_summary', {}),
                    'unusual_activity': result.get('unusual_activity', {}),
                    'volatility_analysis': result.get('volatility_analysis', {}),
                    'confidence_score': result.get('confidence_score', 0.5),
                    'processing_method': 'fallback_local'
                }
            else:
                return {
                    'greeks_summary': {'delta': 0.5, 'gamma': 0.1, 'theta': -0.05, 'vega': 0.2},
                    'unusual_activity': {'detected': False},
                    'volatility_analysis': {'implied_vol': 0.25},
                    'confidence_score': 0.5,
                    'processing_method': 'mock_fallback'
                }
                
        except Exception as e:
            self.logger.error(f"Fallback option analysis failed: {e}")
            return {
                'error': str(e),
                'processing_method': 'error_fallback'
            }

    async def _cache_for_offline_use(self, result: EdgeInferenceResult):
        try:
            cache_key = f"{result.model_type}_{result.inference_id}"
            
            self.offline_cache[cache_key] = {
                'predictions': result.predictions,
                'confidence_score': result.confidence_score,
                'cached_at': datetime.now().isoformat(),
                'model_type': result.model_type
            }
            
            if len(self.offline_cache) > 1000:
                oldest_keys = sorted(
                    self.offline_cache.keys(),
                    key=lambda k: self.offline_cache[k]['cached_at']
                )[:500]
                
                for key in oldest_keys:
                    del self.offline_cache[key]
                    
        except Exception as e:
            self.logger.error(f"Offline caching failed: {e}")

    async def get_offline_predictions(self, model_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            relevant_predictions = [
                prediction for key, prediction in self.offline_cache.items()
                if prediction['model_type'] == model_type
            ]
            
            relevant_predictions.sort(
                key=lambda p: p['cached_at'],
                reverse=True
            )
            
            return relevant_predictions[:limit]
            
        except Exception as e:
            self.logger.error(f"Offline prediction retrieval failed: {e}")
            return []

    async def get_edge_inference_status(self) -> Dict[str, Any]:
        return {
            'total_nodes': len(self.edge_nodes),
            'active_nodes': len([n for n in self.edge_nodes.values() if n['status'] == 'active']),
            'deployed_models': len(self.deployed_models),
            'inferences_performed': self.inferences_performed,
            'inference_errors': self.inference_errors,
            'success_rate': (self.inferences_performed - self.inference_errors) / max(self.inferences_performed, 1),
            'offline_cache_size': len(self.offline_cache),
            'nodes': [
                {
                    'node_id': node_id,
                    'status': node_info['status'],
                    'models': len(node_info['models']),
                    'inferences_performed': node_info['inferences_performed'],
                    'last_activity': node_info['last_activity'].isoformat()
                }
                for node_id, node_info in self.edge_nodes.items()
            ],
            'timestamp': datetime.now().isoformat()
        }

    async def shutdown(self):
        if self.docker_client:
            for node_id, node_info in list(self.edge_nodes.items()):
                try:
                    container = self.docker_client.containers.get(node_info['container_id'])
                    container.stop()
                    container.remove()
                    self.logger.info(f"Stopped edge inference node: {node_id}")
                except Exception as e:
                    self.logger.error(f"Failed to stop node {node_id}: {e}")
            
            self.docker_client.close()
        
        if self.wasm_pipeline:
            await self.wasm_pipeline.shutdown()
        
        if self.causal_gnn:
            await self.causal_gnn.shutdown()
        
        if self.option_analyzer:
            await self.option_analyzer.shutdown()

async def main():
    config = {
        'build_dir': '/tmp/wasm_builds',
        'output_dir': '/tmp/wasm_output',
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password'
    }
    
    edge_inference = EdgeAIInference(config)
    await edge_inference.initialize()
    
    sample_market_data = {
        'symbol': 'AAPL',
        'price': 150.0,
        'volume': 1000000,
        'price_data': [148, 149, 150, 151, 150],
        'timestamp': datetime.now().isoformat()
    }
    
    sample_option_data = {
        'symbol': 'AAPL',
        'strikes': [145, 150, 155],
        'expiries': [0.08, 0.08, 0.08],
        'underlying_price': 150.0,
        'risk_free_rate': 0.05,
        'volatilities': [0.25, 0.23, 0.25]
    }
    
    causal_result = await edge_inference.perform_causal_inference_at_edge(sample_market_data)
    option_result = await edge_inference.perform_option_analysis_at_edge(sample_option_data)
    
    print(f"Edge AI Inference Results:")
    print(f"- Causal inference time: {causal_result.inference_time_ms:.2f}ms")
    print(f"- Option analysis time: {option_result.inference_time_ms:.2f}ms")
    print(f"- Causal confidence: {causal_result.confidence_score:.2f}")
    print(f"- Option confidence: {option_result.confidence_score:.2f}")
    
    status = await edge_inference.get_edge_inference_status()
    print(f"\nEdge Inference Status:")
    print(f"- Active nodes: {status['active_nodes']}/{status['total_nodes']}")
    print(f"- Success rate: {status['success_rate']:.2%}")
    print(f"- Offline cache size: {status['offline_cache_size']}")
    
    await edge_inference.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

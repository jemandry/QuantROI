import asyncio
import logging
import json
import hashlib
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
    from .news_ingestion import NewsIngestionEngine
    from .nlp_processor import EnhancedNLPProcessor
    from .wasm_compilation_pipeline import WasmCompilationPipeline
    NEWS_COMPONENTS_AVAILABLE = True
except ImportError:
    NEWS_COMPONENTS_AVAILABLE = False
    logging.warning("News components not available")

@dataclass
class EdgeProcessingResult:
    news_id: str
    processed_data: Dict[str, Any]
    processing_time: float
    edge_node_id: str
    wasm_module_used: str
    ipfs_hash: Optional[str] = None

class EdgeNewsProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.docker_client = None
        self.wasm_pipeline = None
        self.news_ingestion = None
        self.nlp_processor = None
        
        self.edge_nodes = {}
        self.deployed_modules = {}
        
        self.processed_items = 0
        self.processing_errors = 0

    async def initialize(self):
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
                self.logger.info("Connected to Docker daemon")
            except Exception as e:
                self.logger.warning(f"Docker connection failed: {e}")
        
        if NEWS_COMPONENTS_AVAILABLE:
            try:
                self.wasm_pipeline = WasmCompilationPipeline(self.config)
                await self.wasm_pipeline.initialize()
                
                self.news_ingestion = NewsIngestionEngine(self.config)
                await self.news_ingestion.initialize()
                
                self.nlp_processor = EnhancedNLPProcessor(self.config)
                await self.nlp_processor.initialize()
                
                self.logger.info("Initialized news processing components")
            except Exception as e:
                self.logger.warning(f"News components initialization failed: {e}")
        
        await self._deploy_edge_infrastructure()

    async def _deploy_edge_infrastructure(self):
        try:
            if not self.wasm_pipeline:
                self.logger.warning("WASM pipeline not available for edge deployment")
                return
            
            modules = await self.wasm_pipeline.compile_news_processing_modules()
            
            if modules:
                deployment_results = await self.wasm_pipeline.deploy_to_edge_nodes(modules)
                
                for deployed_module in deployment_results['deployed_modules']:
                    module_id = deployed_module['module_id']
                    container_name = deployed_module['container_name']
                    
                    self.deployed_modules[module_id] = deployed_module
                    
                    if container_name not in self.edge_nodes:
                        self.edge_nodes[container_name] = {
                            'node_id': container_name,
                            'modules': [],
                            'status': 'active',
                            'processed_count': 0,
                            'last_activity': datetime.now()
                        }
                    
                    self.edge_nodes[container_name]['modules'].append(module_id)
                
                self.logger.info(f"Deployed {len(modules)} WASM modules to {len(self.edge_nodes)} edge nodes")
            
        except Exception as e:
            self.logger.error(f"Edge infrastructure deployment failed: {e}")

    async def process_news_at_edge(self, news_items: List[Dict[str, Any]], edge_node_id: Optional[str] = None) -> List[EdgeProcessingResult]:
        results = []
        
        if not edge_node_id:
            edge_node_id = self._select_optimal_edge_node()
        
        if not edge_node_id or edge_node_id not in self.edge_nodes:
            self.logger.warning("No suitable edge node available, falling back to local processing")
            return await self._process_locally(news_items)
        
        for news_item in news_items:
            try:
                result = await self._process_single_item_at_edge(news_item, edge_node_id)
                if result:
                    results.append(result)
                    self.processed_items += 1
                    
            except Exception as e:
                self.logger.error(f"Edge processing failed for {news_item.get('news_id', 'unknown')}: {e}")
                self.processing_errors += 1
        
        return results

    def _select_optimal_edge_node(self) -> Optional[str]:
        if not self.edge_nodes:
            return None
        
        best_node = None
        min_load = float('inf')
        
        for node_id, node_info in self.edge_nodes.items():
            if node_info['status'] == 'active':
                load_score = node_info['processed_count'] / max(len(node_info['modules']), 1)
                if load_score < min_load:
                    min_load = load_score
                    best_node = node_id
        
        return best_node

    async def _process_single_item_at_edge(self, news_item: Dict[str, Any], edge_node_id: str) -> Optional[EdgeProcessingResult]:
        try:
            start_time = datetime.now()
            
            edge_node = self.edge_nodes[edge_node_id]
            
            if not edge_node['modules']:
                return None
            
            wasm_module_id = edge_node['modules'][0]
            
            if self.docker_client:
                container_name = edge_node_id
                
                try:
                    container = self.docker_client.containers.get(container_name)
                    
                    news_json = json.dumps(news_item)
                    
                    exec_result = container.exec_run(
                        f'echo \'{news_json}\' | wasmedge /wasm_modules/{wasm_module_id}.wasm',
                        capture_output=True
                    )
                    
                    if exec_result.exit_code == 0:
                        processed_data = json.loads(exec_result.output.decode())
                    else:
                        processed_data = await self._fallback_processing(news_item)
                        
                except Exception as e:
                    self.logger.error(f"Container execution failed: {e}")
                    processed_data = await self._fallback_processing(news_item)
            else:
                processed_data = await self._fallback_processing(news_item)
            
            ipfs_hash = await self._store_processed_data_in_ipfs(processed_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            edge_node['processed_count'] += 1
            edge_node['last_activity'] = datetime.now()
            
            return EdgeProcessingResult(
                news_id=news_item.get('news_id', ''),
                processed_data=processed_data,
                processing_time=processing_time,
                edge_node_id=edge_node_id,
                wasm_module_used=wasm_module_id,
                ipfs_hash=ipfs_hash
            )
            
        except Exception as e:
            self.logger.error(f"Edge processing failed: {e}")
            return None

    async def _fallback_processing(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.nlp_processor:
                nlp_result = await self.nlp_processor.process_news_text(
                    news_item.get('news_id', ''),
                    news_item.get('full_text', ''),
                    news_item.get('title', '')
                )
                
                return {
                    'news_id': news_item.get('news_id', ''),
                    'source': news_item.get('source', 'unknown'),
                    'sentiment_score': nlp_result.sentiment_score,
                    'sentiment_label': nlp_result.sentiment_label,
                    'entities': nlp_result.entities,
                    'event_tags': [
                        {
                            'event_type': tag.event_type,
                            'confidence': tag.confidence,
                            'entities': tag.entities
                        }
                        for tag in nlp_result.tags
                    ],
                    'confidence_score': nlp_result.confidence_score,
                    'processing_method': 'fallback_local',
                    'processing_time': nlp_result.processing_time
                }
            else:
                return {
                    'news_id': news_item.get('news_id', ''),
                    'source': news_item.get('source', 'unknown'),
                    'sentiment_score': 0.0,
                    'sentiment_label': 'neutral',
                    'entities': [],
                    'event_tags': [],
                    'confidence_score': 0.5,
                    'processing_method': 'mock_fallback',
                    'processing_time': 0.001
                }
                
        except Exception as e:
            self.logger.error(f"Fallback processing failed: {e}")
            return {
                'news_id': news_item.get('news_id', ''),
                'error': str(e),
                'processing_method': 'error_fallback'
            }

    async def _store_processed_data_in_ipfs(self, processed_data: Dict[str, Any]) -> Optional[str]:
        try:
            if self.news_ingestion and self.news_ingestion.ipfs_client:
                content = json.dumps(processed_data, sort_keys=True)
                ipfs_hash = await self.news_ingestion._store_in_ipfs(content)
                return ipfs_hash
            else:
                content_hash = hashlib.sha256(json.dumps(processed_data, sort_keys=True).encode()).hexdigest()
                return f"mock_ipfs_{content_hash[:16]}"
                
        except Exception as e:
            self.logger.error(f"IPFS storage failed: {e}")
            return None

    async def _process_locally(self, news_items: List[Dict[str, Any]]) -> List[EdgeProcessingResult]:
        results = []
        
        for news_item in news_items:
            try:
                start_time = datetime.now()
                
                processed_data = await self._fallback_processing(news_item)
                ipfs_hash = await self._store_processed_data_in_ipfs(processed_data)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                result = EdgeProcessingResult(
                    news_id=news_item.get('news_id', ''),
                    processed_data=processed_data,
                    processing_time=processing_time,
                    edge_node_id='local_fallback',
                    wasm_module_used='local_processor',
                    ipfs_hash=ipfs_hash
                )
                
                results.append(result)
                self.processed_items += 1
                
            except Exception as e:
                self.logger.error(f"Local processing failed: {e}")
                self.processing_errors += 1
        
        return results

    async def get_edge_node_status(self) -> Dict[str, Any]:
        status = {
            'total_nodes': len(self.edge_nodes),
            'active_nodes': 0,
            'total_modules': len(self.deployed_modules),
            'processed_items': self.processed_items,
            'processing_errors': self.processing_errors,
            'nodes': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for node_id, node_info in self.edge_nodes.items():
            if node_info['status'] == 'active':
                status['active_nodes'] += 1
            
            status['nodes'].append({
                'node_id': node_id,
                'status': node_info['status'],
                'modules_count': len(node_info['modules']),
                'processed_count': node_info['processed_count'],
                'last_activity': node_info['last_activity'].isoformat()
            })
        
        return status

    async def shutdown(self):
        if self.docker_client:
            for node_id in list(self.edge_nodes.keys()):
                try:
                    container = self.docker_client.containers.get(node_id)
                    container.stop()
                    container.remove()
                    self.logger.info(f"Stopped edge node: {node_id}")
                except Exception as e:
                    self.logger.error(f"Failed to stop edge node {node_id}: {e}")
            
            self.docker_client.close()
        
        if self.wasm_pipeline:
            await self.wasm_pipeline.shutdown()
        
        if self.news_ingestion:
            await self.news_ingestion.shutdown()
        
        if self.nlp_processor:
            await self.nlp_processor.shutdown()

async def main():
    config = {
        'build_dir': '/tmp/wasm_builds',
        'output_dir': '/tmp/wasm_output',
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
        'ipfs_api_url': 'http://localhost:5001',
        'kafka_bootstrap_servers': 'localhost:9092'
    }
    
    edge_processor = EdgeNewsProcessor(config)
    await edge_processor.initialize()
    
    sample_news = [
        {
            'news_id': 'edge_test_001',
            'source': 'reuters',
            'title': 'Market volatility increases amid economic uncertainty',
            'full_text': 'Financial markets experienced significant volatility today as investors reacted to economic uncertainty.',
            'published_time': datetime.now().isoformat()
        },
        {
            'news_id': 'edge_test_002',
            'source': 'bloomberg',
            'title': 'Tech stocks rally on AI breakthrough',
            'full_text': 'Technology stocks surged following news of a major artificial intelligence breakthrough.',
            'published_time': datetime.now().isoformat()
        }
    ]
    
    results = await edge_processor.process_news_at_edge(sample_news)
    
    print(f"Edge News Processing Results:")
    print(f"- Processed items: {len(results)}")
    print(f"- Processing errors: {edge_processor.processing_errors}")
    
    for result in results:
        print(f"\nNews ID: {result.news_id}")
        print(f"- Processing time: {result.processing_time:.3f}s")
        print(f"- Edge node: {result.edge_node_id}")
        print(f"- WASM module: {result.wasm_module_used}")
        print(f"- IPFS hash: {result.ipfs_hash}")
        print(f"- Sentiment: {result.processed_data.get('sentiment_score', 'N/A')}")
    
    status = await edge_processor.get_edge_node_status()
    print(f"\nEdge Node Status:")
    print(f"- Total nodes: {status['total_nodes']}")
    print(f"- Active nodes: {status['active_nodes']}")
    print(f"- Total modules: {status['total_modules']}")
    
    await edge_processor.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

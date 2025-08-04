import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logging.warning("Docker not available")

try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logging.warning("Ray not available")

try:
    from .distributed_ai_processor import DistributedAIProcessor
    from .wasm_compilation_pipeline import WasmCompilationPipeline, WasmModule
    from .edge_news_processor import EdgeNewsProcessor
    DISTRIBUTED_COMPONENTS_AVAILABLE = True
except ImportError:
    DISTRIBUTED_COMPONENTS_AVAILABLE = False
    logging.warning("Distributed components not available")

@dataclass
class EdgeNode:
    node_id: str
    container_id: str
    status: str
    wasm_modules: List[str]
    workload: int
    last_heartbeat: datetime
    performance_metrics: Dict[str, float]

@dataclass
class WorkloadTask:
    task_id: str
    task_type: str
    data: Dict[str, Any]
    priority: int
    assigned_node: Optional[str] = None
    status: str = 'pending'
    created_at: datetime = None

class WasmEdgeOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.docker_client = None
        self.ray_cluster = None
        self.distributed_processor = None
        self.wasm_pipeline = None
        self.edge_processor = None
        
        self.edge_nodes = {}
        self.task_queue = []
        self.completed_tasks = []
        
        self.orchestration_active = False
        self.heartbeat_interval = config.get('heartbeat_interval', 30)
        self.max_node_workload = config.get('max_node_workload', 10)
        
        self.tasks_processed = 0
        self.orchestration_errors = 0

    async def initialize(self):
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
                self.logger.info("Connected to Docker daemon")
            except Exception as e:
                self.logger.warning(f"Docker connection failed: {e}")
        
        if RAY_AVAILABLE:
            try:
                if not ray.is_initialized():
                    ray.init(address='auto', ignore_reinit_error=True)
                self.ray_cluster = ray
                self.logger.info("Connected to Ray cluster")
            except Exception as e:
                self.logger.warning(f"Ray initialization failed: {e}")
        
        if DISTRIBUTED_COMPONENTS_AVAILABLE:
            try:
                self.distributed_processor = DistributedAIProcessor(self.config)
                await self.distributed_processor.initialize()
                
                self.wasm_pipeline = WasmCompilationPipeline(self.config)
                await self.wasm_pipeline.initialize()
                
                self.edge_processor = EdgeNewsProcessor(self.config)
                await self.edge_processor.initialize()
                
                self.logger.info("Initialized distributed components")
            except Exception as e:
                self.logger.warning(f"Distributed components initialization failed: {e}")

    async def deploy_wasm_edge_cluster(self, cluster_size: int = 3) -> Dict[str, Any]:
        deployment_results = {
            'deployed_nodes': [],
            'deployment_errors': [],
            'cluster_size': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            if not self.wasm_pipeline:
                self.logger.error("WASM pipeline not available")
                return deployment_results
            
            modules = await self.wasm_pipeline.compile_news_processing_modules()
            
            if not modules:
                self.logger.error("No WASM modules available for deployment")
                return deployment_results
            
            for i in range(cluster_size):
                try:
                    node_id = f"wasmedge_node_{i:03d}"
                    
                    container = self.docker_client.containers.run(
                        'wasmedge/wasmedge:latest',
                        'sleep infinity',
                        name=node_id,
                        detach=True,
                        volumes={
                            self.wasm_pipeline.output_dir: {
                                'bind': '/wasm_modules',
                                'mode': 'ro'
                            }
                        },
                        environment={
                            'WASMEDGE_NODE_ID': node_id,
                            'WASMEDGE_CLUSTER_MODE': 'true'
                        }
                    )
                    
                    edge_node = EdgeNode(
                        node_id=node_id,
                        container_id=container.id,
                        status='active',
                        wasm_modules=[m.module_id for m in modules],
                        workload=0,
                        last_heartbeat=datetime.now(),
                        performance_metrics={
                            'cpu_usage': 0.0,
                            'memory_usage': 0.0,
                            'tasks_completed': 0,
                            'average_response_time': 0.0
                        }
                    )
                    
                    self.edge_nodes[node_id] = edge_node
                    
                    deployment_results['deployed_nodes'].append({
                        'node_id': node_id,
                        'container_id': container.id,
                        'wasm_modules': len(modules),
                        'status': 'active'
                    })
                    
                except Exception as e:
                    self.logger.error(f"Node deployment failed for {node_id}: {e}")
                    deployment_results['deployment_errors'].append({
                        'node_id': f"wasmedge_node_{i:03d}",
                        'error': str(e)
                    })
                    self.orchestration_errors += 1
            
            deployment_results['cluster_size'] = len(deployment_results['deployed_nodes'])
            
            if deployment_results['cluster_size'] > 0:
                await self._start_orchestration()
            
            self.logger.info(f"Deployed WasmEdge cluster with {deployment_results['cluster_size']} nodes")
            return deployment_results
            
        except Exception as e:
            self.logger.error(f"Cluster deployment failed: {e}")
            deployment_results['deployment_errors'].append({'error': str(e)})
            return deployment_results

    async def _start_orchestration(self):
        if self.orchestration_active:
            return
        
        self.orchestration_active = True
        
        asyncio.create_task(self._orchestration_loop())
        asyncio.create_task(self._heartbeat_monitor())
        
        self.logger.info("Started WasmEdge orchestration")

    async def _orchestration_loop(self):
        while self.orchestration_active:
            try:
                await self._process_task_queue()
                await self._balance_workloads()
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Orchestration loop error: {e}")
                self.orchestration_errors += 1
                await asyncio.sleep(5)

    async def _heartbeat_monitor(self):
        while self.orchestration_active:
            try:
                await self._check_node_health()
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def submit_task(self, task_type: str, data: Dict[str, Any], priority: int = 1) -> str:
        task_id = f"task_{int(datetime.now().timestamp() * 1000000)}"
        
        task = WorkloadTask(
            task_id=task_id,
            task_type=task_type,
            data=data,
            priority=priority,
            created_at=datetime.now()
        )
        
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)
        
        self.logger.info(f"Submitted task: {task_id} ({task_type})")
        return task_id

    async def _process_task_queue(self):
        if not self.task_queue:
            return
        
        available_nodes = [
            node for node in self.edge_nodes.values()
            if node.status == 'active' and node.workload < self.max_node_workload
        ]
        
        if not available_nodes:
            return
        
        tasks_to_process = min(len(self.task_queue), len(available_nodes))
        
        for i in range(tasks_to_process):
            task = self.task_queue.pop(0)
            node = self._select_optimal_node(available_nodes, task)
            
            if node:
                await self._assign_task_to_node(task, node)
                available_nodes.remove(node)

    def _select_optimal_node(self, available_nodes: List[EdgeNode], task: WorkloadTask) -> Optional[EdgeNode]:
        if not available_nodes:
            return None
        
        best_node = None
        best_score = float('inf')
        
        for node in available_nodes:
            score = (
                node.workload * 0.4 +
                node.performance_metrics.get('cpu_usage', 0) * 0.3 +
                node.performance_metrics.get('average_response_time', 0) * 0.3
            )
            
            if score < best_score:
                best_score = score
                best_node = node
        
        return best_node

    async def _assign_task_to_node(self, task: WorkloadTask, node: EdgeNode):
        try:
            task.assigned_node = node.node_id
            task.status = 'assigned'
            
            node.workload += 1
            
            if self.docker_client:
                container = self.docker_client.containers.get(node.container_id)
                
                task_data_json = json.dumps(task.data)
                
                if task.task_type == 'news_processing':
                    cmd = f'echo \'{task_data_json}\' | wasmedge /wasm_modules/nlp_processor.wasm'
                elif task.task_type == 'relevance_scoring':
                    cmd = f'echo \'{task_data_json}\' | wasmedge /wasm_modules/relevance_scorer.wasm'
                elif task.task_type == 'sentiment_analysis':
                    cmd = f'echo \'{task_data_json}\' | wasmedge /wasm_modules/news_sentiment_analyzer.wasm'
                else:
                    cmd = f'echo \'{task_data_json}\' | wasmedge /wasm_modules/news_sentiment_analyzer.wasm'
                
                exec_result = container.exec_run(cmd, capture_output=True)
                
                if exec_result.exit_code == 0:
                    task.status = 'completed'
                    result_data = json.loads(exec_result.output.decode())
                    task.data['result'] = result_data
                    
                    self.completed_tasks.append(task)
                    self.tasks_processed += 1
                    
                    node.performance_metrics['tasks_completed'] += 1
                else:
                    task.status = 'failed'
                    task.data['error'] = exec_result.output.decode()
                    self.orchestration_errors += 1
                
                node.workload = max(0, node.workload - 1)
                
            else:
                task.status = 'completed'
                task.data['result'] = {'mock': 'result', 'processed_by': node.node_id}
                self.completed_tasks.append(task)
                self.tasks_processed += 1
                
                node.workload = max(0, node.workload - 1)
            
            self.logger.info(f"Task {task.task_id} processed by node {node.node_id}")
            
        except Exception as e:
            self.logger.error(f"Task assignment failed: {e}")
            task.status = 'failed'
            task.data['error'] = str(e)
            node.workload = max(0, node.workload - 1)
            self.orchestration_errors += 1

    async def _balance_workloads(self):
        if len(self.edge_nodes) < 2:
            return
        
        nodes = list(self.edge_nodes.values())
        nodes.sort(key=lambda n: n.workload)
        
        min_workload_node = nodes[0]
        max_workload_node = nodes[-1]
        
        workload_diff = max_workload_node.workload - min_workload_node.workload
        
        if workload_diff > 3:
            self.logger.info(f"Workload imbalance detected: {max_workload_node.node_id} ({max_workload_node.workload}) vs {min_workload_node.node_id} ({min_workload_node.workload})")

    async def _check_node_health(self):
        current_time = datetime.now()
        
        for node_id, node in list(self.edge_nodes.items()):
            try:
                if self.docker_client:
                    container = self.docker_client.containers.get(node.container_id)
                    container.reload()
                    
                    if container.status != 'running':
                        node.status = 'failed'
                        self.logger.warning(f"Node {node_id} is not running: {container.status}")
                        continue
                
                time_since_heartbeat = (current_time - node.last_heartbeat).total_seconds()
                
                if time_since_heartbeat > self.heartbeat_interval * 2:
                    node.status = 'unhealthy'
                    self.logger.warning(f"Node {node_id} missed heartbeat")
                else:
                    node.status = 'active'
                    node.last_heartbeat = current_time
                
            except Exception as e:
                self.logger.error(f"Health check failed for node {node_id}: {e}")
                node.status = 'failed'

    async def get_cluster_status(self) -> Dict[str, Any]:
        total_nodes = len(self.edge_nodes)
        active_nodes = len([n for n in self.edge_nodes.values() if n.status == 'active'])
        total_workload = sum(n.workload for n in self.edge_nodes.values())
        
        return {
            'cluster_size': total_nodes,
            'active_nodes': active_nodes,
            'unhealthy_nodes': total_nodes - active_nodes,
            'total_workload': total_workload,
            'pending_tasks': len(self.task_queue),
            'completed_tasks': len(self.completed_tasks),
            'tasks_processed': self.tasks_processed,
            'orchestration_errors': self.orchestration_errors,
            'orchestration_active': self.orchestration_active,
            'nodes': [
                {
                    'node_id': node.node_id,
                    'status': node.status,
                    'workload': node.workload,
                    'wasm_modules': len(node.wasm_modules),
                    'tasks_completed': node.performance_metrics.get('tasks_completed', 0),
                    'last_heartbeat': node.last_heartbeat.isoformat()
                }
                for node in self.edge_nodes.values()
            ],
            'timestamp': datetime.now().isoformat()
        }

    async def scale_cluster(self, target_size: int) -> Dict[str, Any]:
        current_size = len(self.edge_nodes)
        
        if target_size == current_size:
            return {
                'action': 'no_scaling_needed',
                'current_size': current_size,
                'target_size': target_size
            }
        elif target_size > current_size:
            return await self._scale_up(target_size - current_size)
        else:
            return await self._scale_down(current_size - target_size)

    async def _scale_up(self, additional_nodes: int) -> Dict[str, Any]:
        deployment_results = await self.deploy_wasm_edge_cluster(additional_nodes)
        
        return {
            'action': 'scale_up',
            'nodes_added': len(deployment_results['deployed_nodes']),
            'deployment_errors': len(deployment_results['deployment_errors']),
            'new_cluster_size': len(self.edge_nodes),
            'timestamp': datetime.now().isoformat()
        }

    async def _scale_down(self, nodes_to_remove: int) -> Dict[str, Any]:
        nodes_removed = 0
        removal_errors = []
        
        nodes_to_shutdown = list(self.edge_nodes.values())[:nodes_to_remove]
        
        for node in nodes_to_shutdown:
            try:
                if self.docker_client:
                    container = self.docker_client.containers.get(node.container_id)
                    container.stop()
                    container.remove()
                
                del self.edge_nodes[node.node_id]
                nodes_removed += 1
                
                self.logger.info(f"Removed node: {node.node_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to remove node {node.node_id}: {e}")
                removal_errors.append({'node_id': node.node_id, 'error': str(e)})
        
        return {
            'action': 'scale_down',
            'nodes_removed': nodes_removed,
            'removal_errors': len(removal_errors),
            'new_cluster_size': len(self.edge_nodes),
            'timestamp': datetime.now().isoformat()
        }

    async def shutdown(self):
        self.orchestration_active = False
        
        for node_id, node in list(self.edge_nodes.items()):
            try:
                if self.docker_client:
                    container = self.docker_client.containers.get(node.container_id)
                    container.stop()
                    container.remove()
                
                self.logger.info(f"Shutdown edge node: {node_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to shutdown node {node_id}: {e}")
        
        self.edge_nodes.clear()
        
        if self.ray_cluster and ray.is_initialized():
            ray.shutdown()
        
        if self.docker_client:
            self.docker_client.close()
        
        if self.distributed_processor:
            await self.distributed_processor.shutdown()
        
        if self.wasm_pipeline:
            await self.wasm_pipeline.shutdown()
        
        if self.edge_processor:
            await self.edge_processor.shutdown()

async def main():
    config = {
        'build_dir': '/tmp/wasm_builds',
        'output_dir': '/tmp/wasm_output',
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
        'heartbeat_interval': 30,
        'max_node_workload': 10
    }
    
    orchestrator = WasmEdgeOrchestrator(config)
    await orchestrator.initialize()
    
    deployment_results = await orchestrator.deploy_wasm_edge_cluster(3)
    
    print(f"WasmEdge Orchestration Results:")
    print(f"- Deployed nodes: {len(deployment_results['deployed_nodes'])}")
    print(f"- Deployment errors: {len(deployment_results['deployment_errors'])}")
    print(f"- Cluster size: {deployment_results['cluster_size']}")
    
    if deployment_results['cluster_size'] > 0:
        task_ids = []
        
        for i in range(5):
            task_id = await orchestrator.submit_task(
                'news_processing',
                {
                    'news_id': f'test_{i:03d}',
                    'source': 'reuters',
                    'full_text': f'Test news article {i+1} for WASM processing',
                    'relevance_score': 0.7,
                    'sentiment_score': 0.3
                },
                priority=i % 3 + 1
            )
            task_ids.append(task_id)
        
        await asyncio.sleep(10)
        
        status = await orchestrator.get_cluster_status()
        print(f"\nCluster Status:")
        print(f"- Active nodes: {status['active_nodes']}/{status['cluster_size']}")
        print(f"- Total workload: {status['total_workload']}")
        print(f"- Pending tasks: {status['pending_tasks']}")
        print(f"- Completed tasks: {status['completed_tasks']}")
        print(f"- Tasks processed: {status['tasks_processed']}")
        
        scale_results = await orchestrator.scale_cluster(5)
        print(f"\nScaling Results: {scale_results['action']}")
        if scale_results['action'] == 'scale_up':
            print(f"- Nodes added: {scale_results['nodes_added']}")
    
    await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

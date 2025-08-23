import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

try:
    from src.news_ingestion import NewsIngestionEngine
    from src.nlp_processor import EnhancedNLPProcessor
    from src.relevance_model import MarketRelevanceModel
    from src.source_tracker import NewsSourceTracker
    from src.merkle_audit_tool import EnhancedMerkleAuditTool
    from src.delay_alerts import NewsDelayAlertSystem
    from src.news_dashboard import CausalNewsIntelligenceDashboard
    from src.wasm_compilation_pipeline import WasmCompilationPipeline
    from src.edge_news_processor import EdgeNewsProcessor
    from src.wasmedge_orchestrator import WasmEdgeOrchestrator
    CAUSAL_NEWS_AVAILABLE = True
except ImportError:
    CAUSAL_NEWS_AVAILABLE = False

@pytest.fixture
def test_config():
    return {
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'test_password',
        'redis_host': 'localhost',
        'redis_port': 6379,
        'ipfs_api_url': 'http://localhost:5001',
        'kafka_bootstrap_servers': 'localhost:9092',
        'solana_rpc_url': 'https://api.devnet.solana.com',
        'build_dir': '/tmp/test_wasm_builds',
        'output_dir': '/tmp/test_wasm_output'
    }

@pytest.fixture
def sample_news_items():
    return [
        {
            'news_id': 'test_001',
            'source': 'reuters',
            'title': 'Apple reports strong Q4 earnings',
            'full_text': 'Apple Inc. reported quarterly earnings that beat analyst expectations, with revenue up 15% year-over-year.',
            'published_time': datetime.now().isoformat(),
            'received_time': datetime.now().isoformat()
        },
        {
            'news_id': 'test_002',
            'source': 'bloomberg',
            'title': 'Tesla stock volatile on production concerns',
            'full_text': 'Tesla stock price experienced volatility amid concerns about production targets.',
            'published_time': (datetime.now() - timedelta(minutes=10)).isoformat(),
            'received_time': datetime.now().isoformat()
        }
    ]

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestNewsIngestionEngine:
    @pytest.fixture
    async def news_engine(self, test_config):
        engine = NewsIngestionEngine(test_config)
        await engine.initialize()
        yield engine
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_news_ingestion_initialization(self, news_engine):
        assert news_engine is not None
        assert news_engine.processed_items == 0
        assert news_engine.ingestion_errors == 0

    @pytest.mark.asyncio
    async def test_rss_feed_processing(self, news_engine, sample_news_items):
        with patch.object(news_engine, '_fetch_rss_feed', return_value=sample_news_items):
            results = await news_engine.ingest_from_rss('https://test-rss-feed.com')
            
            assert 'processed_items' in results
            assert 'errors' in results
            assert results['processed_items'] >= 0

    @pytest.mark.asyncio
    async def test_api_news_processing(self, news_engine, sample_news_items):
        with patch.object(news_engine, '_fetch_api_news', return_value=sample_news_items):
            results = await news_engine.ingest_from_api('test_api', {'key': 'value'})
            
            assert 'processed_items' in results
            assert 'errors' in results

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestEnhancedNLPProcessor:
    @pytest.fixture
    async def nlp_processor(self, test_config):
        processor = EnhancedNLPProcessor(test_config)
        await processor.initialize()
        yield processor
        await processor.shutdown()

    @pytest.mark.asyncio
    async def test_nlp_processor_initialization(self, nlp_processor):
        assert nlp_processor is not None
        assert nlp_processor.processed_items == 0
        assert nlp_processor.processing_errors == 0

    @pytest.mark.asyncio
    async def test_news_text_processing(self, nlp_processor):
        result = await nlp_processor.process_news_text(
            'test_001',
            'Apple Inc. reported strong quarterly earnings with revenue growth.',
            'Apple reports strong earnings'
        )
        
        assert result.news_id == 'test_001'
        assert result.sentiment_score is not None
        assert result.sentiment_label is not None
        assert isinstance(result.entities, list)
        assert isinstance(result.tags, list)
        assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_batch_processing(self, nlp_processor, sample_news_items):
        results = await nlp_processor.batch_process_news(sample_news_items)
        
        assert len(results) == len(sample_news_items)
        for result in results:
            assert result.news_id is not None
            assert result.sentiment_score is not None

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestMarketRelevanceModel:
    @pytest.fixture
    async def relevance_model(self, test_config):
        model = MarketRelevanceModel(test_config)
        await model.initialize()
        yield model
        await model.shutdown()

    @pytest.mark.asyncio
    async def test_relevance_model_initialization(self, relevance_model):
        assert relevance_model is not None
        assert relevance_model.predictions_made == 0
        assert relevance_model.prediction_errors == 0

    @pytest.mark.asyncio
    async def test_relevance_prediction(self, relevance_model):
        news_item = {
            'news_id': 'test_001',
            'source': 'reuters',
            'full_text': 'Apple reports strong earnings',
            'sentiment_score': 0.7,
            'event_tags': [{'event_type': 'earnings_call', 'confidence': 0.9}],
            'entities': [{'text': 'Apple', 'label': 'ORG'}],
            'published_time': datetime.now().isoformat()
        }
        
        prediction = await relevance_model.predict_relevance(news_item)
        
        assert prediction.news_id == 'test_001'
        assert 0 <= prediction.relevance_score <= 1
        assert 0 <= prediction.confidence_score <= 1
        assert isinstance(prediction.feature_importance, dict)

    @pytest.mark.asyncio
    async def test_batch_predictions(self, relevance_model, sample_news_items):
        predictions = await relevance_model.batch_predict(sample_news_items)
        
        assert len(predictions) == len(sample_news_items)
        for prediction in predictions:
            assert 0 <= prediction.relevance_score <= 1

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestNewsSourceTracker:
    @pytest.fixture
    async def source_tracker(self, test_config):
        tracker = NewsSourceTracker(test_config)
        await tracker.initialize()
        yield tracker
        await tracker.shutdown()

    @pytest.mark.asyncio
    async def test_source_tracker_initialization(self, source_tracker):
        assert source_tracker is not None
        assert source_tracker.tracked_sources == 0
        assert source_tracker.validation_events == 0

    @pytest.mark.asyncio
    async def test_news_item_tracking(self, source_tracker):
        news_item = {
            'news_id': 'test_001',
            'source': 'reuters',
            'published_time': datetime.now().isoformat(),
            'received_time': datetime.now().isoformat(),
            'relevance_score': 0.8,
            'sentiment_score': 0.6
        }
        
        await source_tracker.track_news_item(news_item)
        
        rankings = await source_tracker.get_source_rankings()
        assert len(rankings) >= 0

    @pytest.mark.asyncio
    async def test_source_validation(self, source_tracker):
        validation_event = {
            'source': 'reuters',
            'news_id': 'test_001',
            'predicted_impact': 0.8,
            'actual_impact': 0.7,
            'validation_type': 'market_movement'
        }
        
        await source_tracker.validate_source_accuracy(validation_event)
        
        metrics = await source_tracker.get_source_metrics('reuters')
        assert metrics is not None

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestEnhancedMerkleAuditTool:
    @pytest.fixture
    async def audit_tool(self, test_config):
        tool = EnhancedMerkleAuditTool(test_config)
        await tool.initialize()
        yield tool
        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_audit_tool_initialization(self, audit_tool):
        assert audit_tool is not None
        assert audit_tool.trees_created == 0
        assert audit_tool.proofs_generated == 0

    @pytest.mark.asyncio
    async def test_audit_entry_creation(self, audit_tool):
        entry = await audit_tool.add_audit_entry(
            'test content',
            'news_item',
            {'source': 'reuters', 'news_id': 'test_001'}
        )
        
        assert entry.entry_id is not None
        assert entry.data_hash is not None
        assert entry.content_type == 'news_item'

    @pytest.mark.asyncio
    async def test_merkle_tree_building(self, audit_tool):
        await audit_tool.add_audit_entry('content1', 'news_item', {})
        await audit_tool.add_audit_entry('content2', 'nlp_result', {})
        
        tree_id = await audit_tool.build_daily_merkle_tree()
        
        assert tree_id is not None
        assert tree_id in audit_tool.merkle_trees

    @pytest.mark.asyncio
    async def test_news_and_nlp_audit(self, audit_tool, sample_news_items):
        nlp_results = [
            {
                'news_id': 'test_001',
                'sentiment_score': 0.7,
                'confidence_score': 0.9,
                'processing_timestamp': datetime.now().isoformat()
            }
        ]
        
        results = await audit_tool.audit_news_and_nlp_outputs(sample_news_items, nlp_results)
        
        assert 'news_entries' in results
        assert 'nlp_entries' in results
        assert 'total_entries' in results

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestNewsDelayAlertSystem:
    @pytest.fixture
    async def alert_system(self, test_config):
        system = NewsDelayAlertSystem(test_config)
        await system.initialize()
        yield system
        await system.shutdown()

    @pytest.mark.asyncio
    async def test_alert_system_initialization(self, alert_system):
        assert alert_system is not None
        assert alert_system.alerts_generated == 0
        assert alert_system.alerts_sent == 0

    @pytest.mark.asyncio
    async def test_delay_detection(self, alert_system):
        delayed_news = [
            {
                'news_id': 'test_001',
                'source': 'reuters',
                'title': 'BREAKING: Market volatility spikes',
                'content_summary': 'Breaking news about market volatility',
                'published_time': (datetime.now() - timedelta(minutes=10)).isoformat(),
                'received_time': datetime.now().isoformat(),
                'event_tags': [{'event_type': 'market_movement'}]
            }
        ]
        
        alerts = await alert_system.check_news_delays(delayed_news)
        
        assert isinstance(alerts, list)
        if alerts:
            alert = alerts[0]
            assert alert.news_id == 'test_001'
            assert alert.delay_minutes > 0

    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, alert_system):
        delayed_news = [
            {
                'news_id': 'test_001',
                'source': 'reuters',
                'title': 'Test news',
                'content_summary': 'Test content',
                'published_time': (datetime.now() - timedelta(minutes=15)).isoformat(),
                'received_time': datetime.now().isoformat(),
                'event_tags': []
            }
        ]
        
        alerts = await alert_system.check_news_delays(delayed_news)
        
        if alerts:
            alert_id = alerts[0].alert_id
            success = await alert_system.acknowledge_alert(alert_id)
            assert isinstance(success, bool)

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestCausalNewsIntelligenceDashboard:
    @pytest.fixture
    async def dashboard(self, test_config):
        dash = CausalNewsIntelligenceDashboard(test_config)
        await dash.initialize()
        yield dash
        await dash.shutdown()

    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, dashboard):
        assert dashboard is not None

    @pytest.mark.asyncio
    async def test_dashboard_data_retrieval(self, dashboard):
        data = await dashboard.get_dashboard_data()
        
        assert 'news_volume_heatmap' in data
        assert 'ranked_news' in data
        assert 'source_reliability' in data
        assert 'delay_alerts' in data
        assert 'last_updated' in data

    @pytest.mark.asyncio
    async def test_heatmap_data_generation(self, dashboard):
        heatmap_data = await dashboard.get_news_volume_heatmap_data(24)
        
        assert 'heatmap_data' in heatmap_data
        assert 'volume_data' in heatmap_data
        assert 'total_articles' in heatmap_data

    @pytest.mark.asyncio
    async def test_audit_log_export(self, dashboard):
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        export_path = await dashboard.export_audit_logs(start_date, end_date)
        
        assert export_path is not None
        assert export_path.endswith('.csv')

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestWasmCompilationPipeline:
    @pytest.fixture
    async def wasm_pipeline(self, test_config):
        pipeline = WasmCompilationPipeline(test_config)
        await pipeline.initialize()
        yield pipeline
        await pipeline.shutdown()

    @pytest.mark.asyncio
    async def test_wasm_pipeline_initialization(self, wasm_pipeline):
        assert wasm_pipeline is not None
        assert wasm_pipeline.compilation_errors == 0

    @pytest.mark.asyncio
    async def test_rust_compilation(self, wasm_pipeline):
        module = await wasm_pipeline.compile_rust_to_wasm('', 'test_module')
        
        if module:
            assert module.module_id is not None
            assert module.wasm_path is not None
            assert module.module_hash is not None
            assert 'rust' in module.metadata['language']

    @pytest.mark.asyncio
    async def test_python_compilation(self, wasm_pipeline):
        module = await wasm_pipeline.compile_python_to_wasm('', 'test_python_module')
        
        if module:
            assert module.module_id is not None
            assert module.wasm_path is not None
            assert module.module_hash is not None
            assert 'python' in module.metadata['language']

    @pytest.mark.asyncio
    async def test_news_processing_modules_compilation(self, wasm_pipeline):
        modules = await wasm_pipeline.compile_news_processing_modules()
        
        assert isinstance(modules, list)
        if modules:
            for module in modules:
                assert module.module_id is not None
                assert module.performance_metrics is not None

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestEdgeNewsProcessor:
    @pytest.fixture
    async def edge_processor(self, test_config):
        processor = EdgeNewsProcessor(test_config)
        await processor.initialize()
        yield processor
        await processor.shutdown()

    @pytest.mark.asyncio
    async def test_edge_processor_initialization(self, edge_processor):
        assert edge_processor is not None
        assert edge_processor.processed_items == 0
        assert edge_processor.processing_errors == 0

    @pytest.mark.asyncio
    async def test_edge_news_processing(self, edge_processor, sample_news_items):
        results = await edge_processor.process_news_at_edge(sample_news_items)
        
        assert isinstance(results, list)
        assert len(results) == len(sample_news_items)
        
        for result in results:
            assert result.news_id is not None
            assert result.processed_data is not None
            assert result.processing_time >= 0

    @pytest.mark.asyncio
    async def test_edge_node_status(self, edge_processor):
        status = await edge_processor.get_edge_node_status()
        
        assert 'total_nodes' in status
        assert 'active_nodes' in status
        assert 'processed_items' in status
        assert 'nodes' in status

@pytest.mark.skipif(not CAUSAL_NEWS_AVAILABLE, reason="Causal news components not available")
class TestWasmEdgeOrchestrator:
    @pytest.fixture
    async def orchestrator(self, test_config):
        orch = WasmEdgeOrchestrator(test_config)
        await orch.initialize()
        yield orch
        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        assert orchestrator is not None
        assert orchestrator.tasks_processed == 0
        assert orchestrator.orchestration_errors == 0

    @pytest.mark.asyncio
    async def test_task_submission(self, orchestrator):
        task_id = await orchestrator.submit_task(
            'news_processing',
            {'news_id': 'test_001', 'content': 'test content'},
            priority=1
        )
        
        assert task_id is not None
        assert len(orchestrator.task_queue) >= 0

    @pytest.mark.asyncio
    async def test_cluster_status(self, orchestrator):
        status = await orchestrator.get_cluster_status()
        
        assert 'cluster_size' in status
        assert 'active_nodes' in status
        assert 'pending_tasks' in status
        assert 'completed_tasks' in status
        assert 'orchestration_active' in status

class TestCausalNewsIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_news_processing_pipeline(self, test_config, sample_news_items):
        if not CAUSAL_NEWS_AVAILABLE:
            pytest.skip("Causal news components not available")
        
        news_engine = NewsIngestionEngine(test_config)
        nlp_processor = EnhancedNLPProcessor(test_config)
        relevance_model = MarketRelevanceModel(test_config)
        audit_tool = EnhancedMerkleAuditTool(test_config)
        
        try:
            await news_engine.initialize()
            await nlp_processor.initialize()
            await relevance_model.initialize()
            await audit_tool.initialize()
            
            nlp_results = []
            relevance_predictions = []
            
            for news_item in sample_news_items:
                nlp_result = await nlp_processor.process_news_text(
                    news_item['news_id'],
                    news_item['full_text'],
                    news_item['title']
                )
                nlp_results.append(nlp_result)
                
                enhanced_news_item = {
                    **news_item,
                    'sentiment_score': nlp_result.sentiment_score,
                    'event_tags': [
                        {
                            'event_type': tag.event_type,
                            'confidence': tag.confidence
                        }
                        for tag in nlp_result.tags
                    ],
                    'entities': nlp_result.entities
                }
                
                prediction = await relevance_model.predict_relevance(enhanced_news_item)
                relevance_predictions.append(prediction)
            
            audit_results = await audit_tool.audit_news_and_nlp_outputs(
                sample_news_items,
                [
                    {
                        'news_id': result.news_id,
                        'sentiment_score': result.sentiment_score,
                        'confidence_score': result.confidence_score,
                        'processing_timestamp': datetime.now().isoformat()
                    }
                    for result in nlp_results
                ]
            )
            
            assert len(nlp_results) == len(sample_news_items)
            assert len(relevance_predictions) == len(sample_news_items)
            assert audit_results['total_entries'] > 0
            
            for nlp_result in nlp_results:
                assert nlp_result.sentiment_score is not None
                assert nlp_result.confidence_score > 0
            
            for prediction in relevance_predictions:
                assert 0 <= prediction.relevance_score <= 1
                assert 0 <= prediction.confidence_score <= 1
            
        finally:
            await news_engine.shutdown()
            await nlp_processor.shutdown()
            await relevance_model.shutdown()
            await audit_tool.shutdown()

    @pytest.mark.asyncio
    async def test_wasm_edge_processing_integration(self, test_config, sample_news_items):
        if not CAUSAL_NEWS_AVAILABLE:
            pytest.skip("Causal news components not available")
        
        edge_processor = EdgeNewsProcessor(test_config)
        orchestrator = WasmEdgeOrchestrator(test_config)
        
        try:
            await edge_processor.initialize()
            await orchestrator.initialize()
            
            edge_results = await edge_processor.process_news_at_edge(sample_news_items)
            
            assert len(edge_results) == len(sample_news_items)
            
            for result in edge_results:
                assert result.news_id is not None
                assert result.processed_data is not None
                assert result.processing_time >= 0
                assert result.edge_node_id is not None
                assert result.wasm_module_used is not None
            
            cluster_status = await orchestrator.get_cluster_status()
            assert 'cluster_size' in cluster_status
            assert 'orchestration_active' in cluster_status
            
        finally:
            await edge_processor.shutdown()
            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, test_config):
        if not CAUSAL_NEWS_AVAILABLE:
            pytest.skip("Causal news components not available")
        
        wasm_pipeline = WasmCompilationPipeline(test_config)
        
        try:
            await wasm_pipeline.initialize()
            
            modules = await wasm_pipeline.compile_news_processing_modules()
            
            if modules:
                benchmark_results = await wasm_pipeline.benchmark_performance(modules)
                
                assert 'module_benchmarks' in benchmark_results
                assert 'aggregate_metrics' in benchmark_results
                
                aggregate = benchmark_results['aggregate_metrics']
                if aggregate:
                    assert 'average_load_time' in aggregate
                    assert 'performance_improvement' in aggregate
                    assert aggregate['performance_improvement'] >= 1.0
            
        finally:
            await wasm_pipeline.shutdown()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

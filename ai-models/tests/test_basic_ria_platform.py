"""
Basic tests for RIA platform components without external dependencies
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

def test_platform_imports():
    """Test that platform modules can be imported"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from src.comprehensive_ria_platform import ComprehensiveRIAPlatform, PlatformMode
        assert ComprehensiveRIAPlatform is not None
        assert PlatformMode is not None
        print("✓ Platform imports successful")
    except ImportError as e:
        pytest.fail(f"Platform import failed: {e}")

def test_platform_mode_enum():
    """Test platform mode enumeration"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from src.comprehensive_ria_platform import PlatformMode
    
    assert PlatformMode.DEVELOPMENT.value == "development"
    assert PlatformMode.TESTING.value == "testing"
    assert PlatformMode.PRODUCTION.value == "production"
    print("✓ Platform modes defined correctly")

@pytest.mark.asyncio
async def test_platform_initialization_basic():
    """Test basic platform initialization without external dependencies"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from src.comprehensive_ria_platform import ComprehensiveRIAPlatform
    
    config = {
        'mode': 'testing',
        'data_engine': {'mmap_file_path': '/tmp/test.dat'},
        'nats': {'nats_servers': ['nats://localhost:4222']},
        'weaviate': {'weaviate_url': 'http://localhost:8080'}
    }
    
    platform = ComprehensiveRIAPlatform(config)
    
    assert platform.config == config
    assert platform.mode.value == 'testing'
    assert platform.focus_weight == 0.6  # 60% portfolio focus
    assert platform.target_latency_ms == 1.0
    assert platform.target_throughput_eps == 20000
    
    print("✓ Platform basic initialization successful")

@pytest.mark.asyncio
async def test_platform_initialization_with_mocks():
    """Test platform initialization with mocked dependencies"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from src.comprehensive_ria_platform import ComprehensiveRIAPlatform
    
    config = {
        'mode': 'testing',
        'data_engine': {'mmap_file_path': '/tmp/test.dat'},
        'nats': {'nats_servers': ['nats://localhost:4222']},
        'weaviate': {'weaviate_url': 'http://localhost:8080'}
    }
    
    platform = ComprehensiveRIAPlatform(config)
    
    success = await platform.initialize()
    
    assert success == True
    assert platform.is_initialized == True
    
    await platform.shutdown()
    assert platform.is_initialized == False
    
    print("✓ Platform initialization with mocks successful")

def test_specialized_agents_imports():
    """Test that specialized agents can be imported"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from src.ria_specialized_agents import ComplianceAgent, RiskAgent, DetectorAgent, BaseRIAAgent
        assert ComplianceAgent is not None
        assert RiskAgent is not None
        assert DetectorAgent is not None
        assert BaseRIAAgent is not None
        print("✓ Specialized agents imports successful")
    except ImportError as e:
        pytest.fail(f"Specialized agents import failed: {e}")

def test_compliance_engine_imports():
    """Test that compliance engine can be imported"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from src.ria_compliance_engine import RIAComplianceEngine, ComplianceStatus, ViolationType
        assert RIAComplianceEngine is not None
        assert ComplianceStatus is not None
        assert ViolationType is not None
        print("✓ Compliance engine imports successful")
    except ImportError as e:
        pytest.fail(f"Compliance engine import failed: {e}")

def test_nats_integration_imports():
    """Test that NATS integration can be imported"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from src.enhanced_nats_integration import EnhancedNATSIntegration, NATSEvent, EventPriority
        assert EnhancedNATSIntegration is not None
        assert NATSEvent is not None
        assert EventPriority is not None
        print("✓ NATS integration imports successful")
    except ImportError as e:
        pytest.fail(f"NATS integration import failed: {e}")

def test_weaviate_profiling_imports():
    """Test that Weaviate profiling can be imported"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from src.weaviate_client_profiling import WeaviateClientProfiling, ClientProfile, ClientBehavior
        assert WeaviateClientProfiling is not None
        assert ClientProfile is not None
        assert ClientBehavior is not None
        print("✓ Weaviate profiling imports successful")
    except ImportError as e:
        pytest.fail(f"Weaviate profiling import failed: {e}")

@pytest.mark.asyncio
async def test_agent_basic_functionality():
    """Test basic agent functionality"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from src.ria_specialized_agents import BaseRIAAgent, AgentStatus
    
    config = {'agent_id': 'test_agent'}
    agent = BaseRIAAgent(config)
    
    assert agent.agent_id == 'test_agent'
    assert agent.status == AgentStatus.INITIALIZING
    
    success = await agent.initialize()
    assert success == True
    assert agent.status == AgentStatus.ACTIVE
    
    metrics = agent.get_metrics()
    assert 'agent_id' in metrics
    assert 'agent_type' in metrics
    assert 'status' in metrics
    
    await agent.stop()
    assert agent.status == AgentStatus.STOPPED
    
    print("✓ Agent basic functionality successful")

def test_compliance_violation_types():
    """Test compliance violation types"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from src.ria_compliance_engine import ViolationType
    
    assert ViolationType.SUITABILITY.value == "suitability"
    assert ViolationType.RECORDKEEPING.value == "recordkeeping"
    assert ViolationType.PRIVACY.value == "privacy"
    assert ViolationType.ADVERTISING.value == "advertising"
    assert ViolationType.CUSTODY.value == "custody"
    assert ViolationType.FIDUCIARY.value == "fiduciary"
    
    print("✓ Compliance violation types defined correctly")

def test_event_priority_levels():
    """Test NATS event priority levels"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from src.enhanced_nats_integration import EventPriority
    
    assert EventPriority.CRITICAL.value == "critical"
    assert EventPriority.HIGH.value == "high"
    assert EventPriority.MEDIUM.value == "medium"
    assert EventPriority.LOW.value == "low"
    
    print("✓ Event priority levels defined correctly")

@pytest.mark.asyncio
async def test_platform_metrics_basic():
    """Test basic platform metrics functionality"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from src.comprehensive_ria_platform import ComprehensiveRIAPlatform, PlatformMetrics
    
    config = {'mode': 'testing'}
    platform = ComprehensiveRIAPlatform(config)
    
    await platform.initialize()
    
    metrics = await platform.get_platform_metrics()
    
    assert isinstance(metrics, PlatformMetrics)
    assert metrics.total_clients >= 0
    assert metrics.active_portfolios >= 0
    assert 0.0 <= metrics.system_health_score <= 1.0
    assert metrics.timestamp > 0
    
    await platform.shutdown()
    
    print("✓ Platform metrics basic functionality successful")

if __name__ == "__main__":
    test_platform_imports()
    test_platform_mode_enum()
    test_specialized_agents_imports()
    test_compliance_engine_imports()
    test_nats_integration_imports()
    test_weaviate_profiling_imports()
    test_compliance_violation_types()
    test_event_priority_levels()
    
    asyncio.run(test_platform_initialization_basic())
    asyncio.run(test_platform_initialization_with_mocks())
    asyncio.run(test_agent_basic_functionality())
    asyncio.run(test_platform_metrics_basic())
    
    print("\n✅ All basic RIA platform tests passed!")

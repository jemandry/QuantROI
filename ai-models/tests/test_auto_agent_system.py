import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from auto_agent_system import AutoAgentSystem, DataGap, GapType, ResolutionResult

@pytest.fixture
def auto_agent():
    return AutoAgentSystem()

@pytest.fixture
def sample_gap():
    return DataGap(
        gap_type=GapType.DATA_MISSING,
        symbol="AAPL",
        timeframe="1D",
        severity=0.8,
        detected_at=1234567890.0,
        context={"data_points": 0}
    )

@pytest.mark.asyncio
async def test_detect_gaps(auto_agent):
    with patch.object(auto_agent, '_analyze_symbol_timeframe', return_value=None):
        gaps = await auto_agent.detect_gaps(["AAPL"], ["1D"])
        assert isinstance(gaps, list)

@pytest.mark.asyncio
async def test_resolve_gap(auto_agent, sample_gap):
    with patch.object(auto_agent, '_execute_resolution', return_value={"data_points": 100}):
        result = await auto_agent.resolve_gap(sample_gap)
        assert isinstance(result, ResolutionResult)
        assert result.gap_id.startswith("AAPL_1D_")

@pytest.mark.asyncio
async def test_predict_vix_impact(auto_agent):
    with patch.object(auto_agent, '_fetch_current_vix', return_value=20.0):
        with patch.object(auto_agent, '_fetch_symbol_data', return_value=pd.DataFrame({'Close': [100, 101, 99]})):
            result = await auto_agent.predict_vix_impact("AAPL")
            assert 'symbol' in result
            assert 'current_vix' in result
            assert result['symbol'] == "AAPL"

def test_performance_metrics(auto_agent):
    metrics = auto_agent.get_performance_metrics()
    assert 'gaps_detected' in metrics
    assert 'gaps_resolved' in metrics
    assert 'quota_usage' in metrics

@pytest.mark.asyncio
async def test_quota_limits(auto_agent):
    auto_agent.quota_usage['daily_requests'] = auto_agent.quota_limits['daily_requests']
    
    result = await auto_agent.resolve_gap(DataGap(
        gap_type=GapType.DATA_MISSING,
        symbol="AAPL",
        timeframe="1D",
        severity=0.5,
        detected_at=1234567890.0,
        context={}
    ))
    
    assert not result.success
    assert "quota exceeded" in result.error_message

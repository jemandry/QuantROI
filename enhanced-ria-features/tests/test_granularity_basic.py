"""
Basic functionality test for enhanced granularity limiter system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage-granularity'))

from granularity_limiter import GranularityLimiter, MetricRequest
from datetime import datetime, timedelta
import pandas as pd

def test_basic_functionality():
    """Test basic enhanced granularity limiter functionality"""
    
    print("🔧 Testing Enhanced Granularity Limiter...")
    
    limiter = GranularityLimiter()
    print('✅ GranularityLimiter initialized successfully')
    
    data = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
    validated_data = limiter.validate_index(data)
    print(f'✅ Index validation: {type(validated_data.index).__name__}')
    assert isinstance(validated_data.index, pd.DatetimeIndex)
    
    request = MetricRequest(
        metric_name='volatility',
        data_resolution=timedelta(minutes=1),
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now()
    )
    result = limiter.validate_granularity(request)
    print(f'✅ Granularity validation: {result.is_valid}')
    assert result.audit_hash is not None
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=100, freq='h')
    test_data = pd.DataFrame({
        'value': range(100),
        'volume': range(1000, 1100),
        'price': [100 + i * 0.1 for i in range(100)]
    }, index=dates)
    
    rule = limiter.rules['moving_average']
    aggregated = limiter.aggregate_data_enhanced(test_data, rule, timedelta(days=1))
    print(f'✅ Enhanced aggregation: {len(test_data)} → {len(aggregated)} records')
    assert len(aggregated) <= len(test_data)
    
    metrics = limiter.get_performance_metrics()
    print(f'✅ Performance metrics: {metrics["queries_processed"]} queries processed')
    assert metrics["queries_processed"] > 0
    
    print("🎉 All basic tests passed!")
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    exit(0 if success else 1)

#!/usr/bin/env python3
"""
Simple validation script for strand creation engines
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all strand engine modules can be imported"""
    try:
        from strand_types import EventStrand, MarketStrand
        print('✅ EventStrand and MarketStrand import successful')
        
        from braided_cord_data_engine import BraidedCordDataEngine
        print('✅ BraidedCordDataEngine import successful')
        
        from event_upload_processor import EventUploadProcessor
        print('✅ EventUploadProcessor import successful')
        
        from automated_strand_creator import AutomatedStrandCreator
        print('✅ AutomatedStrandCreator import successful')
        
        return True
    except Exception as e:
        print(f'❌ Import failed: {e}')
        return False

def test_basic_functionality():
    """Test basic strand creation functionality"""
    try:
        from strand_types import EventStrand
        
        events = [
            {'timestamp_ns': 1000000000, 'type_id': 1, 'source_id': 1, 'payload': {'price': 100.0}},
            {'timestamp_ns': 1000001000, 'type_id': 1, 'source_id': 1, 'payload': {'price': 101.0}}
        ]
        
        strand = EventStrand.create_from_events(events)
        print(f'✅ EventStrand creation successful: {len(strand.timestamps_ns)} events')
        
        correlations = strand.calculate_causal_correlations()
        print(f'✅ Causal correlation calculation successful: {len(correlations)} correlations')
        
        return True
    except Exception as e:
        print(f'❌ Basic functionality test failed: {e}')
        return False

if __name__ == "__main__":
    print("🚀 Validating strand creation engines...")
    
    imports_ok = test_imports()
    functionality_ok = test_basic_functionality()
    
    if imports_ok and functionality_ok:
        print("✅ All strand creation engines validated successfully!")
        sys.exit(0)
    else:
        print("❌ Validation failed")
        sys.exit(1)

#!/usr/bin/env python3
"""
Integration check for API reliability enhancements
"""

import sys
import os
import traceback

def test_imports():
    """Test all critical imports for integration issues"""
    print("🔍 Testing imports for integration issues...")
    
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        
        from event_upload_processor import FastEventUploadProcessor, MacroLearningEngine, MicroLearningEngine
        print("✅ FastEventUploadProcessor imports successful")
        
        from api_provider_adapter import MultiProviderNewsAdapter, NewsItem
        print("✅ MultiProviderNewsAdapter imports successful")
        
        from news_ingestion_pipeline import NewsIngestionPipeline
        print("✅ NewsIngestionPipeline imports successful")
        
        config = {'test_mode': True, 'kafka_enabled': False}
        
        processor = FastEventUploadProcessor(config)
        print("✅ FastEventUploadProcessor instantiation successful")
        
        pipeline = NewsIngestionPipeline(config)
        print("✅ NewsIngestionPipeline instantiation successful")
        
        adapter = MultiProviderNewsAdapter({})
        print("✅ MultiProviderNewsAdapter instantiation successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   This indicates missing dependencies or module structure issues")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Integration Error: {e}")
        print("   This indicates compatibility issues between components")
        traceback.print_exc()
        return False

def test_existing_infrastructure():
    """Test integration with existing infrastructure"""
    print("\n🔍 Testing integration with existing infrastructure...")
    
    try:
        from automated_strand_creator import AutomatedStrandCreator
        print("✅ AutomatedStrandCreator import successful")
        
        from braided_cord_data_engine import BraidedCordDataEngine
        print("✅ BraidedCordDataEngine import successful")
        
        from unified_api_server import app
        print("✅ Unified API Server import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Infrastructure Import Error: {e}")
        print("   This indicates issues with existing infrastructure integration")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Infrastructure Integration Error: {e}")
        traceback.print_exc()
        return False

def main():
    print("🚀 Starting integration check for API reliability enhancements...")
    
    imports_ok = test_imports()
    infrastructure_ok = test_existing_infrastructure()
    
    if imports_ok and infrastructure_ok:
        print("\n🎉 All integration checks passed!")
        print("✅ API reliability enhancements are properly integrated")
        print("✅ No import or compatibility issues detected")
        return True
    else:
        print("\n❌ Integration issues detected!")
        print("   Manual investigation required for identified problems")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

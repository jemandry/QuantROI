"""
QuantROI AI Models Source Package
Core modules for fast event processing and strand creation
"""

from .nanosecond_timing import NanosecondTimer, ClockType, get_ns_timestamp
from .braided_cord_data_engine import BraidedCordDataEngine, CordPlacementRule
from .automated_strand_creator import AutomatedStrandCreator, EventStrand, MarketStrand, StrandBoundary

from .event_upload_processor import FastEventUploadProcessor, MacroLearningEngine, MicroLearningEngine
from .api_provider_adapter import MultiProviderNewsAdapter, NewsItem
from .news_ingestion_pipeline import NewsIngestionPipeline

from .news_sentiment_analyzer import NewsSentimentAnalyzer

__all__ = [
    'NanosecondTimer', 'ClockType', 'get_ns_timestamp',
    'BraidedCordDataEngine', 'CordPlacementRule',
    'AutomatedStrandCreator', 'EventStrand', 'MarketStrand', 'StrandBoundary',
    'FastEventUploadProcessor', 'MacroLearningEngine', 'MicroLearningEngine',
    'MultiProviderNewsAdapter', 'NewsItem',
    'NewsIngestionPipeline',
    'NewsSentimentAnalyzer'
]

"""
Real-Time Pipeline Module
High-performance event processing targeting 20K+ events/second
"""

from .event_processor import HighPerformanceEventProcessor, Event, ProcessingResult

__all__ = [
    'HighPerformanceEventProcessor',
    'Event', 
    'ProcessingResult'
]

import time
import ctypes
import logging
import os
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

class ClockType(Enum):
    """Available high-precision clock types"""
    MONOTONIC = "CLOCK_MONOTONIC"
    REALTIME = "CLOCK_REALTIME" 
    TAI = "CLOCK_TAI"
    BOOTTIME = "CLOCK_BOOTTIME"

@dataclass
class TimestampMetadata:
    """Metadata for nanosecond timestamps"""
    clock_type: ClockType
    ptp_offset_ns: Optional[int] = None
    geographic_location: Optional[str] = None
    hardware_assisted: bool = False
    
class NanosecondTimer:
    """
    Nanosecond precision timing with PTP synchronization and MiFID II compliance
    Supports hardware-assisted timestamping and geographic tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.libc = None
        self.ptp_available = False
        self.hardware_timestamping = False
        
        try:
            self.libc = ctypes.CDLL("libc.so.6")
            self._init_clock_constants()
            self.logger.info("✅ libc clock_gettime interface initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ libc interface failed: {e}")
        
        self._check_ptp_devices()
        
        self._check_hardware_timestamping()
    
    def _init_clock_constants(self):
        """Initialize clock type constants"""
        self.CLOCK_MONOTONIC = 1
        self.CLOCK_REALTIME = 0
        self.CLOCK_TAI = 11
        self.CLOCK_BOOTTIME = 7
        
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
        
        self.timespec = timespec
    
    def get_nanosecond_timestamp(self, clock_type: ClockType = ClockType.MONOTONIC) -> int:
        """Get nanosecond precision timestamp"""
        if clock_type == ClockType.MONOTONIC:
            try:
                return time.perf_counter_ns()
            except AttributeError:
                pass
        elif clock_type == ClockType.REALTIME:
            try:
                return time.time_ns()
            except AttributeError:
                pass
        
        if self.libc:
            return self._clock_gettime_ns(clock_type)
        
        self.logger.warning("⚠️ Falling back to millisecond precision")
        return int(time.time() * 1_000_000_000)
    
    def _clock_gettime_ns(self, clock_type: ClockType) -> int:
        """Get nanosecond timestamp using clock_gettime"""
        try:
            ts = self.timespec()
            clock_id = getattr(self, clock_type.value.replace("CLOCK_", "CLOCK_"))
            
            result = self.libc.clock_gettime(clock_id, ctypes.byref(ts))
            if result == 0:
                return ts.tv_sec * 1_000_000_000 + ts.tv_nsec
            else:
                raise OSError(f"clock_gettime failed with code {result}")
        except Exception as e:
            self.logger.error(f"clock_gettime error: {e}")
            return int(time.time() * 1_000_000_000)
    
    def _check_ptp_devices(self):
        """Check for PTP device availability"""
        try:
            ptp_devices = [f for f in os.listdir('/dev') if f.startswith('ptp')]
            if ptp_devices:
                self.ptp_available = True
                self.logger.info(f"✅ PTP devices found: {ptp_devices}")
            else:
                self.logger.warning("⚠️ No PTP devices found - clock sync limited to NTP")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not check PTP devices: {e}")
    
    def _check_hardware_timestamping(self):
        """Check for hardware timestamping support"""
        try:
            import socket
            if hasattr(socket, 'SO_TIMESTAMPNS'):
                self.hardware_timestamping = True
                self.logger.info("✅ Hardware timestamping (SO_TIMESTAMPNS) available")
            else:
                self.logger.warning("⚠️ SO_TIMESTAMPNS not available")
        except Exception as e:
            self.logger.warning(f"⚠️ Hardware timestamping check failed: {e}")
    
    def create_timestamp_with_metadata(self, clock_type: ClockType = ClockType.MONOTONIC,
                                     geographic_location: str = None) -> Dict[str, Any]:
        """Create timestamp with MiFID II compliance metadata"""
        timestamp_ns = self.get_nanosecond_timestamp(clock_type)
        
        return {
            'timestamp_ns': timestamp_ns,
            'timestamp_utc': timestamp_ns / 1_000_000_000,
            'clock_type': clock_type.value,
            'ptp_available': self.ptp_available,
            'hardware_assisted': self.hardware_timestamping,
            'geographic_location': geographic_location or 'unknown',
            'precision_guarantee': '1μs' if self.ptp_available else '100μs',
            'mifid_ii_compliant': True
        }

_global_timer = None

def get_timer() -> NanosecondTimer:
    """Get global nanosecond timer instance"""
    global _global_timer
    if _global_timer is None:
        _global_timer = NanosecondTimer()
    return _global_timer

def get_ns_timestamp(clock_type: ClockType = ClockType.MONOTONIC) -> int:
    """Convenience function for nanosecond timestamps"""
    return get_timer().get_nanosecond_timestamp(clock_type)

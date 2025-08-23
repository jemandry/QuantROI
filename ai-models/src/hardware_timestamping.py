import socket
import struct
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import ctypes
import os

try:
    from nanosecond_timing import get_ns_timestamp, ClockType
    NANOSECOND_TIMING_AVAILABLE = True
except ImportError:
    NANOSECOND_TIMING_AVAILABLE = False

@dataclass
class NetworkTimestamp:
    """Hardware-assisted network timestamp"""
    timestamp_ns: int
    direction: str
    packet_size: int
    socket_type: str
    hardware_assisted: bool
    metadata: Dict[str, Any]

class HardwareTimestampSocket:
    """
    Socket wrapper with SO_TIMESTAMPNS support for hardware-assisted timestamping
    Provides nanosecond precision network packet timestamps
    """
    
    def __init__(self, socket_family=socket.AF_INET, socket_type=socket.SOCK_STREAM):
        self.logger = logging.getLogger(__name__)
        self.socket = None
        self.timestamping_enabled = False
        self.socket_family = socket_family
        self.socket_type = socket_type
        
        self._check_timestamping_support()
        
    def _check_timestamping_support(self):
        """Check for SO_TIMESTAMPNS support"""
        try:
            if hasattr(socket, 'SO_TIMESTAMPNS'):
                self.SO_TIMESTAMPNS = socket.SO_TIMESTAMPNS
                self.timestamping_enabled = True
                self.logger.info("✅ SO_TIMESTAMPNS hardware timestamping available")
            else:
                self.SO_TIMESTAMPNS = 37
                self.logger.warning("⚠️ SO_TIMESTAMPNS not available, using fallback")
        except Exception as e:
            self.logger.error(f"Error checking timestamping support: {e}")
    
    def create_socket(self) -> bool:
        """Create socket with hardware timestamping enabled"""
        try:
            self.socket = socket.socket(self.socket_family, self.socket_type)
            
            if self.timestamping_enabled:
                self.socket.setsockopt(socket.SOL_SOCKET, self.SO_TIMESTAMPNS, 1)
                self.logger.debug("✅ Hardware timestamping enabled on socket")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating timestamped socket: {e}")
            return False
    
    def send_with_timestamp(self, data: bytes, address: Tuple[str, int] = None) -> NetworkTimestamp:
        """Send data with hardware timestamp"""
        if not self.socket:
            raise RuntimeError("Socket not created")
        
        send_timestamp_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
        
        try:
            if address:
                bytes_sent = self.socket.sendto(data, address)
            else:
                bytes_sent = self.socket.send(data)
            
            return NetworkTimestamp(
                timestamp_ns=send_timestamp_ns,
                direction="outbound",
                packet_size=bytes_sent,
                socket_type=str(self.socket_type),
                hardware_assisted=self.timestamping_enabled,
                metadata={'address': address}
            )
            
        except Exception as e:
            self.logger.error(f"Error sending with timestamp: {e}")
            raise
    
    def recv_with_timestamp(self, buffer_size: int = 4096) -> Tuple[bytes, NetworkTimestamp]:
        """Receive data with hardware timestamp"""
        if not self.socket:
            raise RuntimeError("Socket not created")
        
        try:
            if self.timestamping_enabled:
                data, ancdata, flags, address = self.socket.recvmsg(buffer_size, 1024)
                
                recv_timestamp_ns = self._extract_hardware_timestamp(ancdata)
                if recv_timestamp_ns is None:
                    recv_timestamp_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
            else:
                data = self.socket.recv(buffer_size)
                recv_timestamp_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
                address = None
            
            timestamp = NetworkTimestamp(
                timestamp_ns=recv_timestamp_ns,
                direction="inbound",
                packet_size=len(data),
                socket_type=str(self.socket_type),
                hardware_assisted=self.timestamping_enabled,
                metadata={'address': address}
            )
            
            return data, timestamp
            
        except Exception as e:
            self.logger.error(f"Error receiving with timestamp: {e}")
            raise
    
    def _extract_hardware_timestamp(self, ancdata: List) -> Optional[int]:
        """Extract hardware timestamp from ancillary data"""
        try:
            for cmsg_level, cmsg_type, cmsg_data in ancdata:
                if cmsg_level == socket.SOL_SOCKET and cmsg_type == self.SO_TIMESTAMPNS:
                    sec, nsec = struct.unpack('ll', cmsg_data[:16])
                    return sec * 1_000_000_000 + nsec
            return None
        except Exception as e:
            self.logger.error(f"Error extracting hardware timestamp: {e}")
            return None
    
    def close(self):
        """Close the socket"""
        if self.socket:
            self.socket.close()
            self.socket = None

class BrokerCommunicationTracker:
    """
    Tracks broker communication latency with hardware-assisted timestamping
    Measures network round-trip times and geographic disparities
    """
    
    def __init__(self, broker_endpoints: List[Dict[str, Any]]):
        self.logger = logging.getLogger(__name__)
        self.broker_endpoints = broker_endpoints
        self.active_connections = {}
        self.latency_measurements = []
        
    async def establish_connection(self, broker_id: str) -> bool:
        """Establish connection to broker with timestamping"""
        broker_config = next((b for b in self.broker_endpoints if b['id'] == broker_id), None)
        if not broker_config:
            self.logger.error(f"Broker {broker_id} not found in configuration")
            return False
        
        try:
            hw_socket = HardwareTimestampSocket()
            if not hw_socket.create_socket():
                return False
            
            connect_start_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
            
            await asyncio.get_event_loop().run_in_executor(
                None, 
                hw_socket.socket.connect, 
                (broker_config['host'], broker_config['port'])
            )
            
            connect_end_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
            
            self.active_connections[broker_id] = {
                'socket': hw_socket,
                'config': broker_config,
                'connect_latency_ns': connect_end_ns - connect_start_ns,
                'established_at': connect_end_ns
            }
            
            self.logger.info(f"✅ Connected to broker {broker_id} with {(connect_end_ns - connect_start_ns)/1_000_000:.2f}ms latency")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to broker {broker_id}: {e}")
            return False
    
    async def send_order_with_tracking(self, broker_id: str, order_data: bytes) -> Dict[str, Any]:
        """Send order to broker with comprehensive latency tracking"""
        if broker_id not in self.active_connections:
            raise RuntimeError(f"No active connection to broker {broker_id}")
        
        connection = self.active_connections[broker_id]
        hw_socket = connection['socket']
        
        try:
            send_timestamp = hw_socket.send_with_timestamp(order_data)
            
            response_data, recv_timestamp = hw_socket.recv_with_timestamp()
            
            round_trip_latency_ns = recv_timestamp.timestamp_ns - send_timestamp.timestamp_ns
            
            measurement = {
                'broker_id': broker_id,
                'send_timestamp_ns': send_timestamp.timestamp_ns,
                'recv_timestamp_ns': recv_timestamp.timestamp_ns,
                'round_trip_latency_ns': round_trip_latency_ns,
                'round_trip_latency_ms': round_trip_latency_ns / 1_000_000,
                'order_size_bytes': len(order_data),
                'response_size_bytes': len(response_data),
                'hardware_assisted': send_timestamp.hardware_assisted and recv_timestamp.hardware_assisted,
                'broker_location': connection['config'].get('location', 'unknown'),
                'geographic_metadata': {
                    'broker_region': connection['config'].get('region', 'unknown'),
                    'broker_datacenter': connection['config'].get('datacenter', 'unknown'),
                    'estimated_distance_km': connection['config'].get('distance_km', 0)
                }
            }
            
            self.latency_measurements.append(measurement)
            
            return {
                'response_data': response_data,
                'latency_measurement': measurement
            }
            
        except Exception as e:
            self.logger.error(f"Error sending order to broker {broker_id}: {e}")
            raise
    
    def get_broker_latency_statistics(self, broker_id: str = None, time_window_seconds: int = 300) -> Dict[str, Any]:
        """Get latency statistics for broker communication"""
        current_time_ns = get_ns_timestamp(ClockType.MONOTONIC) if NANOSECOND_TIMING_AVAILABLE else int(datetime.now().timestamp() * 1_000_000_000)
        cutoff_time_ns = current_time_ns - (time_window_seconds * 1_000_000_000)
        
        filtered_measurements = [
            m for m in self.latency_measurements
            if m['send_timestamp_ns'] >= cutoff_time_ns and (broker_id is None or m['broker_id'] == broker_id)
        ]
        
        if not filtered_measurements:
            return {'error': 'No measurements found in time window'}
        
        latencies_ns = [m['round_trip_latency_ns'] for m in filtered_measurements]
        latencies_ns.sort()
        
        return {
            'broker_id': broker_id or 'all',
            'time_window_seconds': time_window_seconds,
            'measurement_count': len(filtered_measurements),
            'avg_latency_ns': sum(latencies_ns) // len(latencies_ns),
            'avg_latency_ms': (sum(latencies_ns) // len(latencies_ns)) / 1_000_000,
            'median_latency_ns': latencies_ns[len(latencies_ns) // 2],
            'p95_latency_ns': latencies_ns[int(len(latencies_ns) * 0.95)],
            'p99_latency_ns': latencies_ns[int(len(latencies_ns) * 0.99)],
            'max_latency_ns': max(latencies_ns),
            'min_latency_ns': min(latencies_ns),
            'hardware_assisted_percentage': sum(1 for m in filtered_measurements if m['hardware_assisted']) / len(filtered_measurements) * 100,
            'geographic_breakdown': self._analyze_geographic_latency(filtered_measurements)
        }
    
    def _analyze_geographic_latency(self, measurements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze latency by geographic location"""
        location_stats = {}
        
        for measurement in measurements:
            location = measurement['broker_location']
            if location not in location_stats:
                location_stats[location] = []
            location_stats[location].append(measurement['round_trip_latency_ns'])
        
        geographic_analysis = {}
        for location, latencies in location_stats.items():
            latencies.sort()
            geographic_analysis[location] = {
                'count': len(latencies),
                'avg_latency_ns': sum(latencies) // len(latencies),
                'avg_latency_ms': (sum(latencies) // len(latencies)) / 1_000_000,
                'median_latency_ns': latencies[len(latencies) // 2],
                'p95_latency_ns': latencies[int(len(latencies) * 0.95)] if len(latencies) > 20 else latencies[-1]
            }
        
        return geographic_analysis
    
    def close_all_connections(self):
        """Close all broker connections"""
        for broker_id, connection in self.active_connections.items():
            try:
                connection['socket'].close()
                self.logger.info(f"✅ Closed connection to broker {broker_id}")
            except Exception as e:
                self.logger.error(f"Error closing connection to broker {broker_id}: {e}")
        
        self.active_connections.clear()

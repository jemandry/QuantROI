import asyncio
import logging
import subprocess
import re
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

@dataclass
class PTPStatus:
    """PTP synchronization status"""
    synchronized: bool
    offset_ns: int
    master_clock_id: str
    sync_accuracy_ns: int
    ptp_device: str
    last_sync_time: datetime

class PTPSynchronizer:
    """
    PTP (Precision Time Protocol) synchronization manager
    Provides sub-microsecond clock synchronization for MiFID II compliance
    """
    
    def __init__(self, ptp_device: str = None):
        self.logger = logging.getLogger(__name__)
        self.ptp_device = ptp_device
        self.ptp_available = False
        self.sync_status = None
        
        self._detect_ptp_devices()
        self._check_ptp_daemon()
    
    def _detect_ptp_devices(self):
        """Detect available PTP devices"""
        try:
            ptp_devices = [f for f in os.listdir('/dev') if f.startswith('ptp')]
            if ptp_devices:
                self.ptp_available = True
                if not self.ptp_device:
                    self.ptp_device = f"/dev/{ptp_devices[0]}"
                self.logger.info(f"✅ PTP devices found: {ptp_devices}, using {self.ptp_device}")
            else:
                self.logger.warning("⚠️ No PTP devices found - hardware PTP not available")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not detect PTP devices: {e}")
    
    def _check_ptp_daemon(self):
        """Check if PTP daemon is available"""
        try:
            result = subprocess.run(['which', 'ptp4l'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"✅ ptp4l daemon available at: {result.stdout.strip()}")
            else:
                self.logger.warning("⚠️ ptp4l daemon not found - install linuxptp package")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not check PTP daemon: {e}")
    
    async def start_ptp_synchronization(self, master_ip: str = None, slave_only: bool = True) -> bool:
        """Start PTP synchronization"""
        if not self.ptp_available:
            self.logger.warning("PTP not available - cannot start synchronization")
            return False
        
        try:
            ptp_config = self._generate_ptp_config(master_ip, slave_only)
            
            config_path = "/tmp/ptp4l.conf"
            with open(config_path, 'w') as f:
                f.write(ptp_config)
            
            cmd = ['sudo', 'ptp4l', '-f', config_path, '-i', 'eth0', '-s']
            if slave_only:
                cmd.append('-s')
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            asyncio.create_task(self._monitor_ptp_process(process))
            
            self.logger.info("✅ PTP synchronization started")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting PTP synchronization: {e}")
            return False
    
    def _generate_ptp_config(self, master_ip: str = None, slave_only: bool = True) -> str:
        """Generate PTP configuration"""
        config = """
[global]
dataset_comparison     G.8275.x
G.8275.defaultDS.localPriority     128
maxStepsRemoved        255
logAnnounceInterval    1
logSyncInterval        0
logMinDelayReqInterval 0
twoStepFlag            1
minPdelayReqInterval   0
announceReceiptTimeout 3
syncReceiptTimeout     0
delayAsymmetry         0
fault_reset_interval   4
neighborPropDelayThresh 20000000
serverOnly             0
G.8275.portDS.localPriority        128
asCapable              auto
BMCA                   ptp
inhibit_announce       0
inhibit_delay_req      0
ignore_source_id       0
"""
        
        if slave_only:
            config += "slaveOnly              1\n"
        
        if master_ip:
            config += f"masterOnly             0\npreferredMaster        {master_ip}\n"
        
        return config
    
    async def _monitor_ptp_process(self, process):
        """Monitor PTP process output"""
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                self._parse_ptp_output(line)
                
        except Exception as e:
            self.logger.error(f"Error monitoring PTP process: {e}")
    
    def _parse_ptp_output(self, line: str):
        """Parse PTP daemon output for synchronization status"""
        try:
            if "master offset" in line:
                offset_match = re.search(r'master offset\s+(-?\d+)', line)
                if offset_match:
                    offset_ns = int(offset_match.group(1))
                    
                    self.sync_status = PTPStatus(
                        synchronized=abs(offset_ns) < 100_000,
                        offset_ns=offset_ns,
                        master_clock_id="unknown",
                        sync_accuracy_ns=abs(offset_ns),
                        ptp_device=self.ptp_device,
                        last_sync_time=datetime.now()
                    )
                    
                    if abs(offset_ns) < 1_000:
                        self.logger.debug(f"✅ PTP synchronized: offset {offset_ns}ns")
                    elif abs(offset_ns) < 100_000:
                        self.logger.debug(f"⚠️ PTP sync marginal: offset {offset_ns}ns")
                    else:
                        self.logger.warning(f"❌ PTP sync poor: offset {offset_ns}ns")
            
            elif "selected best master clock" in line:
                master_match = re.search(r'selected best master clock\s+([a-f0-9.]+)', line)
                if master_match and self.sync_status:
                    self.sync_status.master_clock_id = master_match.group(1)
                    self.logger.info(f"✅ PTP master selected: {self.sync_status.master_clock_id}")
                    
        except Exception as e:
            self.logger.error(f"Error parsing PTP output: {e}")
    
    def get_sync_status(self) -> Optional[PTPStatus]:
        """Get current PTP synchronization status"""
        return self.sync_status
    
    def is_synchronized(self, max_offset_ns: int = 100_000) -> bool:
        """Check if PTP is synchronized within tolerance"""
        if not self.sync_status:
            return False
        
        return (self.sync_status.synchronized and 
                abs(self.sync_status.offset_ns) <= max_offset_ns)

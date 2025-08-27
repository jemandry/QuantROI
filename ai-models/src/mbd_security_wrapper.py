import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time
import hashlib
import json
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from sklearn.ensemble import IsolationForest
import os

class MBDSecurityWrapper:
    """
    Security wrapper for MBD processing with encryption, signature verification,
    and anomaly detection to prevent data manipulation and front-running
    """
    
    def __init__(self, mbd_processor, 
                 private_key_path: Optional[str] = None,
                 public_key_path: Optional[str] = None):
        self.mbd_processor = mbd_processor
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.ping_latency_history = []
        self.model_trained = False
        
        self.aes_key = os.urandom(32)  # 256-bit key
        
        if private_key_path and os.path.exists(private_key_path):
            with open(private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
        else:
            self.private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            
        if public_key_path and os.path.exists(public_key_path):
            with open(public_key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(), backend=default_backend()
                )
        else:
            self.public_key = self.private_key.public_key()
    
    def encrypt_payload(self, payload: bytes) -> Dict[str, Any]:
        """Encrypt MBD payload using AES encryption"""
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        padding_length = 16 - (len(payload) % 16)
        padded_payload = payload + bytes([padding_length] * padding_length)
        
        encrypted_data = encryptor.update(padded_payload) + encryptor.finalize()
        
        return {
            'encrypted_data': encrypted_data,
            'iv': iv,
            'timestamp': time.time_ns()
        }
    
    def decrypt_payload(self, encrypted_payload: Dict[str, Any]) -> bytes:
        """Decrypt MBD payload"""
        cipher = Cipher(
            algorithms.AES(self.aes_key), 
            modes.CBC(encrypted_payload['iv']), 
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(encrypted_payload['encrypted_data']) + decryptor.finalize()
        
        padding_length = decrypted_padded[-1]
        decrypted_data = decrypted_padded[:-padding_length]
        
        return decrypted_data
    
    def sign_message(self, message: bytes) -> bytes:
        """Sign message using ECDSA"""
        signature = self.private_key.sign(message, ec.ECDSA(hashes.SHA256()))
        return signature
    
    def verify_signature(self, message: bytes, signature: bytes) -> bool:
        """Verify ECDSA signature"""
        try:
            self.public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False
    
    async def detect_ping_anomalies(self, ping_latencies: List[float]) -> Dict[str, Any]:
        """Detect suspicious ping patterns that might indicate front-running"""
        if len(ping_latencies) < 10:
            return {'anomaly_detected': False, 'reason': 'insufficient_data'}
        
        recent_latencies = ping_latencies[-50:]  # Last 50 pings
        rolling_mean = np.mean(recent_latencies)
        rolling_std = np.std(recent_latencies)
        
        current_latency = ping_latencies[-1]
        deviation = abs(current_latency - rolling_mean)
        
        if deviation > 50:  # 50ms threshold
            return {
                'anomaly_detected': True,
                'anomaly_type': 'latency_spike',
                'current_latency': current_latency,
                'rolling_mean': rolling_mean,
                'deviation': deviation
            }
        
        if len(self.ping_latency_history) > 100:
            features = np.array(ping_latencies[-100:]).reshape(-1, 1)
            
            if not self.model_trained:
                self.anomaly_detector.fit(features)
                self.model_trained = True
            
            anomaly_score = self.anomaly_detector.decision_function([[current_latency]])
            is_anomaly = self.anomaly_detector.predict([[current_latency]])[0] == -1
            
            if is_anomaly:
                return {
                    'anomaly_detected': True,
                    'anomaly_type': 'pattern_anomaly',
                    'anomaly_score': float(anomaly_score[0]),
                    'current_latency': current_latency
                }
        
        return {'anomaly_detected': False}
    
    async def process_secure_mbd_stream(self, encrypted_events: List[Dict[str, Any]], 
                                      exchange: str = 'DEFAULT') -> Dict[str, Any]:
        """Process encrypted and signed MBD events with security checks"""
        start_time = time.time_ns()
        
        decrypted_events = []
        security_violations = []
        ping_latencies = []
        
        for event in encrypted_events:
            try:
                encrypted_payload = event.get('encrypted_payload')
                signature = event.get('signature')
                timestamp_ns = event.get('timestamp_ns', time.time_ns())
                
                if not encrypted_payload or not signature:
                    security_violations.append({
                        'type': 'missing_security_data',
                        'event_id': event.get('id', 'unknown')
                    })
                    continue
                
                decrypted_data = self.decrypt_payload(encrypted_payload)
                
                if not self.verify_signature(decrypted_data, signature):
                    security_violations.append({
                        'type': 'signature_verification_failed',
                        'event_id': event.get('id', 'unknown')
                    })
                    continue
                
                event_data = json.loads(decrypted_data.decode('utf-8'))
                
                current_time = time.time_ns()
                ping_latency = (current_time - timestamp_ns) / 1_000_000  # Convert to ms
                ping_latencies.append(ping_latency)
                
                decrypted_events.append(event_data)
                
            except Exception as e:
                security_violations.append({
                    'type': 'decryption_error',
                    'error': str(e),
                    'event_id': event.get('id', 'unknown')
                })
        
        if ping_latencies:
            self.ping_latency_history.extend(ping_latencies)
            if len(self.ping_latency_history) > 1000:
                self.ping_latency_history = self.ping_latency_history[-1000:]
            
            ping_anomaly = await self.detect_ping_anomalies(self.ping_latency_history)
            if ping_anomaly['anomaly_detected']:
                security_violations.append({
                    'type': 'ping_anomaly',
                    'details': ping_anomaly
                })
        
        if security_violations:
            return {
                'status': 'SECURITY_VIOLATION',
                'violations': security_violations,
                'processed_events': 0,
                'processing_halted': True
            }
        
        processing_result = await self.mbd_processor.process_mbd_stream(
            decrypted_events, exchange
        )
        
        processing_time = (time.time_ns() - start_time) / 1_000_000  # Convert to ms
        
        return {
            'status': 'SUCCESS',
            'security_overhead_ms': processing_time - processing_result.get('avg_reconstruction_latency_ns', 0) / 1_000_000,
            'ping_latencies': ping_latencies,
            'avg_ping_latency_ms': np.mean(ping_latencies) if ping_latencies else 0,
            **processing_result
        }

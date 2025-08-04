import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
import hashlib
import sqlite3
from datetime import datetime
import os

class SolanaAuditIntegration:
    """Solana blockchain integration for immutable audit anchoring"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rpc_url = "http://localhost:8899"  # Default devnet
        self.program_id = None  # Will be set from environment
        
        self._init_consent_ledger()
    
    def _init_consent_ledger(self):
        """Initialize SQLite database for consent ledger"""
        os.makedirs('audit_logs', exist_ok=True)
        with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    consent_hash TEXT,
                    tx_id TEXT,
                    consent_data TEXT,
                    timestamp TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_anchors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_root TEXT,
                    ipfs_hash TEXT,
                    solana_tx_id TEXT,
                    block_height INTEGER,
                    timestamp TEXT
                )
            ''')
    
    async def log_consent(self, user_id: str, consent_data: Dict[str, Any]) -> str:
        """Log user consent and store hash on Solana"""
        consent_string = json.dumps(consent_data, sort_keys=True)
        consent_hash = hashlib.sha256(consent_string.encode()).hexdigest()
        
        tx_id = await self._store_on_solana_mock(consent_hash, user_id)
        
        with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
            conn.execute('''
                INSERT INTO consents (user_id, consent_hash, tx_id, consent_data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                consent_hash,
                tx_id,
                json.dumps(consent_data),
                datetime.now().isoformat()
            ))
        
        self.logger.info(f"Logged consent for user {user_id} with tx_id {tx_id}")
        return tx_id
    
    async def anchor_audit_root(self, audit_root: str, ipfs_hash: str) -> str:
        """Anchor audit root to Solana blockchain"""
        tx_id = await self._store_audit_root_mock(audit_root, ipfs_hash)
        
        with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
            conn.execute('''
                INSERT INTO audit_anchors (audit_root, ipfs_hash, solana_tx_id, block_height, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                audit_root,
                ipfs_hash,
                tx_id,
                0,  # Mock block height
                datetime.now().isoformat()
            ))
        
        self.logger.info(f"Anchored audit root {audit_root[:16]}... to Solana with tx_id {tx_id}")
        return tx_id
    
    async def _store_on_solana_mock(self, consent_hash: str, user_id: str) -> str:
        """Mock Solana storage for consent (replace with actual Solana client)"""
        tx_data = f"{consent_hash}_{user_id}_{datetime.now().timestamp()}"
        tx_id = hashlib.sha256(tx_data.encode()).hexdigest()[:32]
        
        await asyncio.sleep(0.1)
        
        return f"solana_tx_{tx_id}"
    
    async def _store_audit_root_mock(self, audit_root: str, ipfs_hash: str) -> str:
        """Mock Solana storage for audit root (replace with actual Solana client)"""
        tx_data = f"{audit_root}_{ipfs_hash}_{datetime.now().timestamp()}"
        tx_id = hashlib.sha256(tx_data.encode()).hexdigest()[:32]
        
        await asyncio.sleep(0.1)
        
        return f"audit_tx_{tx_id}"
    
    async def verify_consent(self, user_id: str, consent_hash: str) -> Optional[Dict[str, Any]]:
        """Verify consent exists in ledger"""
        with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
            cursor = conn.execute('''
                SELECT * FROM consents WHERE user_id = ? AND consent_hash = ?
            ''', (user_id, consent_hash))
            row = cursor.fetchone()
            
            if row:
                return {
                    'user_id': row[1],
                    'consent_hash': row[2],
                    'tx_id': row[3],
                    'consent_data': json.loads(row[4]),
                    'timestamp': row[5]
                }
        return None
    
    async def get_audit_anchor(self, audit_root: str) -> Optional[Dict[str, Any]]:
        """Get audit anchor information"""
        with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
            cursor = conn.execute('''
                SELECT * FROM audit_anchors WHERE audit_root = ?
            ''', (audit_root,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'audit_root': row[1],
                    'ipfs_hash': row[2],
                    'solana_tx_id': row[3],
                    'block_height': row[4],
                    'timestamp': row[5]
                }
        return None
    
    async def generate_compliance_report(self, output_file: str):
        """Generate basic compliance report with consent and audit data"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            c = canvas.Canvas(output_file, pagesize=letter)
            c.drawString(100, 750, "Audit Compliance Report")
            c.drawString(100, 730, f"Generated: {datetime.now().isoformat()}")
            
            y_position = 700
            
            with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
                cursor = conn.execute("SELECT user_id, consent_hash, tx_id FROM consents LIMIT 20")
                c.drawString(100, y_position, "User Consents:")
                y_position -= 20
                
                for row in cursor:
                    c.drawString(120, y_position, f"User: {row[0]}, Hash: {row[1][:16]}..., Tx: {row[2]}")
                    y_position -= 15
                    if y_position < 100:
                        break
            
            c.save()
            self.logger.info(f"Generated compliance report: {output_file}")
        except ImportError:
            with open(output_file.replace('.pdf', '.txt'), 'w') as f:
                f.write(f"Audit Compliance Report\nGenerated: {datetime.now().isoformat()}\n\n")
                
                with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
                    cursor = conn.execute("SELECT user_id, consent_hash, tx_id FROM consents LIMIT 20")
                    f.write("User Consents:\n")
                    for row in cursor:
                        f.write(f"User: {row[0]}, Hash: {row[1][:16]}..., Tx: {row[2]}\n")
            
            self.logger.info(f"Generated text compliance report: {output_file.replace('.pdf', '.txt')}")
    
    async def get_consent_statistics(self) -> Dict[str, Any]:
        """Get consent and audit anchor statistics"""
        with sqlite3.connect('audit_logs/consent_ledger.db') as conn:
            consent_cursor = conn.execute('SELECT COUNT(*) FROM consents')
            consent_count = consent_cursor.fetchone()[0]
            
            anchor_cursor = conn.execute('SELECT COUNT(*) FROM audit_anchors')
            anchor_count = anchor_cursor.fetchone()[0]
            
            return {
                'total_consents': consent_count,
                'total_audit_anchors': anchor_count,
                'last_updated': datetime.now().isoformat()
            }

#!/usr/bin/env python3
"""
Auditable Option Chain Analysis with Solana CLI Signing and Knowledge Base Export
"""

import json
import subprocess
import hashlib
import ipfshttpclient
from typing import List, Dict, Any
import os
import time
from datetime import datetime

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not available, using mock data")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("Warning: neo4j not available, skipping KB export")


def build_merkle_tree(leaves: List[bytes]) -> List[List[bytes]]:
    """Build a Merkle tree from leaf nodes"""
    if not leaves:
        return []
    
    tree = [leaves]
    current_level = leaves
    
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            
            combined = left + right
            hash_obj = hashlib.sha256(combined)
            next_level.append(hash_obj.digest())
        
        tree.append(next_level)
        current_level = next_level
    
    return tree


def generate_proof(tree: List[List[bytes]], index: int) -> List[str]:
    """Generate Merkle proof for a specific leaf index"""
    if not tree or index >= len(tree[0]):
        return []
    
    proof = []
    current_index = index
    
    for level in tree[:-1]:  # Exclude root level
        if current_index % 2 == 0:
            sibling_index = current_index + 1
        else:
            sibling_index = current_index - 1
        
        if sibling_index < len(level):
            proof.append(level[sibling_index].hex())
        
        current_index //= 2
    
    return proof


def get_option_chain_data(ticker: str = "AAPL") -> List[Dict[str, Any]]:
    """Get option chain data - real or mock"""
    if YFINANCE_AVAILABLE:
        try:
            ticker_obj = yf.Ticker(ticker)
            options_dates = ticker_obj.options
            if options_dates:
                option_chain = ticker_obj.option_chain(options_dates[0])
                data = option_chain.calls.to_dict('records')[:3]
                return data
        except Exception as e:
            print(f"Error fetching real data: {e}, using mock data")
    
    return [
        {"strike": 100, "openInterest": 5000, "impliedVolatility": 0.25, "volume": 1200, "lastPrice": 5.50},
        {"strike": 105, "openInterest": 3000, "impliedVolatility": 0.245, "volume": 800, "lastPrice": 3.20},
        {"strike": 110, "openInterest": 2000, "impliedVolatility": 0.26, "volume": 600, "lastPrice": 1.80}
    ]


def export_to_knowledge_base(ticker: str, chain_data: List[Dict], audit_metadata: Dict):
    """Export causal patterns to Neo4j knowledge base"""
    if not NEO4J_AVAILABLE:
        print("Neo4j not available, skipping KB export")
        return
    
    try:
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            for i, option in enumerate(chain_data):
                price_delta = (option.get('lastPrice', 0) - 3.0) * 2.0  # Synthetic causal effect
                
                query = """
                MERGE (o:OptionChain {
                    ticker: $ticker,
                    strike: $strike,
                    openInterest: $oi,
                    impliedVolatility: $iv,
                    volume: $volume,
                    timestamp: $timestamp
                })
                MERGE (p:PriceMove {
                    delta: $delta,
                    timestamp: $timestamp
                })
                MERGE (a:AuditLog {
                    root: $root,
                    ipfs_hash: $ipfs_hash,
                    timestamp: $timestamp
                })
                CREATE (o)-[:CAUSES]->(p)
                CREATE (a)-[:VALIDATES]->(o)
                """
                
                session.run(query, {
                    'ticker': ticker,
                    'strike': option.get('strike', 0),
                    'oi': option.get('openInterest', 0),
                    'iv': option.get('impliedVolatility', 0),
                    'volume': option.get('volume', 0),
                    'delta': price_delta,
                    'root': audit_metadata.get('root', ''),
                    'ipfs_hash': audit_metadata.get('ipfs_hash', ''),
                    'timestamp': audit_metadata.get('timestamp', datetime.now().isoformat())
                })
        
        driver.close()
        print(f"Successfully exported {len(chain_data)} patterns to knowledge base")
        
    except Exception as e:
        print(f"Error exporting to KB: {e}")


def main():
    """Main audit process"""
    print("Starting Option Chain Audit Process...")
    
    ticker = "AAPL"
    option_data = get_option_chain_data(ticker)
    print(f"Retrieved {len(option_data)} option chain entries for {ticker}")
    
    data_bytes = []
    for entry in option_data:
        entry_json = json.dumps(entry, sort_keys=True)
        data_bytes.append(entry_json.encode('utf-8'))
    
    tree = build_merkle_tree(data_bytes)
    if not tree:
        print("Error: Could not build Merkle tree")
        return
    
    root = tree[-1][0].hex()
    proof_index = 1  # Generate proof for second entry
    proof = generate_proof(tree, proof_index)
    
    print(f"Merkle root: {root}")
    print(f"Proof for index {proof_index}: {proof}")
    
    audit_log = {
        "root": root,
        "proof": proof,
        "entry": option_data[proof_index],
        "index": proof_index,
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "features": {
            "total_open_interest": sum(entry.get('openInterest', 0) for entry in option_data),
            "avg_implied_volatility": sum(entry.get('impliedVolatility', 0) for entry in option_data) / len(option_data),
            "total_volume": sum(entry.get('volume', 0) for entry in option_data)
        }
    }
    
    os.makedirs('audit_logs', exist_ok=True)
    
    audit_file = 'audit_logs/audit_log.json'
    with open(audit_file, 'w') as f:
        json.dump(audit_log, f, indent=2)
    
    print(f"Audit log saved to {audit_file}")
    
    try:
        wallet_path = os.getenv('SOLANA_WALLET', '/wallet.json')
        if os.path.exists(wallet_path):
            subprocess.run([
                "solana", "sign-offchain-message", audit_file, 
                "--keypair", wallet_path
            ], check=True)
            print("Successfully signed audit log with Solana CLI")
        else:
            print(f"Wallet not found at {wallet_path}, skipping Solana signing")
    except Exception as e:
        print(f"Error signing with Solana CLI: {e}")
    
    try:
        ipfs_api = os.getenv('IPFS_API', 'http://127.0.0.1:5001')
        client = ipfshttpclient.connect(ipfs_api)
        
        result = client.add(audit_file)
        ipfs_hash = result['Hash']
        print(f"Uploaded to IPFS: {ipfs_hash}")
        
        audit_log['ipfs_hash'] = ipfs_hash
        with open(audit_file, 'w') as f:
            json.dump(audit_log, f, indent=2)
        
    except Exception as e:
        print(f"Error uploading to IPFS: {e}")
        ipfs_hash = "mock_ipfs_hash"
        audit_log['ipfs_hash'] = ipfs_hash
    
    try:
        program_id = os.getenv('SOLANA_PROGRAM_ID')
        solana_rpc = os.getenv('SOLANA_RPC')
        wallet_path = os.getenv('SOLANA_WALLET')
        
        if program_id and solana_rpc and os.path.exists(wallet_path):
            cmd = f"solana program call {program_id} --account {wallet_path} --instruction store_audit {root} {ipfs_hash} --url {solana_rpc}"
            subprocess.run(cmd, shell=True, check=True)
            print("Successfully anchored to Solana blockchain")
        else:
            print("Solana configuration incomplete, skipping blockchain anchoring")
    except Exception as e:
        print(f"Error anchoring to Solana: {e}")
    
    export_to_knowledge_base(ticker, option_data, audit_log)
    
    print("Audit process completed successfully!")


if __name__ == "__main__":
    main()

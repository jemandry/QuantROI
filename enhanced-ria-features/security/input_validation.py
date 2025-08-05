#!/usr/bin/env python3
"""
Input Validation and Sanitization Module
Prevents injection attacks and validates all user inputs
"""

import re
import hashlib
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator, Field
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class VoteSubmissionRequest(BaseModel):
    """Validated vote submission request"""
    voter_secret: str = Field(..., min_length=8, max_length=128)
    vote_choice: int = Field(..., ge=0, le=1)
    stake_amount: float = Field(..., gt=0, le=1000000)
    coercion_token: Optional[str] = Field(None, max_length=64)
    
    @validator('voter_secret')
    def validate_voter_secret(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Voter secret contains invalid characters')
        return v
    
    @validator('coercion_token')
    def validate_coercion_token(cls, v):
        if v and not re.match(r'^[a-fA-F0-9]+$', v):
            raise ValueError('Coercion token must be hexadecimal')
        return v

class DelegationRequest(BaseModel):
    """Validated delegation request"""
    delegator: str = Field(..., regex=r'^0x[a-fA-F0-9]{40}$')
    delegatee: str = Field(..., regex=r'^0x[a-fA-F0-9]{40}$')
    task_type: str = Field(..., min_length=1, max_length=50)
    stake_amount: float = Field(..., gt=0, le=100)
    deadline_hours: int = Field(24, ge=1, le=168)  # Max 1 week
    
    @validator('task_type')
    def validate_task_type(cls, v):
        allowed_types = ['market_analysis', 'risk_assessment', 'portfolio_optimization', 'compliance_check']
        if v not in allowed_types:
            raise ValueError(f'Task type must be one of: {allowed_types}')
        return v

class CausalAnalysisRequest(BaseModel):
    """Validated causal analysis request"""
    source_node: str = Field(..., min_length=1, max_length=100)
    target_node: str = Field(..., min_length=1, max_length=100)
    event_type: Optional[str] = Field(None, max_length=50)
    
    @validator('source_node', 'target_node')
    def validate_node_names(cls, v):
        if any(char in v for char in ['`', '"', "'", ';', '\\', '\n', '\r']):
            raise ValueError('Node names contain invalid characters')
        return v.strip()

class InputSanitizer:
    """Sanitizes and validates all user inputs"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent injection attacks"""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        if len(sanitized) > max_length:
            raise ValueError(f"Input too long (max {max_length} characters)")
        
        return sanitized.strip()
    
    @staticmethod
    def validate_ethereum_address(address: str) -> str:
        """Validate Ethereum address format"""
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            raise ValueError("Invalid Ethereum address format")
        return address.lower()
    
    @staticmethod
    def validate_hash(hash_value: str, expected_length: int = 64) -> str:
        """Validate hash format (SHA-256 by default)"""
        if not re.match(f'^[a-fA-F0-9]{{{expected_length}}}$', hash_value):
            raise ValueError(f"Invalid hash format (expected {expected_length} hex characters)")
        return hash_value.lower()
    
    @staticmethod
    def sanitize_neo4j_query_param(param: str) -> str:
        """Sanitize parameters for Neo4j queries"""
        dangerous_chars = ['`', '"', "'", ';', '\\', '\n', '\r', '$', '{', '}']
        sanitized = param
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()
    
    @staticmethod
    def validate_numeric_range(value: Union[int, float], min_val: float, max_val: float) -> Union[int, float]:
        """Validate numeric value is within acceptable range"""
        if not isinstance(value, (int, float)):
            raise ValueError("Value must be numeric")
        
        if value < min_val or value > max_val:
            raise ValueError(f"Value must be between {min_val} and {max_val}")
        
        return value

class SecurityValidator:
    """Additional security validations"""
    
    @staticmethod
    def validate_zkp_proof_structure(proof_data: Dict[str, Any]) -> bool:
        """Validate ZKP proof has required structure"""
        required_fields = ['commitment', 'nullifier', 'random_vote_id', 'timestamp']
        
        if not isinstance(proof_data, dict):
            raise ValueError("Proof data must be a dictionary")
        
        for field in required_fields:
            if field not in proof_data:
                raise ValueError(f"Missing required field: {field}")
            
            if not isinstance(proof_data[field], str):
                raise ValueError(f"Field {field} must be a string")
        
        InputSanitizer.validate_hash(proof_data['commitment'])
        InputSanitizer.validate_hash(proof_data['nullifier'])
        InputSanitizer.validate_hash(proof_data['random_vote_id'])
        
        try:
            timestamp = int(proof_data['timestamp'])
            if timestamp < 0 or timestamp > 2**32:
                raise ValueError("Invalid timestamp range")
        except (ValueError, TypeError):
            raise ValueError("Invalid timestamp format")
        
        return True
    
    @staticmethod
    def validate_bulletproof_structure(proof: Dict[str, Any]) -> bool:
        """Validate Bulletproof structure"""
        required_fields = ['A', 'S', 'T1', 'T2', 'tau_x', 'mu', 'inner_product_proof']
        
        if not isinstance(proof, dict):
            raise ValueError("Bulletproof must be a dictionary")
        
        for field in required_fields:
            if field not in proof:
                raise ValueError(f"Missing Bulletproof field: {field}")
        
        ip_proof = proof['inner_product_proof']
        if not isinstance(ip_proof, dict):
            raise ValueError("Inner product proof must be a dictionary")
        
        ip_required = ['L', 'R', 'a', 'b']
        for field in ip_required:
            if field not in ip_proof:
                raise ValueError(f"Missing inner product proof field: {field}")
        
        return True

def create_validation_middleware():
    """Create input validation middleware for FastAPI"""
    
    async def validate_request(request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid request format")
    
    return validate_request

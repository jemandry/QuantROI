import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class RiskGuardrailType(Enum):
    MARGIN_CONTROL = "margin_control"
    POSITION_SIZE = "position_size"
    VOLATILITY_THRESHOLD = "volatility_threshold"
    MODEL_SELECTION = "model_selection"
    SECTOR_CONCENTRATION = "sector_concentration"

@dataclass
class DIPSwitchConfig:
    switch_id: str
    guardrail_type: RiskGuardrailType
    enabled: bool
    threshold_value: float
    user_id: str
    expiration_timestamp: int
    smart_contract_address: str

class RiskGuardrailEngine:
    """Real-time risk guardrails with user-controlled DIP switches"""
    
    def __init__(self, solana_rpc_url: str = "https://api.devnet.solana.com"):
        self.logger = logging.getLogger(__name__)
        self.solana_rpc_url = solana_rpc_url
        self.active_switches = {}
        self.violation_history = []
        
    async def create_dip_switch(self, user_id: str, guardrail_type: RiskGuardrailType, 
                               threshold: float, duration_hours: int = 24) -> str:
        """Create user-controlled DIP switch with smart contract commitment"""
        try:
            switch_id = f"dip_{user_id}_{guardrail_type.value}_{int(datetime.now().timestamp())}"
            expiration = int(datetime.now().timestamp()) + (duration_hours * 3600)
            
            contract_result = await self._create_smart_contract_authorization(
                user_id, guardrail_type, threshold, expiration
            )
            
            if contract_result:
                dip_switch = DIPSwitchConfig(
                    switch_id=switch_id,
                    guardrail_type=guardrail_type,
                    enabled=True,
                    threshold_value=threshold,
                    user_id=user_id,
                    expiration_timestamp=expiration,
                    smart_contract_address=contract_result['address']
                )
                
                self.active_switches[switch_id] = dip_switch
                self.logger.info(f"Created DIP switch: {switch_id}")
                return switch_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating DIP switch: {e}")
            return None
    
    async def validate_trade_against_guardrails(self, trade_request: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate trade request against active DIP switch guardrails"""
        violations = []
        
        try:
            user_id = trade_request.get('user_id')
            if not user_id:
                violations.append("Missing user_id in trade request")
                return False, violations
            
            user_switches = {k: v for k, v in self.active_switches.items() if v.user_id == user_id}
            
            for switch_id, switch_config in user_switches.items():
                if not switch_config.enabled:
                    continue
                
                if datetime.now().timestamp() > switch_config.expiration_timestamp:
                    switch_config.enabled = False
                    continue
                
                violation = await self._check_guardrail_violation(trade_request, switch_config)
                if violation:
                    violations.append(violation)
            
            if violations:
                await self._log_guardrail_violations(user_id, trade_request, violations)
            
            return len(violations) == 0, violations
            
        except Exception as e:
            self.logger.error(f"Error validating guardrails: {e}")
            return False, [f"Guardrail validation error: {str(e)}"]
    
    async def _check_guardrail_violation(self, trade_request: Dict[str, Any], 
                                       switch_config: DIPSwitchConfig) -> Optional[str]:
        """Check specific guardrail violation"""
        try:
            if switch_config.guardrail_type == RiskGuardrailType.POSITION_SIZE:
                position_size = trade_request.get('quantity', 0) * trade_request.get('price', 0)
                if position_size > switch_config.threshold_value:
                    return f"Position size ${position_size:,.2f} exceeds limit ${switch_config.threshold_value:,.2f}"
            
            elif switch_config.guardrail_type == RiskGuardrailType.VOLATILITY_THRESHOLD:
                volatility = trade_request.get('estimated_volatility', 0)
                if volatility > switch_config.threshold_value:
                    return f"Volatility {volatility:.2%} exceeds threshold {switch_config.threshold_value:.2%}"
            
            elif switch_config.guardrail_type == RiskGuardrailType.MARGIN_CONTROL:
                if trade_request.get('use_margin', False) and not switch_config.threshold_value:
                    return "Margin trading disabled by DIP switch"
            
            elif switch_config.guardrail_type == RiskGuardrailType.SECTOR_CONCENTRATION:
                sector = trade_request.get('sector', '')
                current_sector_exposure = await self._calculate_sector_exposure(
                    switch_config.user_id, sector
                )
                if current_sector_exposure > switch_config.threshold_value:
                    return f"Sector concentration {current_sector_exposure:.2%} exceeds limit {switch_config.threshold_value:.2%}"
            
            elif switch_config.guardrail_type == RiskGuardrailType.MODEL_SELECTION:
                model_type = trade_request.get('model_type', 'correlation')
                if model_type == 'correlation' and switch_config.threshold_value > 0.5:
                    return "Correlation-based model disabled by DIP switch"
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking guardrail: {e}")
            return f"Guardrail check error: {str(e)}"
    
    async def _create_smart_contract_authorization(self, user_id: str, guardrail_type: RiskGuardrailType,
                                                 threshold: float, expiration: int) -> Optional[Dict[str, Any]]:
        """Create smart contract authorization for DIP switch"""
        try:
            contract_data = {
                'agent_id': f"guardrail_{user_id}",
                'allowed_actions': ['validate_trade'],
                'constraints': {
                    'guardrail_type': guardrail_type.value,
                    'threshold_value': threshold,
                    'expiration_timestamp': expiration
                },
                'investor_type': 'moderate'
            }
            
            mock_address = f"solana_contract_{hash(user_id + guardrail_type.value) % 100000}"
            
            return {
                'address': mock_address,
                'transaction_hash': f"tx_{int(datetime.now().timestamp())}",
                'contract_data': contract_data
            }
            
        except Exception as e:
            self.logger.error(f"Error creating smart contract authorization: {e}")
            return None
    
    async def _calculate_sector_exposure(self, user_id: str, sector: str) -> float:
        """Calculate current sector exposure for user"""
        try:
            mock_portfolio = {
                'Technology': 0.35,
                'Healthcare': 0.20,
                'Finance': 0.15,
                'Energy': 0.10,
                'Consumer': 0.20
            }
            
            return mock_portfolio.get(sector, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating sector exposure: {e}")
            return 0.0
    
    async def _log_guardrail_violations(self, user_id: str, trade_request: Dict[str, Any], 
                                      violations: List[str]):
        """Log guardrail violations for audit trail"""
        try:
            violation_record = {
                'user_id': user_id,
                'trade_request': trade_request,
                'violations': violations,
                'timestamp': datetime.now().isoformat(),
                'violation_id': f"violation_{int(datetime.now().timestamp())}"
            }
            
            self.violation_history.append(violation_record)
            
            if len(self.violation_history) > 1000:
                self.violation_history = self.violation_history[-500:]
            
            self.logger.warning(f"Guardrail violations for user {user_id}: {violations}")
            
        except Exception as e:
            self.logger.error(f"Error logging guardrail violations: {e}")
    
    async def update_dip_switch(self, switch_id: str, enabled: bool, new_threshold: Optional[float] = None) -> bool:
        """Update existing DIP switch configuration"""
        try:
            if switch_id not in self.active_switches:
                return False
            
            switch_config = self.active_switches[switch_id]
            switch_config.enabled = enabled
            
            if new_threshold is not None:
                switch_config.threshold_value = new_threshold
            
            await self._update_smart_contract(switch_config)
            
            self.logger.info(f"Updated DIP switch {switch_id}: enabled={enabled}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating DIP switch: {e}")
            return False
    
    async def _update_smart_contract(self, switch_config: DIPSwitchConfig):
        """Update smart contract with new DIP switch configuration"""
        try:
            update_data = {
                'switch_id': switch_config.switch_id,
                'enabled': switch_config.enabled,
                'threshold_value': switch_config.threshold_value,
                'update_timestamp': int(datetime.now().timestamp())
            }
            
            self.logger.info(f"Smart contract update: {update_data}")
            
        except Exception as e:
            self.logger.error(f"Error updating smart contract: {e}")
    
    def get_user_guardrails(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active guardrails for a user"""
        try:
            user_switches = [
                {
                    'switch_id': switch_id,
                    'guardrail_type': config.guardrail_type.value,
                    'enabled': config.enabled,
                    'threshold_value': config.threshold_value,
                    'expiration_timestamp': config.expiration_timestamp,
                    'expires_in_hours': (config.expiration_timestamp - datetime.now().timestamp()) / 3600
                }
                for switch_id, config in self.active_switches.items()
                if config.user_id == user_id
            ]
            
            return user_switches
            
        except Exception as e:
            self.logger.error(f"Error getting user guardrails: {e}")
            return []
    
    def get_violation_history(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get violation history for audit purposes"""
        try:
            if user_id:
                violations = [
                    record for record in self.violation_history
                    if record['user_id'] == user_id
                ]
            else:
                violations = self.violation_history
            
            return violations[-limit:]
            
        except Exception as e:
            self.logger.error(f"Error getting violation history: {e}")
            return []

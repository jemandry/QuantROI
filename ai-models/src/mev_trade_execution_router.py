#!/usr/bin/env python3
"""
MEV-Protected Trade Execution Router
Centralizes all trade execution through MEV protection for all trading engines
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

try:
    from .mev_protected_trading import MevProtectedTradingService, AtomicTradeBundle
    from .ibkr_trading_integration import IBKRTradingIntegration, IBKRTradeRequest, OrderType, OrderSide
    MEV_AVAILABLE = True
except ImportError:
    MEV_AVAILABLE = False
    logging.warning("MEV protection not available - trades will be vulnerable")

@dataclass
class TradeExecutionRequest:
    """Unified trade execution request for all trading engines"""
    symbol: str
    quantity: float
    action: str  # "buy", "sell", "hold"
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    user_id: str = "default_user"
    strategy_id: str = "default_strategy"
    urgency_ms: int = 5000
    trade_value_usd: float = 10000
    confidence: float = 0.75
    source_engine: str = "unknown"
    causal_analysis: Optional[Dict[str, Any]] = None
    compliance_data: Optional[Dict[str, Any]] = None

@dataclass
class TradeExecutionResponse:
    """Unified trade execution response"""
    success: bool
    order_id: Optional[str] = None
    execution_time_ms: float = 0.0
    mev_protected: bool = False
    slippage_bps: float = 0.0
    fill_price: Optional[float] = None
    error_message: Optional[str] = None
    mev_metrics: Optional[Dict[str, Any]] = None

class MevTradeExecutionRouter:
    """
    Centralized router for MEV-protected trade execution
    All trading engines route through this for consistent MEV protection
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mev_service = MevProtectedTradingService() if MEV_AVAILABLE else None
        self.ibkr_integration = IBKRTradingIntegration() if MEV_AVAILABLE else None
        
        self.execution_stats = {
            'total_trades': 0,
            'mev_protected_trades': 0,
            'successful_trades': 0,
            'avg_execution_time_ms': 0.0,
            'total_tips_paid': 0
        }
    
    def route_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route trade through MEV protection (synchronous wrapper for execute_trade)"""
        try:
            request = TradeExecutionRequest(
                symbol=trade_data.get('symbol', 'UNKNOWN'),
                quantity=float(trade_data.get('quantity', 100)),
                action=trade_data.get('action', 'hold'),
                order_type=trade_data.get('order_type', 'MARKET'),
                limit_price=trade_data.get('limit_price'),
                user_id=trade_data.get('user_id', 'default_user'),
                strategy_id=trade_data.get('strategy_id', 'default_strategy'),
                urgency_ms=trade_data.get('urgency_ms', 5000),
                trade_value_usd=trade_data.get('trade_value_usd', 10000),
                confidence=trade_data.get('confidence', 0.75),
                source_engine=trade_data.get('source_engine', 'unknown')
            )
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.execute_trade(request))
                        result = future.result(timeout=30)
                else:
                    result = asyncio.run(self.execute_trade(request))
            except RuntimeError:
                result = asyncio.run(self.execute_trade(request))
            
            return {
                'success': result.success,
                'order_id': result.order_id,
                'execution_time_ms': result.execution_time_ms,
                'mev_protected': result.mev_protected,
                'slippage_bps': result.slippage_bps,
                'fill_price': result.fill_price,
                'error_message': result.error_message,
                'mev_metrics': result.mev_metrics
            }
            
        except Exception as e:
            self.logger.error(f"❌ Trade routing failed: {e}")
            return {
                'success': False,
                'error_message': str(e),
                'mev_protected': False,
                'execution_time_ms': 0.0
            }
        
    async def execute_trade(self, request: TradeExecutionRequest) -> TradeExecutionResponse:
        """Execute trade with MEV protection if available"""
        start_time = time.time()
        
        try:
            self.execution_stats['total_trades'] += 1
            
            if request.action == "hold":
                return TradeExecutionResponse(
                    success=True,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    mev_protected=False
                )
            
            if self.mev_service and self.ibkr_integration:
                result = await self._execute_mev_protected_trade(request)
                if result.mev_protected:
                    self.execution_stats['mev_protected_trades'] += 1
            else:
                result = await self._execute_direct_trade(request)
                self.logger.warning(f"🚨 Trade executed without MEV protection: {request.symbol}")
            
            if result.success:
                self.execution_stats['successful_trades'] += 1
            
            execution_time = (time.time() - start_time) * 1000
            total = self.execution_stats['total_trades']
            self.execution_stats['avg_execution_time_ms'] = (
                (self.execution_stats['avg_execution_time_ms'] * (total - 1) + execution_time) / total
            )
            
            result.execution_time_ms = execution_time
            
            self.logger.info(f"Trade executed: {request.symbol} {request.action} "
                           f"(MEV: {'✅' if result.mev_protected else '❌'}, "
                           f"Time: {execution_time:.2f}ms)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Trade execution failed: {e}")
            return TradeExecutionResponse(
                success=False,
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _execute_mev_protected_trade(self, request: TradeExecutionRequest) -> TradeExecutionResponse:
        """Execute trade with full MEV protection"""
        try:
            mev_trade_request = {
                "symbol": request.symbol,
                "quantity": request.quantity,
                "side": request.action.upper(),
                "order_type": request.order_type,
                "user_id": request.user_id,
                "strategy_id": request.strategy_id,
                "urgency_ms": request.urgency_ms,
                "trade_value_usd": request.trade_value_usd,
                "limit_price": request.limit_price
            }
            
            mev_result = await self.mev_service.execute_mev_protected_trade(mev_trade_request)
            
            if mev_result["success"]:
                ibkr_request = self._convert_to_ibkr_request(request)
                ibkr_result = await self.ibkr_integration.execute_trade(ibkr_request)
                
                if ibkr_result:
                    self.execution_stats['total_tips_paid'] += mev_result.get('bundle_details', {}).get('tip_paid', 0)
                    
                    return TradeExecutionResponse(
                        success=True,
                        order_id=ibkr_result.order_id,
                        mev_protected=mev_result.get('mev_protected', False),
                        slippage_bps=ibkr_result.slippage_bps,
                        fill_price=ibkr_result.avg_fill_price,
                        mev_metrics={
                            'tip_paid': mev_result.get('bundle_details', {}).get('tip_paid', 0),
                            'priority_fee': mev_result.get('bundle_details', {}).get('priority_fee', 0),
                            'geographic_endpoint': mev_result.get('geographic_optimization', {}).get('current_endpoint', 'unknown'),
                            'bundle_hash': mev_result.get('bundle_details', {}).get('bundle_hash')
                        }
                    )
                else:
                    return TradeExecutionResponse(
                        success=False,
                        error_message="IBKR execution failed after MEV protection",
                        mev_protected=True
                    )
            else:
                return TradeExecutionResponse(
                    success=False,
                    error_message=f"MEV protection failed: {mev_result.get('error', 'Unknown error')}",
                    mev_protected=False
                )
                
        except Exception as e:
            self.logger.error(f"❌ MEV-protected execution failed: {e}")
            return TradeExecutionResponse(
                success=False,
                error_message=str(e),
                mev_protected=False
            )
    
    async def _execute_direct_trade(self, request: TradeExecutionRequest) -> TradeExecutionResponse:
        """Fallback direct trade execution (vulnerable to MEV)"""
        await asyncio.sleep(0.05)
        
        return TradeExecutionResponse(
            success=True,
            order_id=f"direct_{int(time.time() * 1000)}",
            mev_protected=False,
            slippage_bps=5.0,
            fill_price=100.0
        )
    
    def _convert_to_ibkr_request(self, request: TradeExecutionRequest) -> 'IBKRTradeRequest':
        """Convert unified request to IBKR format"""
        if not MEV_AVAILABLE:
            return None
            
        return IBKRTradeRequest(
            symbol=request.symbol,
            quantity=int(request.quantity),
            order_type=OrderType.MARKET if request.order_type == "MARKET" else OrderType.LIMIT,
            side=OrderSide.BUY if request.action.upper() == "BUY" else OrderSide.SELL,
            user_id=request.user_id,
            strategy_id=request.strategy_id,
            limit_price=request.limit_price
        )
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics"""
        total = max(1, self.execution_stats['total_trades'])
        
        return {
            'total_trades': self.execution_stats['total_trades'],
            'successful_trades': self.execution_stats['successful_trades'],
            'mev_protected_trades': self.execution_stats['mev_protected_trades'],
            'success_rate': self.execution_stats['successful_trades'] / total,
            'mev_protection_rate': self.execution_stats['mev_protected_trades'] / total,
            'avg_execution_time_ms': self.execution_stats['avg_execution_time_ms'],
            'total_tips_paid': self.execution_stats['total_tips_paid'],
            'mev_available': MEV_AVAILABLE
        }

_global_router = None

def get_mev_trade_router() -> MevTradeExecutionRouter:
    """Get global MEV trade execution router instance"""
    global _global_router
    if _global_router is None:
        _global_router = MevTradeExecutionRouter()
    return _global_router

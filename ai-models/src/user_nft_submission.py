import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib
import uuid

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    logging.warning("Web3.py not available - using mock blockchain integration")
    WEB3_AVAILABLE = False

try:
    import ipfshttpclient
    IPFS_AVAILABLE = True
except ImportError:
    logging.warning("IPFS client not available - using local storage")
    IPFS_AVAILABLE = False

@dataclass
class NFTStrategy:
    """Container for NFT trading strategy"""
    nft_id: str
    strategy_name: str
    creator_address: str
    strategy_code: str
    metadata: Dict[str, Any]
    performance_metrics: Dict[str, float]
    royalty_rate: float
    created_at: datetime
    last_updated: datetime
    status: str  # 'pending', 'validated', 'active', 'retired'

@dataclass
class CompetitionResult:
    """Results from NFT strategy competition"""
    nft_id: str
    competition_id: str
    performance_score: float
    sharpe_ratio: float
    total_return: float
    accuracy: float
    max_drawdown: float
    trades_count: int
    royalties_earned: float
    rank: int
    timestamp: datetime

class NFTValidator:
    """
    ERC-721 NFT validation and integration with Ethereum/blockchain
    Validates NFT ownership and strategy authenticity
    """
    
    def __init__(self, web3_provider_url: str = "https://mainnet.infura.io/v3/YOUR_PROJECT_ID"):
        self.logger = logging.getLogger(__name__)
        
        if WEB3_AVAILABLE:
            try:
                self.w3 = Web3(Web3.HTTPProvider(web3_provider_url))
                if self.w3.is_connected():
                    self.web3_available = True
                    self.logger.info("Connected to Ethereum network")
                else:
                    self.web3_available = False
                    self.logger.warning("Failed to connect to Ethereum network")
            except Exception as e:
                self.logger.error(f"Web3 initialization error: {e}")
                self.web3_available = False
        else:
            self.web3_available = False
        
        self.nft_contract_address = "0x1234567890123456789012345678901234567890"
        self.royalty_contract_address = "0x0987654321098765432109876543210987654321"
        
        self.erc721_abi = [
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "ownerOf",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "tokenURI",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }
        ]
        
        if self.web3_available:
            try:
                self.nft_contract = self.w3.eth.contract(
                    address=self.nft_contract_address,
                    abi=self.erc721_abi
                )
            except Exception as e:
                self.logger.error(f"Contract initialization error: {e}")
                self.nft_contract = None
        else:
            self.nft_contract = None
    
    def validate_nft_ownership(self, nft_id: str, user_address: str) -> bool:
        """Validate NFT ownership on blockchain"""
        try:
            if not self.web3_available or not self.nft_contract:
                self.logger.warning("Using mock NFT validation")
                return True
            
            token_id = int(nft_id.replace('NFT_', ''), 16) if 'NFT_' in nft_id else int(nft_id)
            
            owner_address = self.nft_contract.functions.ownerOf(token_id).call()
            
            owner_normalized = self.w3.to_checksum_address(owner_address.lower())
            user_normalized = self.w3.to_checksum_address(user_address.lower())
            
            is_owner = owner_normalized == user_normalized
            
            self.logger.info(f"NFT {nft_id} ownership validation: {is_owner}")
            return is_owner
            
        except Exception as e:
            self.logger.error(f"Error validating NFT ownership: {e}")
            return False
    
    def get_nft_metadata(self, nft_id: str) -> Dict[str, Any]:
        """Retrieve NFT metadata from blockchain"""
        try:
            if not self.web3_available or not self.nft_contract:
                return {
                    'name': f'Trading Strategy NFT {nft_id}',
                    'description': 'AI-powered trading strategy',
                    'attributes': [
                        {'trait_type': 'Strategy Type', 'value': 'Momentum'},
                        {'trait_type': 'Accuracy', 'value': '75%'},
                        {'trait_type': 'Sharpe Ratio', 'value': '2.1'}
                    ],
                    'creator': '0x1234567890123456789012345678901234567890'
                }
            
            token_id = int(nft_id.replace('NFT_', ''), 16) if 'NFT_' in nft_id else int(nft_id)
            
            token_uri = self.nft_contract.functions.tokenURI(token_id).call()
            
            metadata = {
                'token_uri': token_uri,
                'token_id': token_id,
                'retrieved_at': datetime.now().isoformat()
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error retrieving NFT metadata: {e}")
            return {}
    
    def validate_strategy_code(self, strategy_code: str) -> Dict[str, Any]:
        """Validate and analyze strategy code for security and compliance"""
        validation_result = {
            'is_valid': True,
            'security_score': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        try:
            forbidden_imports = ['os', 'subprocess', 'sys', 'eval', 'exec']
            security_issues = []
            
            for forbidden in forbidden_imports:
                if forbidden in strategy_code:
                    security_issues.append(f"Forbidden import/function: {forbidden}")
            
            suspicious_patterns = ['__import__', 'getattr', 'setattr', 'delattr']
            for pattern in suspicious_patterns:
                if pattern in strategy_code:
                    security_issues.append(f"Suspicious pattern: {pattern}")
            
            if security_issues:
                validation_result['security_score'] = max(0, 1.0 - len(security_issues) * 0.2)
                validation_result['issues'] = security_issues
                validation_result['is_valid'] = len(security_issues) < 3  # Allow minor issues
            else:
                validation_result['security_score'] = 1.0
            
            if len(strategy_code) < 100:
                validation_result['recommendations'].append("Strategy code seems too short")
            
            if 'def predict' not in strategy_code and 'def trade' not in strategy_code:
                validation_result['recommendations'].append("Strategy should have predict or trade function")
            
            self.logger.info(f"Strategy validation completed. Score: {validation_result['security_score']:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error validating strategy code: {e}")
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"Validation error: {e}")
        
        return validation_result

class NFTCompetitionEngine:
    """
    NFT strategy competition engine with automated testing and leaderboards
    Manages competitions against master strategy and user strategies
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validator = NFTValidator()
        self.active_competitions = {}
        self.competition_history = []
        self.leaderboard = []
        
    def submit_nft_strategy(self, nft_id: str, strategy_name: str, 
                          creator_address: str, strategy_code: str,
                          metadata: Dict[str, Any] = None) -> NFTStrategy:
        """Submit NFT strategy for competition"""
        try:
            if not self.validator.validate_nft_ownership(nft_id, creator_address):
                raise ValueError(f"NFT ownership validation failed for {nft_id}")
            
            validation_result = self.validator.validate_strategy_code(strategy_code)
            if not validation_result['is_valid']:
                raise ValueError(f"Strategy validation failed: {validation_result['issues']}")
            
            nft_strategy = NFTStrategy(
                nft_id=nft_id,
                strategy_name=strategy_name,
                creator_address=creator_address,
                strategy_code=strategy_code,
                metadata=metadata or {},
                performance_metrics={},
                royalty_rate=0.05,  # 5% default royalty
                created_at=datetime.now(),
                last_updated=datetime.now(),
                status='pending'
            )
            
            self.logger.info(f"NFT strategy submitted: {nft_id} by {creator_address}")
            return nft_strategy
            
        except Exception as e:
            self.logger.error(f"Error submitting NFT strategy: {e}")
            raise
    
    def run_strategy_backtest(self, nft_strategy: NFTStrategy, 
                            market_data: pd.DataFrame) -> Dict[str, float]:
        """Run backtest for NFT strategy"""
        try:
            self.logger.info(f"Running backtest for strategy {nft_strategy.nft_id}")
            
            returns = []
            positions = []
            
            for i in range(len(market_data)):
                if i > 0:
                    price_change = market_data.iloc[i]['close'] - market_data.iloc[i-1]['close']
                    signal = 1 if price_change > 0 else -1
                    
                    if i > 1:
                        position_return = positions[-1] * price_change / market_data.iloc[i-1]['close']
                        returns.append(position_return)
                    
                    positions.append(signal)
            
            returns_array = np.array(returns)
            
            metrics = {
                'total_return': np.sum(returns_array),
                'sharpe_ratio': np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0,
                'max_drawdown': self._calculate_max_drawdown(returns_array),
                'accuracy': (np.sum(returns_array > 0) / len(returns_array)) if len(returns_array) > 0 else 0,
                'trades_count': len(returns_array),
                'volatility': np.std(returns_array) * np.sqrt(252)
            }
            
            self.logger.info(f"Backtest completed. Sharpe: {metrics['sharpe_ratio']:.2f}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error running strategy backtest: {e}")
            return {}
    
    def create_competition(self, competition_name: str, 
                         participating_strategies: List[NFTStrategy],
                         master_strategy: Dict[str, Any] = None) -> str:
        """Create new NFT strategy competition"""
        try:
            competition_id = str(uuid.uuid4())
            
            competition_data = self._generate_competition_data()
            
            competition = {
                'competition_id': competition_id,
                'name': competition_name,
                'strategies': participating_strategies,
                'master_strategy': master_strategy,
                'market_data': competition_data,
                'results': [],
                'status': 'running',
                'created_at': datetime.now(),
                'leaderboard': []
            }
            
            self.active_competitions[competition_id] = competition
            
            asyncio.create_task(self._run_competition(competition_id))
            
            self.logger.info(f"Competition created: {competition_id} with {len(participating_strategies)} strategies")
            return competition_id
            
        except Exception as e:
            self.logger.error(f"Error creating competition: {e}")
            return ""
    
    async def _run_competition(self, competition_id: str):
        """Run NFT strategy competition"""
        try:
            competition = self.active_competitions[competition_id]
            results = []
            
            master_result = None
            if competition['master_strategy']:
                master_metrics = self._run_master_strategy(competition['market_data'])
                master_result = {
                    'strategy_name': 'Master Strategy',
                    'nft_id': 'MASTER',
                    'metrics': master_metrics
                }
            
            for strategy in competition['strategies']:
                try:
                    metrics = self.run_strategy_backtest(strategy, competition['market_data'])
                    
                    result = CompetitionResult(
                        nft_id=strategy.nft_id,
                        competition_id=competition_id,
                        performance_score=self._calculate_performance_score(metrics),
                        sharpe_ratio=metrics.get('sharpe_ratio', 0),
                        total_return=metrics.get('total_return', 0),
                        accuracy=metrics.get('accuracy', 0),
                        max_drawdown=metrics.get('max_drawdown', 0),
                        trades_count=metrics.get('trades_count', 0),
                        royalties_earned=0.0,  # Will be calculated based on usage
                        rank=0,  # Will be assigned after sorting
                        timestamp=datetime.now()
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    self.logger.error(f"Error testing strategy {strategy.nft_id}: {e}")
            
            results.sort(key=lambda x: x.performance_score, reverse=True)
            
            for i, result in enumerate(results):
                result.rank = i + 1
            
            competition['results'] = results
            competition['status'] = 'completed'
            competition['leaderboard'] = results[:10]  # Top 10
            
            await self._calculate_royalties(competition_id)
            
            self._update_global_leaderboard(results)
            
            self.logger.info(f"Competition {competition_id} completed with {len(results)} results")
            
        except Exception as e:
            self.logger.error(f"Error running competition: {e}")
    
    def _generate_competition_data(self, days: int = 30) -> pd.DataFrame:
        """Generate market data for competition testing"""
        try:
            dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                                end=datetime.now(), freq='D')
            
            initial_price = 100.0
            returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% daily return, 2% volatility
            
            prices = [initial_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            market_data = pd.DataFrame({
                'date': dates,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, len(dates))
            })
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error generating competition data: {e}")
            return pd.DataFrame()
    
    def _run_master_strategy(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Run master strategy for comparison"""
        try:
            returns = []
            positions = []
            
            for i in range(20, len(market_data)):  # Start after 20-day lookback
                ma_short = market_data['close'].iloc[i-5:i].mean()
                ma_long = market_data['close'].iloc[i-20:i].mean()
                
                if ma_short > ma_long:
                    signal = 1  # Buy
                elif ma_short < ma_long:
                    signal = -1  # Sell
                else:
                    signal = 0  # Hold
                
                if i > 20 and len(positions) > 0:
                    price_change = market_data.iloc[i]['close'] - market_data.iloc[i-1]['close']
                    position_return = positions[-1] * price_change / market_data.iloc[i-1]['close']
                    returns.append(position_return)
                
                positions.append(signal)
            
            returns_array = np.array(returns)
            
            metrics = {
                'total_return': np.sum(returns_array),
                'sharpe_ratio': np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0,
                'max_drawdown': self._calculate_max_drawdown(returns_array),
                'accuracy': (np.sum(returns_array > 0) / len(returns_array)) if len(returns_array) > 0 else 0,
                'trades_count': len(returns_array),
                'volatility': np.std(returns_array) * np.sqrt(252)
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error running master strategy: {e}")
            return {}
    
    def _calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """Calculate composite performance score"""
        try:
            sharpe_weight = 0.4
            return_weight = 0.3
            accuracy_weight = 0.2
            drawdown_weight = 0.1
            
            sharpe_score = min(metrics.get('sharpe_ratio', 0) / 3.0, 1.0)  # Normalize to max 3.0
            return_score = min(max(metrics.get('total_return', 0), -0.5) + 0.5, 1.0)  # Normalize -50% to +50%
            accuracy_score = metrics.get('accuracy', 0)
            drawdown_score = max(1.0 - metrics.get('max_drawdown', 0) / 0.3, 0)  # Penalize >30% drawdown
            
            performance_score = (
                sharpe_weight * sharpe_score +
                return_weight * return_score +
                accuracy_weight * accuracy_score +
                drawdown_weight * drawdown_score
            )
            
            return performance_score
            
        except Exception as e:
            self.logger.error(f"Error calculating performance score: {e}")
            return 0.0
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        try:
            if len(returns) == 0:
                return 0.0
            
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            
            return abs(np.min(drawdown))
            
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    async def _calculate_royalties(self, competition_id: str):
        """Calculate and distribute royalties to NFT strategy creators"""
        try:
            competition = self.active_competitions[competition_id]
            results = competition['results']
            
            total_prize_pool = 1000.0  # ETH or tokens
            
            for i, result in enumerate(results[:10]):  # Top 10 get rewards
                if i == 0:
                    royalty = total_prize_pool * 0.3  # 30% for winner
                elif i < 3:
                    royalty = total_prize_pool * 0.15  # 15% for 2nd-3rd
                elif i < 5:
                    royalty = total_prize_pool * 0.08  # 8% for 4th-5th
                else:
                    royalty = total_prize_pool * 0.02  # 2% for 6th-10th
                
                result.royalties_earned = royalty
                
                self.logger.info(f"Royalty calculated for {result.nft_id}: {royalty:.4f}")
            
        except Exception as e:
            self.logger.error(f"Error calculating royalties: {e}")
    
    def _update_global_leaderboard(self, results: List[CompetitionResult]):
        """Update global NFT strategy leaderboard"""
        try:
            for result in results:
                existing_idx = None
                for i, entry in enumerate(self.leaderboard):
                    if entry.nft_id == result.nft_id:
                        existing_idx = i
                        break
                
                if existing_idx is not None:
                    if result.performance_score > self.leaderboard[existing_idx].performance_score:
                        self.leaderboard[existing_idx] = result
                else:
                    self.leaderboard.append(result)
            
            self.leaderboard.sort(key=lambda x: x.performance_score, reverse=True)
            self.leaderboard = self.leaderboard[:100]
            
            for i, entry in enumerate(self.leaderboard):
                entry.rank = i + 1
            
            self.logger.info(f"Global leaderboard updated with {len(self.leaderboard)} entries")
            
        except Exception as e:
            self.logger.error(f"Error updating global leaderboard: {e}")
    
    def get_leaderboard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get current NFT strategy leaderboard"""
        try:
            leaderboard_data = []
            
            for entry in self.leaderboard[:limit]:
                leaderboard_data.append({
                    'rank': entry.rank,
                    'nft_id': entry.nft_id,
                    'performance_score': round(entry.performance_score, 4),
                    'sharpe_ratio': round(entry.sharpe_ratio, 3),
                    'total_return': round(entry.total_return, 4),
                    'accuracy': round(entry.accuracy, 3),
                    'max_drawdown': round(entry.max_drawdown, 4),
                    'trades_count': entry.trades_count,
                    'royalties_earned': round(entry.royalties_earned, 6),
                    'last_updated': entry.timestamp.isoformat()
                })
            
            return leaderboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting leaderboard: {e}")
            return []

class NFTStrategyEngine:
    """
    Main engine for NFT strategy management and competition
    Combines validation, competition management, and blockchain integration
    """
    
    def __init__(self):
        self.competition_engine = NFTCompetitionEngine()
        self.validator = NFTValidator()
        self.royalty_manager = None  # Will be initialized below
        self.logger = logging.getLogger(__name__)
    
    async def submit_nft_strategy(self, nft_id: str, creator_address: str, strategy_code: str, strategy_name: str) -> Dict[str, Any]:
        """Submit NFT strategy for competition"""
        try:
            nft_strategy = self.competition_engine.submit_nft_strategy(
                nft_id, strategy_name, creator_address, strategy_code
            )
            
            return {
                'success': True,
                'nft_id': nft_id,
                'strategy_name': strategy_name,
                'creator_address': creator_address
            }
        except Exception as e:
            self.logger.error(f"Error submitting NFT strategy: {e}")
            return {
                'success': False,
                'error': str(e),
                'nft_id': nft_id
            }
    
    async def run_strategy_backtest(self, nft_id: str, market_data: np.ndarray) -> Dict[str, Any]:
        """Run backtest for NFT strategy"""
        try:
            market_df = pd.DataFrame(market_data, columns=['close', 'volume', 'high', 'low', 'open'])
            
            strategy = None
            for comp_id, competition in self.competition_engine.active_competitions.items():
                for strat in competition['strategies']:
                    if strat.nft_id == nft_id:
                        strategy = strat
                        break
                if strategy:
                    break
            
            if not strategy:
                strategy = NFTStrategy(
                    nft_id=nft_id,
                    strategy_name="Test Strategy",
                    creator_address="0x1234567890123456789012345678901234567890",
                    strategy_code="def predict(): return 1",
                    metadata={},
                    performance_metrics={},
                    royalty_rate=0.05,
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                    status='active'
                )
            
            metrics = self.competition_engine.run_strategy_backtest(strategy, market_df)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error running strategy backtest: {e}")
            return {'error': str(e)}
    
    def calculate_royalty(self, nft_id: str, usage_count: int) -> float:
        """Calculate royalty for strategy usage"""
        if not self.royalty_manager:
            self.royalty_manager = RoyaltyManager()
        
        usage_metrics = {
            'performance_score': 0.8,
            'trades_count': usage_count,
            'profit': usage_count * 10.0  # Mock profit calculation
        }
        
        return self.royalty_manager.calculate_usage_royalty(nft_id, usage_metrics)
    
    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get competition leaderboard"""
        return self.competition_engine.get_leaderboard()
    
    def validate_nft_ownership(self, nft_contract_address: str, token_id: int, owner_address: str) -> bool:
        """Validate NFT ownership"""
        return self.validator.validate_nft_ownership(nft_id=str(token_id), user_address=owner_address)

class RoyaltyManager:
    """
    Smart contract royalty management for NFT strategy usage
    Handles royalty distribution and payment tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validator = NFTValidator()
        self.royalty_records = []
        
    def calculate_usage_royalty(self, nft_id: str, usage_metrics: Dict[str, Any]) -> float:
        """Calculate royalty based on strategy usage"""
        try:
            base_rate = 0.05
            
            performance_score = usage_metrics.get('performance_score', 0.5)
            performance_multiplier = 1.0 + (performance_score - 0.5)  # 0.5x to 1.5x
            
            trades_count = usage_metrics.get('trades_count', 0)
            volume_multiplier = min(1.0 + (trades_count / 1000) * 0.1, 2.0)  # Up to 2x for high volume
            
            profit = usage_metrics.get('profit', 0)
            royalty = profit * base_rate * performance_multiplier * volume_multiplier
            
            self.logger.info(f"Royalty calculated for {nft_id}: {royalty:.6f}")
            return max(royalty, 0)
            
        except Exception as e:
            self.logger.error(f"Error calculating usage royalty: {e}")
            return 0.0
    
    def record_royalty_payment(self, nft_id: str, creator_address: str, 
                             amount: float, transaction_hash: str = None):
        """Record royalty payment for audit trail"""
        try:
            record = {
                'nft_id': nft_id,
                'creator_address': creator_address,
                'amount': amount,
                'transaction_hash': transaction_hash or f"mock_tx_{uuid.uuid4()}",
                'timestamp': datetime.now(),
                'status': 'completed'
            }
            
            self.royalty_records.append(record)
            self.logger.info(f"Royalty payment recorded: {amount:.6f} to {creator_address}")
            
        except Exception as e:
            self.logger.error(f"Error recording royalty payment: {e}")

async def main():
    """Example NFT submission and competition execution"""
    
    competition_engine = NFTCompetitionEngine()
    royalty_manager = RoyaltyManager()
    
    mock_strategy_code = """
def predict(market_data):
    if len(market_data) < 2:
        return 0
    
    price_change = market_data[-1]['close'] - market_data[-2]['close']
    return 1 if price_change > 0 else -1

def trade(signal, position_size=100):
    return signal * position_size
"""
    
    try:
        nft_strategy = competition_engine.submit_nft_strategy(
            nft_id="NFT_000001",
            strategy_name="Momentum Master",
            creator_address="0x1234567890123456789012345678901234567890",
            strategy_code=mock_strategy_code,
            metadata={
                'description': 'Advanced momentum trading strategy',
                'version': '1.0',
                'risk_level': 'medium'
            }
        )
        
        print(f"NFT strategy submitted: {nft_strategy.nft_id}")
        
        competition_id = competition_engine.create_competition(
            "Weekly NFT Strategy Challenge",
            [nft_strategy]
        )
        
        print(f"Competition created: {competition_id}")
        
        await asyncio.sleep(2)
        
        leaderboard = competition_engine.get_leaderboard(10)
        print(f"Leaderboard entries: {len(leaderboard)}")
        
        if leaderboard:
            top_strategy = leaderboard[0]
            print(f"Top strategy: {top_strategy['nft_id']} with score {top_strategy['performance_score']:.3f}")
            
            usage_metrics = {
                'performance_score': top_strategy['performance_score'],
                'trades_count': top_strategy['trades_count'],
                'profit': 1000.0  # Mock profit
            }
            
            royalty = royalty_manager.calculate_usage_royalty(
                top_strategy['nft_id'], 
                usage_metrics
            )
            
            print(f"Royalty calculated: {royalty:.6f}")
        
    except Exception as e:
        print(f"Error in NFT submission example: {e}")

if __name__ == "__main__":
    asyncio.run(main())

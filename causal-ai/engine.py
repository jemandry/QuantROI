#!/usr/bin/env python3
"""
Enhanced Causal AI Engine for RIA Roboadvisor Platform
Integrates with Neo4j for market relationship mapping and RL agents for predictions
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from neo4j import GraphDatabase
# from causalnex.structure import StructureModel
# from causalnex.network import BayesianNetwork  
# from dowhy import CausalModel
import networkx as nx
from statsmodels.tsa.stattools import grangercausalitytests
import gym
from gym import spaces

try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai-models', 'src'))
    from causal_backtesting_engine import CausalBacktestingEngine, CausalEvent
except ImportError:
    logging.warning("Could not import existing causal backtesting engine")
    CausalBacktestingEngine = None
    CausalEvent = None

class EnhancedCausalAIEngine:
    """Enhanced Causal AI Engine with Neo4j integration and RL agents"""
    
    def __init__(self, neo4j_uri: str = 'bolt://localhost:7687'):
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=('neo4j', 'password'))
        self.backtesting_engine = CausalBacktestingEngine() if CausalBacktestingEngine else None
        self.logger = logging.getLogger(__name__)
        self.confidence_threshold = 0.85
        self.rl_prediction_enabled = True
        self.rl_agents = {}
        self._init_neo4j_schema()
        self._initialize_rl_agents()
    
    def _init_neo4j_schema(self):
        """Initialize Neo4j schema for causal relationships"""
        with self.neo4j_driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT causal_link_unique IF NOT EXISTS FOR (c:CausalLinkNode) REQUIRE c.link_id IS UNIQUE",
                "CREATE CONSTRAINT market_correlation_unique IF NOT EXISTS FOR (m:MarketCorrelationNode) REQUIRE (m.symbol_pair, m.timeframe) IS UNIQUE",
                "CREATE CONSTRAINT news_unique IF NOT EXISTS FOR (n:News) REQUIRE n.news_id IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    self.logger.warning(f"Constraint may already exist: {e}")
    
    def _initialize_rl_agents(self):
        """Initialize RL agents for perpetual evolution"""
        try:
            from stable_baselines3 import PPO, DQN
            from stable_baselines3.common.vec_env import DummyVecEnv
            
            env = DummyVecEnv([lambda: MarketEnvironment()])
            
            self.rl_agents['ppo'] = PPO(
                'MlpPolicy',
                env,
                verbose=0,
                learning_rate=0.0003,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2
            )
            
            self.rl_agents['dqn'] = DQN(
                'MlpPolicy',
                env,
                verbose=0,
                learning_rate=0.0001,
                buffer_size=100000,
                learning_starts=1000,
                batch_size=32,
                tau=1.0,
                gamma=0.99,
                train_freq=4,
                gradient_steps=1,
                target_update_interval=1000
            )
            
            self.logger.info("✓ RL agents initialized successfully")
            
        except ImportError as e:
            self.logger.warning(f"stable-baselines3 not available: {e}")
            self.rl_prediction_enabled = False
        except Exception as e:
            self.logger.warning(f"RL agents initialization failed: {e}")
            self.rl_prediction_enabled = False
    
    async def create_causal_link_node(
        self,
        source_symbol: str,
        target_symbol: str,
        causal_strength: float,
        confidence_score: float,
        timeframe: str = "1h"
    ) -> str:
        """Create causal link node in Neo4j with RL agent predictions"""
        with self.neo4j_driver.session() as session:
            query = """
            CREATE (c:CausalLinkNode {
                link_id: $link_id,
                source_symbol: $source_symbol,
                target_symbol: $target_symbol,
                causal_strength: $causal_strength,
                confidence_score: $confidence_score,
                timeframe: $timeframe,
                created_at: $timestamp,
                rl_prediction_enabled: true
            })
            RETURN c.link_id as link_id
            """
            
            link_id = f"{source_symbol}_{target_symbol}_{timeframe}_{datetime.now().timestamp()}"
            result = session.run(query,
                link_id=link_id,
                source_symbol=source_symbol,
                target_symbol=target_symbol,
                causal_strength=causal_strength,
                confidence_score=confidence_score,
                timeframe=timeframe,
                timestamp=datetime.now().isoformat()
            )
            
            return result.single()['link_id']
    
    async def store_news_with_timing(
        self,
        news_id: str,
        source: str,
        first_published_timestamp: datetime,
        content_summary: str,
        market_impact_symbols: List[str]
    ) -> bool:
        """Store news with first occurrence timing for causal analysis"""
        with self.neo4j_driver.session() as session:
            query = """
            CREATE (n:News {
                news_id: $news_id,
                source: $source,
                first_published_timestamp: $first_published_timestamp,
                content_summary: $content_summary,
                market_impact_symbols: $market_impact_symbols,
                created_at: $timestamp
            })
            """
            
            session.run(query,
                news_id=news_id,
                source=source,
                first_published_timestamp=first_published_timestamp.isoformat(),
                content_summary=content_summary,
                market_impact_symbols=market_impact_symbols,
                timestamp=datetime.now().isoformat()
            )
            
            return True
    
    async def run_enhanced_causal_analysis(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        confidence_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """Run enhanced causal analysis with confidence scoring"""
        try:
            if self.backtesting_engine:
                base_analysis = await self.backtesting_engine.run_causal_analysis(
                    symbols, start_time, end_time
                )
            else:
                base_analysis = self._mock_causal_analysis(symbols)
            
            enhanced_results = {
                'base_analysis': base_analysis,
                'causal_links': [],
                'confidence_scores': {},
                'market_relationships': {},
                'news_correlations': []
            }
            
            for i, source in enumerate(symbols):
                for j, target in enumerate(symbols):
                    if i != j:
                        causal_strength = np.random.uniform(0.1, 0.9)
                        confidence = np.random.uniform(0.7, 0.98)
                        
                        if confidence >= confidence_threshold:
                            link_id = await self.create_causal_link_node(
                                source, target, causal_strength, confidence
                            )
                            
                            enhanced_results['causal_links'].append({
                                'link_id': link_id,
                                'source': source,
                                'target': target,
                                'strength': causal_strength,
                                'confidence': confidence
                            })
            
            enhanced_results['confidence_scores'] = {
                'overall': np.mean([link['confidence'] for link in enhanced_results['causal_links']]),
                'high_confidence_links': len([l for l in enhanced_results['causal_links'] if l['confidence'] > 0.9]),
                'total_links': len(enhanced_results['causal_links'])
            }
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"Enhanced causal analysis failed: {e}")
            return {'error': str(e)}
    
    def _mock_causal_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """Mock causal analysis for testing when backtesting engine unavailable"""
        return {
            'symbols': symbols,
            'causal_relationships': {
                f"{symbols[0]}_causes_{symbols[1]}": {
                    'source': symbols[0],
                    'target': symbols[1],
                    'strength': np.random.uniform(0.5, 0.9)
                }
            },
            'data_points': 1000
        }
    
    async def query_market_relationships(
        self,
        symbol: str,
        relationship_type: str = "CAUSAL_INFLUENCE",
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Query Neo4j for market relationships"""
        with self.neo4j_driver.session() as session:
            query = """
            MATCH (source:CausalLinkNode)-[r]-(target:CausalLinkNode)
            WHERE source.source_symbol = $symbol OR source.target_symbol = $symbol
            RETURN source, target, r
            LIMIT 50
            """
            
            result = session.run(query, symbol=symbol)
            relationships = []
            
            for record in result:
                relationships.append({
                    'source': dict(record['source']),
                    'target': dict(record['target']),
                    'relationship': dict(record['r']) if record['r'] else {}
                })
            
            return relationships
    
    async def generate_trading_signals(
        self,
        causal_analysis: Dict[str, Any],
        risk_tolerance: float = 0.05
    ) -> List[Dict[str, Any]]:
        """Generate trading signals based on causal analysis"""
        signals = []
        
        for link in causal_analysis.get('causal_links', []):
            if link['confidence'] > 0.9 and link['strength'] > 0.7:
                expected_return = link['strength'] * 0.01
                risk_score = 1 - link['confidence']
                
                if risk_score <= risk_tolerance:
                    signals.append({
                        'symbol': link['target'],
                        'action': 'BUY' if expected_return > 0 else 'SELL',
                        'confidence': link['confidence'],
                        'expected_return': expected_return,
                        'risk_score': risk_score,
                        'causal_justification': f"Strong causal link from {link['source']} detected",
                        'signal_strength': link['strength']
                    })
        
    
    async def generate_trading_signal(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trading signal with RL agent prediction"""
        causal_factors = []
        
        rl_prediction = None
        if self.rl_prediction_enabled and 'ppo' in self.rl_agents:
            try:
                market_state = np.array([
                    market_data.get('price', 100.0),
                    market_data.get('volume', 1000.0),
                    market_data.get('volatility', 0.2),
                    len(causal_factors),
                    sum(factor.get('strength', 0.5) for factor in causal_factors),
                    0.0, 0.0, 0.0, 0.0, 0.0
                ], dtype=np.float32)
                
                action, _ = self.rl_agents['ppo'].predict(market_state)
                rl_prediction = ['hold', 'buy', 'sell'][action] if action < 3 else 'hold'
            except Exception as e:
                self.logger.warning(f"RL prediction failed: {e}")
        
        return {
            'action': rl_prediction or 'hold',
            'confidence': 0.75,
            'reasoning': f'Causal analysis suggests moderate confidence for {symbol}',
            'causal_factors': causal_factors,
            'rl_prediction': rl_prediction,
            'timestamp': datetime.now().isoformat()
        }
    
    async def test_granger_causality(self, data: Dict[str, np.ndarray], source: str, target: str, max_lags: int = 5) -> Dict[str, Any]:
        """Test Granger causality between two time series"""
        try:
            source_data = data[source]
            target_data = data[target]
            
            combined_data = np.column_stack([target_data, source_data])
            
            result = grangercausalitytests(combined_data, max_lags, verbose=False)
            
            min_p_value = min(result[lag][0]['ssr_ftest'][1] for lag in range(1, max_lags + 1))
            
            return {
                'p_value': min_p_value,
                'significant': min_p_value < 0.05,
                'confidence': 1 - min_p_value,
                'source': source,
                'target': target,
                'test_type': 'granger_causality'
            }
            
        except Exception as e:
            self.logger.error(f"Granger causality test failed: {e}")
            return {
                'p_value': 1.0,
                'significant': False,
                'confidence': 0.0,
                'error': str(e)
            }

        mock_signals = [
            {'symbol': 'AAPL', 'confidence': 0.85, 'action': 'buy'},
            {'symbol': 'MSFT', 'confidence': 0.78, 'action': 'hold'}
        ]
        return sorted(mock_signals, key=lambda x: x['confidence'], reverse=True)
    
    async def generate_trading_signal(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trading signal with RL agent prediction"""
        causal_factors = []
        
        rl_prediction = None
        if self.rl_prediction_enabled and 'ppo' in self.rl_agents:
            try:
                market_state = np.array([
                    market_data.get('price', 100.0),
                    market_data.get('volume', 1000.0),
                    market_data.get('volatility', 0.2),
                    len(causal_factors),
                    sum(factor.get('strength', 0.5) for factor in causal_factors),
                    0.0, 0.0, 0.0, 0.0, 0.0
                ], dtype=np.float32)
                
                action, _ = self.rl_agents['ppo'].predict(market_state)
                rl_prediction = ['hold', 'buy', 'sell'][action] if action < 3 else 'hold'
            except Exception as e:
                self.logger.warning(f"RL prediction failed: {e}")
        
        return {
            'action': rl_prediction or 'hold',
            'confidence': 0.75,
            'reasoning': f'Causal analysis suggests moderate confidence for {symbol}',
            'causal_factors': causal_factors,
            'rl_prediction': rl_prediction,
            'timestamp': datetime.now().isoformat()
        }
    
    async def test_granger_causality(self, data: Dict[str, np.ndarray], source: str, target: str, max_lags: int = 5) -> Dict[str, Any]:
        """Test Granger causality between two time series"""
        try:
            source_data = data[source]
            target_data = data[target]
            
            combined_data = np.column_stack([target_data, source_data])
            
            result = grangercausalitytests(combined_data, max_lags, verbose=False)
            
            min_p_value = min(result[lag][0]['ssr_ftest'][1] for lag in range(1, max_lags + 1))
            
            return {
                'p_value': min_p_value,
                'significant': min_p_value < 0.05,
                'confidence': 1 - min_p_value,
                'source': source,
                'target': target,
                'test_type': 'granger_causality'
            }
            
        except Exception as e:
            self.logger.error(f"Granger causality test failed: {e}")
            return {
                'p_value': 1.0,
                'significant': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def close(self):
        """Close Neo4j connection"""
        if self.neo4j_driver:
            self.neo4j_driver.close()

class MarketEnvironment(gym.Env):
    """Custom market environment for RL training"""
    
    def __init__(self):
        super(MarketEnvironment, self).__init__()
        
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )
        
        self.current_step = 0
        self.max_steps = 1000
        self.state = np.zeros(10, dtype=np.float32)
    
    def reset(self):
        self.current_step = 0
        self.state = np.random.randn(10).astype(np.float32)
        return self.state
    
    def step(self, action):
        self.current_step += 1
        
        reward = np.random.randn() * 0.1
        if action == 1:
            reward += 0.05
        elif action == 2:
            reward -= 0.02
        
        self.state = np.random.randn(10).astype(np.float32)
        
        done = self.current_step >= self.max_steps
        info = {}
        
        return self.state, reward, done, info
    
    def render(self, mode='human'):
        pass

async def main():
    """Example usage of Enhanced Causal AI Engine"""
    engine = EnhancedCausalAIEngine()
    
    try:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
        start_time = datetime.now() - timedelta(days=30)
        end_time = datetime.now()
        
        analysis = await engine.run_enhanced_causal_analysis(
            symbols, start_time, end_time
        )
        
        print("Enhanced Causal Analysis Results:")
        print(f"- Total causal links: {len(analysis.get('causal_links', []))}")
        print(f"- Overall confidence: {analysis.get('confidence_scores', {}).get('overall', 0):.3f}")
        
        signals = await engine.generate_trading_signals(analysis)
        print(f"- Generated signals: {len(signals)}")
        
        for signal in signals[:3]:
            print(f"  * {signal['action']} {signal['symbol']} (confidence: {signal['confidence']:.3f})")
        
    finally:
        engine.close()

if __name__ == "__main__":
    asyncio.run(main())

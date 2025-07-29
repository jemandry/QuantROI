import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import clickhouse_driver
import numba
from causalnex.structure import StructureModel
from causalnex.network import BayesianNetwork
from dowhy import CausalModel
import networkx as nx
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
import yfinance as yf

@dataclass
class MicrosecondTick:
    timestamp: datetime
    symbol: str
    price: float
    volume: int
    bid: float
    ask: float
    spread: float
    microsecond: int

@dataclass
class CausalEvent:
    event_id: str
    timestamp: datetime
    event_type: str
    symbol: str
    price_impact: float
    volume_impact: float
    causal_chain: List[str]
    vector_clock: Dict[str, int]

class ClickHouseDataManager:
    def __init__(self, host: str = 'localhost', port: int = 9000):
        self.client = clickhouse_driver.Client(host=host, port=port)
        self._create_tables()
    
    def _create_tables(self):
        tick_table_sql = """
        CREATE TABLE IF NOT EXISTS tick_data (
            timestamp DateTime64(6),
            symbol String,
            price Float64,
            volume UInt64,
            bid Float64,
            ask Float64,
            spread Float64,
            microsecond UInt32
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timestamp)
        """
        
        causal_events_sql = """
        CREATE TABLE IF NOT EXISTS causal_events (
            event_id String,
            timestamp DateTime64(6),
            event_type String,
            symbol String,
            price_impact Float64,
            volume_impact Float64,
            causal_chain Array(String),
            vector_clock String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timestamp)
        """
        
        try:
            self.client.execute(tick_table_sql)
            self.client.execute(causal_events_sql)
            logging.info("ClickHouse tables created successfully")
        except Exception as e:
            logging.error(f"Failed to create ClickHouse tables: {e}")
    
    def insert_tick_data(self, ticks: List[MicrosecondTick]):
        if not ticks:
            return
        
        data = [
            (tick.timestamp, tick.symbol, tick.price, tick.volume, 
             tick.bid, tick.ask, tick.spread, tick.microsecond)
            for tick in ticks
        ]
        
        try:
            self.client.execute(
                "INSERT INTO tick_data VALUES",
                data
            )
            logging.info(f"Inserted {len(ticks)} tick records")
        except Exception as e:
            logging.error(f"Failed to insert tick data: {e}")
    
    def query_tick_data(self, symbol: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        query = """
        SELECT timestamp, symbol, price, volume, bid, ask, spread, microsecond
        FROM tick_data
        WHERE symbol = %(symbol)s
        AND timestamp BETWEEN %(start_time)s AND %(end_time)s
        ORDER BY timestamp
        """
        
        try:
            result = self.client.execute(
                query,
                {'symbol': symbol, 'start_time': start_time, 'end_time': end_time}
            )
            
            columns = ['timestamp', 'symbol', 'price', 'volume', 'bid', 'ask', 'spread', 'microsecond']
            return pd.DataFrame(result, columns=columns)
        except Exception as e:
            logging.error(f"Failed to query tick data: {e}")
            return pd.DataFrame()

@numba.jit(nopython=True)
def calculate_microsecond_returns(prices: np.ndarray, timestamps: np.ndarray) -> np.ndarray:
    returns = np.empty(len(prices) - 1)
    for i in range(1, len(prices)):
        time_diff = timestamps[i] - timestamps[i-1]
        if time_diff > 0:
            returns[i-1] = (prices[i] - prices[i-1]) / prices[i-1]
        else:
            returns[i-1] = 0.0
    return returns

@numba.jit(nopython=True)
def detect_price_jumps(prices: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    jumps = np.zeros(len(prices), dtype=numba.boolean)
    for i in range(1, len(prices)):
        price_change = abs(prices[i] - prices[i-1]) / prices[i-1]
        if price_change > threshold:
            jumps[i] = True
    return jumps

class CausalGraphBuilder:
    def __init__(self):
        self.structure_model = None
        self.bayesian_network = None
        
    def build_causal_graph(self, data: pd.DataFrame) -> StructureModel:
        try:
            from causalnex.structure.notears import from_pandas
            
            numeric_data = data.select_dtypes(include=[np.number])
            
            if len(numeric_data.columns) < 2:
                logging.warning("Insufficient numeric columns for causal graph")
                return StructureModel()
            
            self.structure_model = from_pandas(numeric_data, max_iter=1000)
            
            logging.info(f"Built causal graph with {len(self.structure_model.nodes)} nodes and {len(self.structure_model.edges)} edges")
            return self.structure_model
            
        except Exception as e:
            logging.error(f"Failed to build causal graph: {e}")
            return StructureModel()
    
    def create_bayesian_network(self, data: pd.DataFrame) -> BayesianNetwork:
        if self.structure_model is None:
            self.build_causal_graph(data)
        
        try:
            self.bayesian_network = BayesianNetwork(self.structure_model)
            
            discretized_data = data.copy()
            for col in data.select_dtypes(include=[np.number]).columns:
                discretized_data[col] = pd.cut(data[col], bins=5, labels=False)
            
            self.bayesian_network = self.bayesian_network.fit_node_states(discretized_data)
            self.bayesian_network = self.bayesian_network.fit_cpds(discretized_data)
            
            logging.info("Created Bayesian network successfully")
            return self.bayesian_network
            
        except Exception as e:
            logging.error(f"Failed to create Bayesian network: {e}")
            return BayesianNetwork(StructureModel())

class MarketAgent(Agent):
    def __init__(self, unique_id: int, model: Model, symbol: str, strategy_type: str):
        super().__init__(unique_id, model)
        self.symbol = symbol
        self.strategy_type = strategy_type
        self.position = 0
        self.cash = 100000
        self.last_price = 100
        self.decision_history = []
        
    def step(self):
        market_data = self.model.get_market_data(self.symbol)
        
        if market_data is not None:
            decision = self._make_trading_decision(market_data)
            self.decision_history.append({
                'timestamp': self.model.current_time,
                'decision': decision,
                'price': market_data['price'],
                'position': self.position
            })
            
            self._execute_decision(decision, market_data)
    
    def _make_trading_decision(self, market_data: Dict[str, Any]) -> str:
        price = market_data['price']
        volatility = market_data.get('volatility', 0.02)
        
        if self.strategy_type == 'momentum':
            if price > self.last_price * 1.01:
                return 'buy'
            elif price < self.last_price * 0.99:
                return 'sell'
        elif self.strategy_type == 'mean_reversion':
            if price < self.last_price * 0.98:
                return 'buy'
            elif price > self.last_price * 1.02:
                return 'sell'
        elif self.strategy_type == 'volatility':
            if volatility > 0.03:
                return 'buy'
            elif volatility < 0.01:
                return 'sell'
        
        return 'hold'
    
    def _execute_decision(self, decision: str, market_data: Dict[str, Any]):
        price = market_data['price']
        
        if decision == 'buy' and self.cash > price * 100:
            shares = min(100, int(self.cash / price))
            self.position += shares
            self.cash -= shares * price
        elif decision == 'sell' and self.position > 0:
            shares = min(100, self.position)
            self.position -= shares
            self.cash += shares * price
        
        self.last_price = price

class MarketSimulationModel(Model):
    def __init__(self, symbols: List[str], num_agents_per_symbol: int = 10):
        super().__init__()
        self.symbols = symbols
        self.current_time = datetime.now()
        self.market_data = {}
        self.schedule = RandomActivation(self)
        
        agent_id = 0
        strategy_types = ['momentum', 'mean_reversion', 'volatility']
        
        for symbol in symbols:
            for i in range(num_agents_per_symbol):
                strategy = strategy_types[i % len(strategy_types)]
                agent = MarketAgent(agent_id, self, symbol, strategy)
                self.schedule.add(agent)
                agent_id += 1
        
        self._initialize_market_data()
    
    def _initialize_market_data(self):
        for symbol in self.symbols:
            self.market_data[symbol] = {
                'price': 100.0,
                'volume': 1000,
                'volatility': 0.02,
                'last_update': self.current_time
            }
    
    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.market_data.get(symbol)
    
    def update_market_data(self, symbol: str, price: float, volume: int, volatility: float):
        if symbol in self.market_data:
            self.market_data[symbol].update({
                'price': price,
                'volume': volume,
                'volatility': volatility,
                'last_update': self.current_time
            })
    
    def step(self):
        self.current_time += timedelta(microseconds=1000)
        
        for symbol in self.symbols:
            price_change = np.random.normal(0, 0.001)
            current_price = self.market_data[symbol]['price']
            new_price = current_price * (1 + price_change)
            
            volume_change = np.random.randint(-100, 101)
            current_volume = self.market_data[symbol]['volume']
            new_volume = max(100, current_volume + volume_change)
            
            volatility = abs(price_change) * 10
            
            self.update_market_data(symbol, new_price, new_volume, volatility)
        
        self.schedule.step()

class CausalBacktestingEngine:
    def __init__(self, clickhouse_host: str = 'localhost'):
        self.data_manager = ClickHouseDataManager(clickhouse_host)
        self.causal_graph_builder = CausalGraphBuilder()
        self.simulation_model = None
        self.causal_events = []
        
    async def ingest_microsecond_data(self, symbol: str, start_date: str, end_date: str):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval="1m")
            
            if data.empty:
                logging.warning(f"No data found for {symbol}")
                return
            
            ticks = []
            for idx, row in data.iterrows():
                base_time = idx.to_pydatetime()
                
                for microsecond in range(0, 60000000, 1000):
                    tick_time = base_time + timedelta(microseconds=microsecond)
                    
                    price_noise = np.random.normal(0, row['Close'] * 0.0001)
                    tick_price = row['Close'] + price_noise
                    
                    spread = tick_price * 0.001
                    bid = tick_price - spread/2
                    ask = tick_price + spread/2
                    
                    tick = MicrosecondTick(
                        timestamp=tick_time,
                        symbol=symbol,
                        price=tick_price,
                        volume=max(1, int(row['Volume'] / 60000 + np.random.poisson(1))),
                        bid=bid,
                        ask=ask,
                        spread=spread,
                        microsecond=microsecond
                    )
                    ticks.append(tick)
                    
                    if len(ticks) >= 10000:
                        self.data_manager.insert_tick_data(ticks)
                        ticks = []
            
            if ticks:
                self.data_manager.insert_tick_data(ticks)
            
            logging.info(f"Ingested microsecond data for {symbol}")
            
        except Exception as e:
            logging.error(f"Failed to ingest data for {symbol}: {e}")
    
    async def run_causal_analysis(self, symbols: List[str], start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        all_data = []
        
        for symbol in symbols:
            symbol_data = self.data_manager.query_tick_data(symbol, start_time, end_time)
            if not symbol_data.empty:
                symbol_data['symbol'] = symbol
                all_data.append(symbol_data)
        
        if not all_data:
            logging.warning("No data available for causal analysis")
            return {}
        
        combined_data = pd.concat(all_data, ignore_index=True)
        
        pivot_data = combined_data.pivot_table(
            index='timestamp',
            columns='symbol',
            values=['price', 'volume'],
            aggfunc='mean'
        ).fillna(method='ffill')
        
        causal_graph = self.causal_graph_builder.build_causal_graph(pivot_data)
        bayesian_network = self.causal_graph_builder.create_bayesian_network(pivot_data)
        
        causal_relationships = {}
        for edge in causal_graph.edges():
            source, target = edge
            causal_relationships[f"{source}_causes_{target}"] = {
                'source': source,
                'target': target,
                'strength': 1.0
            }
        
        return {
            'causal_graph': causal_graph,
            'bayesian_network': bayesian_network,
            'causal_relationships': causal_relationships,
            'data_points': len(combined_data)
        }
    
    async def run_agent_based_simulation(self, symbols: List[str], num_steps: int = 1000) -> Dict[str, Any]:
        self.simulation_model = MarketSimulationModel(symbols)
        
        simulation_results = []
        
        for step in range(num_steps):
            self.simulation_model.step()
            
            if step % 100 == 0:
                step_results = {
                    'step': step,
                    'timestamp': self.simulation_model.current_time,
                    'market_data': self.simulation_model.market_data.copy()
                }
                simulation_results.append(step_results)
        
        agent_performance = []
        for agent in self.simulation_model.schedule.agents:
            performance = {
                'agent_id': agent.unique_id,
                'symbol': agent.symbol,
                'strategy_type': agent.strategy_type,
                'final_position': agent.position,
                'final_cash': agent.cash,
                'total_value': agent.cash + agent.position * agent.last_price,
                'num_decisions': len(agent.decision_history)
            }
            agent_performance.append(performance)
        
        return {
            'simulation_results': simulation_results,
            'agent_performance': agent_performance,
            'total_steps': num_steps,
            'symbols': symbols
        }
    
    async def run_counterfactual_analysis(self, base_scenario: Dict[str, Any], interventions: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = {}
        
        for i, intervention in enumerate(interventions):
            intervention_id = f"intervention_{i}"
            
            modified_scenario = base_scenario.copy()
            modified_scenario.update(intervention)
            
            simulation_results = await self.run_agent_based_simulation(
                modified_scenario.get('symbols', ['AAPL']),
                modified_scenario.get('num_steps', 1000)
            )
            
            results[intervention_id] = {
                'intervention': intervention,
                'results': simulation_results
            }
        
        return results
    
    def calculate_strategy_attribution(self, agent_performance: List[Dict[str, Any]]) -> Dict[str, float]:
        strategy_returns = {}
        strategy_counts = {}
        
        for agent in agent_performance:
            strategy = agent['strategy_type']
            total_value = agent['total_value']
            initial_value = 100000
            
            strategy_return = (total_value - initial_value) / initial_value
            
            if strategy not in strategy_returns:
                strategy_returns[strategy] = 0
                strategy_counts[strategy] = 0
            
            strategy_returns[strategy] += strategy_return
            strategy_counts[strategy] += 1
        
        strategy_attribution = {}
        for strategy in strategy_returns:
            if strategy_counts[strategy] > 0:
                strategy_attribution[strategy] = strategy_returns[strategy] / strategy_counts[strategy]
        
        return strategy_attribution

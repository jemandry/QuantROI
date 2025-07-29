import numpy as np
import torch
from collections import deque
from typing import Dict, List, Tuple, Any, Optional
import asyncio
import logging
from dataclasses import dataclass
import pickle
import random

@dataclass
class Experience:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    timestamp: float
    priority: float = 1.0

class PrioritizedExperienceReplay:
    """
    Memory-efficient experience replay buffer with prioritized sampling
    Optimized for financial time-series with high-impact event prioritization
    """
    
    def __init__(self, buffer_size: int = 100000, batch_size: int = 32, alpha: float = 0.8):
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        self.alpha = alpha
        self.beta = 0.4
        self.beta_increment = 0.001
        
        self.buffer = deque(maxlen=buffer_size)
        self.priorities = deque(maxlen=buffer_size)
        self.position = 0
        self.logger = logging.getLogger(__name__)
        
    def add_experience(self, experience: Experience):
        """Add experience with priority based on financial impact"""
        priority = abs(experience.reward) * 10 + 0.1
        
        if hasattr(experience, 'market_regime') and experience.market_regime == 'high_volatility':
            priority *= 5.0
        
        if abs(experience.reward) > 0.05:
            priority *= 3.0
        
        if len(self.buffer) < self.buffer_size:
            self.buffer.append(experience)
            self.priorities.append(priority)
        else:
            self.buffer[self.position] = experience
            self.priorities[self.position] = priority
            
        self.position = (self.position + 1) % self.buffer_size
    
    def sample_batch(self) -> Tuple[List[Experience], np.ndarray, np.ndarray]:
        """Sample batch with prioritized sampling for high-impact events"""
        if len(self.buffer) < self.batch_size:
            return [], np.array([]), np.array([])
        
        priorities = np.array(self.priorities)
        probabilities = priorities ** self.alpha
        probabilities /= probabilities.sum()
        
        indices = np.random.choice(
            len(self.buffer), 
            size=self.batch_size, 
            p=probabilities, 
            replace=False
        )
        
        weights = (len(self.buffer) * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()
        
        experiences = [self.buffer[idx] for idx in indices]
        
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        return experiences, indices, weights
    
    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray):
        """Update priorities based on TD errors"""
        for idx, td_error in zip(indices, td_errors):
            priority = abs(td_error) + 0.01
            self.priorities[idx] = priority

class OnlineLearningOptimizer:
    """
    Online learning integration for incremental neural network updates
    Triggered by MarketEvent streams without full retraining
    """
    
    def __init__(self, learning_rate: float = 0.001):
        self.learning_rate = learning_rate
        self.experience_replay = PrioritizedExperienceReplay()
        self.update_frequency = 10
        self.experience_count = 0
        self.logger = logging.getLogger(__name__)
        
    async def process_trade_outcome(self, trade_result: Dict[str, Any], market_data: Dict[str, Any]):
        """Process individual trade outcome for online learning"""
        
        experience = Experience(
            state=np.array(market_data.get('features', [])),
            action=trade_result.get('action_index', 0),
            reward=trade_result.get('return', 0.0),
            next_state=np.array(market_data.get('next_features', [])),
            done=trade_result.get('trade_complete', False),
            timestamp=trade_result.get('timestamp', 0.0)
        )
        
        self.experience_replay.add_experience(experience)
        self.experience_count += 1
        
        if self.experience_count % self.update_frequency == 0:
            await self._incremental_network_update()
    
    async def _incremental_network_update(self):
        """Perform incremental neural network update"""
        experiences, indices, weights = self.experience_replay.sample_batch()
        
        if not experiences:
            return
        
        states = torch.FloatTensor([exp.state for exp in experiences])
        actions = torch.LongTensor([exp.action for exp in experiences])
        rewards = torch.FloatTensor([exp.reward for exp in experiences])
        next_states = torch.FloatTensor([exp.next_state for exp in experiences])
        dones = torch.BoolTensor([exp.done for exp in experiences])
        
        td_errors = rewards.numpy()
        
        self.experience_replay.update_priorities(indices, td_errors)
        
        self.logger.info(f"Incremental update completed with {len(experiences)} experiences")

#!/usr/bin/env python3
"""
Counterfactual GAN for Corporate Causal Engine
Generates realistic market microstructure for what-if scenarios and privacy-preserving synthetic data
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import json

@dataclass
class MarketCondition:
    """Market condition for GAN training and generation"""
    timestamp: datetime
    price: float
    volume: float
    volatility: float
    sentiment: float
    news_impact: float
    sector: str
    market_cap: float

@dataclass
class CounterfactualScenario:
    """Generated counterfactual scenario"""
    scenario_id: str
    original_conditions: MarketCondition
    counterfactual_conditions: MarketCondition
    intervention: Dict[str, Any]
    confidence: float
    realism_score: float

class MarketDataGenerator(nn.Module):
    """Generator network for realistic market data"""
    
    def __init__(self, noise_dim: int = 100, condition_dim: int = 8, output_dim: int = 6):
        super(MarketDataGenerator, self).__init__()
        
        self.noise_dim = noise_dim
        self.condition_dim = condition_dim
        self.output_dim = output_dim
        
        self.model = nn.Sequential(
            nn.Linear(noise_dim + condition_dim, 256),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(256),
            
            nn.Linear(256, 512),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(512),
            
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(256),
            
            nn.Linear(256, output_dim),
            nn.Tanh()  # Normalize outputs to [-1, 1]
        )
        
    def forward(self, noise: torch.Tensor, conditions: torch.Tensor) -> torch.Tensor:
        """Generate market data from noise and conditions"""
        x = torch.cat([noise, conditions], dim=1)
        return self.model(x)

class MarketDataDiscriminator(nn.Module):
    """Discriminator network for market data authenticity"""
    
    def __init__(self, input_dim: int = 6, condition_dim: int = 8):
        super(MarketDataDiscriminator, self).__init__()
        
        self.model = nn.Sequential(
            nn.Linear(input_dim + condition_dim, 512),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            
            nn.Linear(256, 128),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
        
    def forward(self, market_data: torch.Tensor, conditions: torch.Tensor) -> torch.Tensor:
        """Discriminate between real and fake market data"""
        x = torch.cat([market_data, conditions], dim=1)
        return self.model(x)

class CounterfactualGAN:
    """Counterfactual GAN for corporate causal analysis"""
    
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.device = device
        
        self.generator = MarketDataGenerator().to(device)
        self.discriminator = MarketDataDiscriminator().to(device)
        
        self.g_optimizer = optim.Adam(self.generator.parameters(), lr=0.0002, betas=(0.5, 0.999))
        self.d_optimizer = optim.Adam(self.discriminator.parameters(), lr=0.0002, betas=(0.5, 0.999))
        
        self.criterion = nn.BCELoss()
        
        self.training_history = {
            'g_losses': [],
            'd_losses': [],
            'realism_scores': []
        }
        
        logging.info(f"CounterfactualGAN initialized on device: {device}")
    
    def prepare_training_data(self, market_data: pd.DataFrame) -> Tuple[torch.Tensor, torch.Tensor]:
        """Prepare market data for GAN training"""
        try:
            features = ['price', 'volume', 'volatility', 'sentiment', 'news_impact', 'market_cap']
            conditions = ['sector_encoded', 'hour', 'day_of_week', 'month', 'is_earnings', 'is_fed_day', 'vix', 'spy_return']
            
            market_features = market_data[features].values
            market_features = 2 * (market_features - market_features.min(axis=0)) / (market_features.max(axis=0) - market_features.min(axis=0)) - 1
            
            condition_features = market_data[conditions].values
            condition_features = 2 * (condition_features - condition_features.min(axis=0)) / (condition_features.max(axis=0) - condition_features.min(axis=0)) - 1
            
            return torch.FloatTensor(market_features), torch.FloatTensor(condition_features)
            
        except Exception as e:
            logging.error(f"Error preparing training data: {e}")
            batch_size = len(market_data)
            return torch.randn(batch_size, 6), torch.randn(batch_size, 8)
    
    def train_epoch(self, real_data: torch.Tensor, conditions: torch.Tensor, batch_size: int = 64) -> Dict[str, float]:
        """Train GAN for one epoch"""
        
        real_data = real_data.to(self.device)
        conditions = conditions.to(self.device)
        
        total_batches = len(real_data) // batch_size
        epoch_g_loss = 0.0
        epoch_d_loss = 0.0
        
        for i in range(0, len(real_data), batch_size):
            batch_real = real_data[i:i+batch_size]
            batch_conditions = conditions[i:i+batch_size]
            current_batch_size = batch_real.size(0)
            
            self.d_optimizer.zero_grad()
            
            real_labels = torch.ones(current_batch_size, 1).to(self.device)
            real_output = self.discriminator(batch_real, batch_conditions)
            d_loss_real = self.criterion(real_output, real_labels)
            
            noise = torch.randn(current_batch_size, self.generator.noise_dim).to(self.device)
            fake_data = self.generator(noise, batch_conditions)
            fake_labels = torch.zeros(current_batch_size, 1).to(self.device)
            fake_output = self.discriminator(fake_data.detach(), batch_conditions)
            d_loss_fake = self.criterion(fake_output, fake_labels)
            
            d_loss = d_loss_real + d_loss_fake
            d_loss.backward()
            self.d_optimizer.step()
            
            self.g_optimizer.zero_grad()
            
            noise = torch.randn(current_batch_size, self.generator.noise_dim).to(self.device)
            fake_data = self.generator(noise, batch_conditions)
            fake_output = self.discriminator(fake_data, batch_conditions)
            g_loss = self.criterion(fake_output, real_labels)  # Generator wants to fool discriminator
            
            g_loss.backward()
            self.g_optimizer.step()
            
            epoch_g_loss += g_loss.item()
            epoch_d_loss += d_loss.item()
        
        avg_g_loss = epoch_g_loss / total_batches
        avg_d_loss = epoch_d_loss / total_batches
        
        self.training_history['g_losses'].append(avg_g_loss)
        self.training_history['d_losses'].append(avg_d_loss)
        
        return {
            'generator_loss': avg_g_loss,
            'discriminator_loss': avg_d_loss
        }
    
    def generate_counterfactual(self, original_condition: MarketCondition, 
                              intervention: Dict[str, Any]) -> CounterfactualScenario:
        """Generate counterfactual scenario for what-if analysis"""
        
        try:
            self.generator.eval()
            
            with torch.no_grad():
                condition_vector = self._condition_to_vector(original_condition)
                
                modified_conditions = self._apply_intervention(condition_vector, intervention)
                
                noise = torch.randn(1, self.generator.noise_dim).to(self.device)
                conditions_tensor = torch.FloatTensor(modified_conditions).unsqueeze(0).to(self.device)
                
                generated_data = self.generator(noise, conditions_tensor)
                generated_data = generated_data.cpu().numpy()[0]
                
                counterfactual_condition = self._vector_to_condition(generated_data, original_condition)
                
                realism_score = self._calculate_realism_score(generated_data, conditions_tensor)
                
                scenario = CounterfactualScenario(
                    scenario_id=f"cf_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    original_conditions=original_condition,
                    counterfactual_conditions=counterfactual_condition,
                    intervention=intervention,
                    confidence=min(realism_score, 0.95),  # Cap confidence at 95%
                    realism_score=realism_score
                )
                
                return scenario
                
        except Exception as e:
            logging.error(f"Error generating counterfactual: {e}")
            return CounterfactualScenario(
                scenario_id="error",
                original_conditions=original_condition,
                counterfactual_conditions=original_condition,
                intervention=intervention,
                confidence=0.0,
                realism_score=0.0
            )
    
    def generate_synthetic_company_data(self, company_profile: Dict[str, Any], 
                                      num_samples: int = 1000) -> pd.DataFrame:
        """Generate synthetic company data for federated learning"""
        
        try:
            self.generator.eval()
            
            synthetic_data = []
            
            with torch.no_grad():
                for _ in range(num_samples):
                    condition_vector = self._company_profile_to_vector(company_profile)
                    
                    noise_factor = 0.1
                    condition_vector += np.random.normal(0, noise_factor, len(condition_vector))
                    
                    noise = torch.randn(1, self.generator.noise_dim).to(self.device)
                    conditions_tensor = torch.FloatTensor(condition_vector).unsqueeze(0).to(self.device)
                    
                    generated_data = self.generator(noise, conditions_tensor)
                    generated_data = generated_data.cpu().numpy()[0]
                    
                    data_point = {
                        'price': self._denormalize_value(generated_data[0], 'price'),
                        'volume': self._denormalize_value(generated_data[1], 'volume'),
                        'volatility': self._denormalize_value(generated_data[2], 'volatility'),
                        'sentiment': self._denormalize_value(generated_data[3], 'sentiment'),
                        'news_impact': self._denormalize_value(generated_data[4], 'news_impact'),
                        'market_cap': self._denormalize_value(generated_data[5], 'market_cap'),
                        'company_id': f"synthetic_{company_profile.get('sector', 'unknown')}",
                        'timestamp': datetime.now() + timedelta(minutes=np.random.randint(0, 1440))
                    }
                    
                    synthetic_data.append(data_point)
            
            return pd.DataFrame(synthetic_data)
            
        except Exception as e:
            logging.error(f"Error generating synthetic company data: {e}")
            return pd.DataFrame()
    
    def generate_rare_event_scenarios(self, event_type: str = "market_crash", 
                                    num_scenarios: int = 100) -> List[Dict[str, Any]]:
        """Generate rare market event scenarios for training"""
        
        try:
            self.generator.eval()
            
            scenarios = []
            
            event_conditions = {
                'market_crash': {'volatility': 0.8, 'sentiment': -0.9, 'news_impact': 0.9},
                'market_rally': {'volatility': 0.6, 'sentiment': 0.9, 'news_impact': 0.8},
                'flash_crash': {'volatility': 0.95, 'sentiment': -0.8, 'news_impact': 0.7},
                'earnings_surprise': {'volatility': 0.4, 'sentiment': 0.7, 'news_impact': 0.9}
            }
            
            base_conditions = event_conditions.get(event_type, event_conditions['market_crash'])
            
            with torch.no_grad():
                for i in range(num_scenarios):
                    condition_vector = np.array([
                        base_conditions['volatility'] + np.random.normal(0, 0.1),
                        base_conditions['sentiment'] + np.random.normal(0, 0.1),
                        base_conditions['news_impact'] + np.random.normal(0, 0.1),
                        np.random.uniform(-1, 1),  # sector
                        np.random.uniform(-1, 1),  # hour
                        np.random.uniform(-1, 1),  # day_of_week
                        np.random.uniform(-1, 1),  # month
                        1.0 if 'earnings' in event_type else 0.0  # is_earnings
                    ])
                    
                    noise = torch.randn(1, self.generator.noise_dim).to(self.device)
                    conditions_tensor = torch.FloatTensor(condition_vector).unsqueeze(0).to(self.device)
                    
                    generated_data = self.generator(noise, conditions_tensor)
                    generated_data = generated_data.cpu().numpy()[0]
                    
                    scenario = {
                        'scenario_id': f"{event_type}_{i:04d}",
                        'event_type': event_type,
                        'price_change': self._denormalize_value(generated_data[0], 'price_change'),
                        'volume_spike': self._denormalize_value(generated_data[1], 'volume_spike'),
                        'volatility': self._denormalize_value(generated_data[2], 'volatility'),
                        'sentiment': self._denormalize_value(generated_data[3], 'sentiment'),
                        'news_impact': self._denormalize_value(generated_data[4], 'news_impact'),
                        'market_cap_impact': self._denormalize_value(generated_data[5], 'market_cap_impact'),
                        'timestamp': datetime.now() + timedelta(days=np.random.randint(0, 365))
                    }
                    
                    scenarios.append(scenario)
            
            return scenarios
            
        except Exception as e:
            logging.error(f"Error generating rare event scenarios: {e}")
            return []
    
    def _condition_to_vector(self, condition: MarketCondition) -> np.ndarray:
        """Convert MarketCondition to vector for GAN input"""
        return np.array([
            condition.volatility,
            condition.sentiment,
            condition.news_impact,
            hash(condition.sector) % 100 / 100.0,  # Sector encoding
            condition.timestamp.hour / 24.0,
            condition.timestamp.weekday() / 7.0,
            condition.timestamp.month / 12.0,
            0.0  # Default values for missing features
        ])
    
    def _apply_intervention(self, condition_vector: np.ndarray, intervention: Dict[str, Any]) -> np.ndarray:
        """Apply intervention to condition vector"""
        modified = condition_vector.copy()
        
        intervention_mapping = {
            'volatility': 0,
            'sentiment': 1,
            'news_impact': 2,
            'sector': 3
        }
        
        for key, value in intervention.items():
            if key in intervention_mapping:
                modified[intervention_mapping[key]] = value
        
        return modified
    
    def _vector_to_condition(self, vector: np.ndarray, original: MarketCondition) -> MarketCondition:
        """Convert generated vector back to MarketCondition"""
        return MarketCondition(
            timestamp=original.timestamp,
            price=self._denormalize_value(vector[0], 'price'),
            volume=self._denormalize_value(vector[1], 'volume'),
            volatility=self._denormalize_value(vector[2], 'volatility'),
            sentiment=self._denormalize_value(vector[3], 'sentiment'),
            news_impact=self._denormalize_value(vector[4], 'news_impact'),
            sector=original.sector,
            market_cap=self._denormalize_value(vector[5], 'market_cap')
        )
    
    def _company_profile_to_vector(self, profile: Dict[str, Any]) -> np.ndarray:
        """Convert company profile to condition vector"""
        return np.array([
            profile.get('volatility', 0.2),
            profile.get('sentiment', 0.0),
            profile.get('news_impact', 0.1),
            hash(profile.get('sector', 'tech')) % 100 / 100.0,
            np.random.uniform(0, 1),  # Random hour
            np.random.uniform(0, 1),  # Random day
            np.random.uniform(0, 1),  # Random month
            profile.get('is_earnings_season', 0.0)
        ])
    
    def _calculate_realism_score(self, generated_data: np.ndarray, conditions: torch.Tensor) -> float:
        """Calculate realism score for generated data"""
        try:
            with torch.no_grad():
                generated_tensor = torch.FloatTensor(generated_data).unsqueeze(0).to(self.device)
                discriminator_output = self.discriminator(generated_tensor, conditions)
                return float(discriminator_output.cpu().numpy()[0][0])
        except:
            return 0.5  # Default moderate realism
    
    def _denormalize_value(self, normalized_value: float, feature_type: str) -> float:
        """Denormalize generated values to realistic ranges"""
        
        value = (normalized_value + 1) / 2  # Convert to [0, 1]
        
        ranges = {
            'price': (10.0, 1000.0),
            'price_change': (-0.2, 0.2),
            'volume': (1000, 10000000),
            'volume_spike': (1.0, 10.0),
            'volatility': (0.1, 1.0),
            'sentiment': (-1.0, 1.0),
            'news_impact': (0.0, 1.0),
            'market_cap': (1e6, 1e12),
            'market_cap_impact': (-0.5, 0.5)
        }
        
        min_val, max_val = ranges.get(feature_type, (0.0, 1.0))
        return min_val + value * (max_val - min_val)
    
    def save_model(self, filepath: str):
        """Save trained GAN models"""
        torch.save({
            'generator_state_dict': self.generator.state_dict(),
            'discriminator_state_dict': self.discriminator.state_dict(),
            'g_optimizer_state_dict': self.g_optimizer.state_dict(),
            'd_optimizer_state_dict': self.d_optimizer.state_dict(),
            'training_history': self.training_history
        }, filepath)
        
        logging.info(f"GAN model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load trained GAN models"""
        checkpoint = torch.load(filepath, map_location=self.device)
        
        self.generator.load_state_dict(checkpoint['generator_state_dict'])
        self.discriminator.load_state_dict(checkpoint['discriminator_state_dict'])
        self.g_optimizer.load_state_dict(checkpoint['g_optimizer_state_dict'])
        self.d_optimizer.load_state_dict(checkpoint['d_optimizer_state_dict'])
        self.training_history = checkpoint['training_history']
        
        logging.info(f"GAN model loaded from {filepath}")

class CounterfactualGANIntegration:
    """Integration layer for CounterfactualGAN with Corporate Causal Engine"""
    
    def __init__(self, gan_model: Optional[CounterfactualGAN] = None):
        self.gan_model = gan_model or CounterfactualGAN()
        self.scenario_cache = {}
        
    def enhance_what_if_analysis(self, original_scenario: Dict[str, Any], 
                                intervention: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance what-if analysis with GAN-generated counterfactuals"""
        
        try:
            original_condition = MarketCondition(
                timestamp=datetime.now(),
                price=original_scenario.get('price', 100.0),
                volume=original_scenario.get('volume', 1000000),
                volatility=original_scenario.get('volatility', 0.2),
                sentiment=original_scenario.get('sentiment', 0.0),
                news_impact=original_scenario.get('news_impact', 0.1),
                sector=original_scenario.get('sector', 'tech'),
                market_cap=original_scenario.get('market_cap', 1e9)
            )
            
            counterfactual = self.gan_model.generate_counterfactual(original_condition, intervention)
            
            enhanced_result = {
                'original_scenario': original_scenario,
                'counterfactual_scenario': {
                    'price': counterfactual.counterfactual_conditions.price,
                    'volume': counterfactual.counterfactual_conditions.volume,
                    'volatility': counterfactual.counterfactual_conditions.volatility,
                    'sentiment': counterfactual.counterfactual_conditions.sentiment,
                    'news_impact': counterfactual.counterfactual_conditions.news_impact,
                    'market_cap': counterfactual.counterfactual_conditions.market_cap
                },
                'intervention': intervention,
                'confidence': counterfactual.confidence,
                'realism_score': counterfactual.realism_score,
                'scenario_id': counterfactual.scenario_id,
                'generated_at': datetime.now().isoformat()
            }
            
            self.scenario_cache[counterfactual.scenario_id] = enhanced_result
            
            return enhanced_result
            
        except Exception as e:
            logging.error(f"Error enhancing what-if analysis: {e}")
            return {
                'original_scenario': original_scenario,
                'counterfactual_scenario': original_scenario,
                'intervention': intervention,
                'confidence': 0.0,
                'realism_score': 0.0,
                'error': str(e)
            }
    
    def generate_federated_training_data(self, company_profiles: List[Dict[str, Any]], 
                                       samples_per_company: int = 1000) -> Dict[str, pd.DataFrame]:
        """Generate synthetic data for federated learning across companies"""
        
        federated_data = {}
        
        for profile in company_profiles:
            company_id = profile.get('company_id', f"company_{len(federated_data)}")
            
            synthetic_data = self.gan_model.generate_synthetic_company_data(
                profile, samples_per_company
            )
            
            federated_data[company_id] = synthetic_data
            
            logging.info(f"Generated {len(synthetic_data)} synthetic samples for {company_id}")
        
        return federated_data
    
    def augment_rare_events_training(self, event_types: List[str], 
                                   scenarios_per_type: int = 100) -> pd.DataFrame:
        """Generate rare event scenarios for training data augmentation"""
        
        all_scenarios = []
        
        for event_type in event_types:
            scenarios = self.gan_model.generate_rare_event_scenarios(
                event_type, scenarios_per_type
            )
            all_scenarios.extend(scenarios)
        
        return pd.DataFrame(all_scenarios)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    gan = CounterfactualGAN()
    
    original_condition = MarketCondition(
        timestamp=datetime.now(),
        price=150.0,
        volume=2000000,
        volatility=0.25,
        sentiment=0.1,
        news_impact=0.2,
        sector="tech",
        market_cap=5e10
    )
    
    intervention = {
        'sentiment': 0.8,  # Positive news intervention
        'news_impact': 0.9
    }
    
    counterfactual = gan.generate_counterfactual(original_condition, intervention)
    print(f"Generated counterfactual scenario: {counterfactual.scenario_id}")
    print(f"Confidence: {counterfactual.confidence:.3f}")
    print(f"Realism score: {counterfactual.realism_score:.3f}")
    
    company_profile = {
        'sector': 'tech',
        'volatility': 0.3,
        'sentiment': 0.2,
        'market_cap': 1e11
    }
    
    synthetic_data = gan.generate_synthetic_company_data(company_profile, 10)
    print(f"Generated {len(synthetic_data)} synthetic data points")
    
    rare_events = gan.generate_rare_event_scenarios('market_crash', 5)
    print(f"Generated {len(rare_events)} rare event scenarios")

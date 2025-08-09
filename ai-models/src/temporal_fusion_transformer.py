import asyncio
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict

try:
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import mean_squared_error, mean_absolute_error
except ImportError:
    StandardScaler = None
    LabelEncoder = None
    mean_squared_error = None
    mean_absolute_error = None

logger = logging.getLogger(__name__)

@dataclass
class TFTConfig:
    """Configuration for Temporal Fusion Transformer"""
    input_size: int = 50
    hidden_size: int = 128
    num_heads: int = 8
    num_layers: int = 3
    dropout: float = 0.1
    prediction_length: int = 10
    context_length: int = 30
    static_features: int = 5
    time_varying_features: int = 20

class VariableSelectionNetwork(nn.Module):
    """Variable Selection Network for TFT"""
    
    def __init__(self, input_size: int, hidden_size: int, dropout: float = 0.1):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        self.flattened_grn = GatedResidualNetwork(
            input_size, hidden_size, dropout=dropout
        )
        self.single_variable_grns = nn.ModuleList([
            GatedResidualNetwork(1, hidden_size, dropout=dropout)
            for _ in range(input_size)
        ])
        
        self.softmax = nn.Softmax(dim=-1)
    
    def forward(self, flattened_embedding, time_steps=None):
        sparse_weights = self.flattened_grn(flattened_embedding)
        sparse_weights = self.softmax(sparse_weights).unsqueeze(-1)
        
        processed_inputs = []
        for i, grn in enumerate(self.single_variable_grns):
            processed_inputs.append(
                grn(flattened_embedding[..., i:i+1])
            )
        
        processed_inputs = torch.stack(processed_inputs, dim=-2)
        
        outputs = sparse_weights * processed_inputs
        
        return outputs, sparse_weights

class GatedResidualNetwork(nn.Module):
    """Gated Residual Network component"""
    
    def __init__(self, input_size: int, hidden_size: int, output_size: Optional[int] = None, 
                 dropout: float = 0.1, use_time_distributed: bool = True):
        super().__init__()
        
        if output_size is None:
            output_size = input_size
            
        self.input_size = input_size
        self.output_size = output_size
        self.hidden_size = hidden_size
        
        self.linear1 = nn.Linear(input_size, hidden_size)
        self.linear2 = nn.Linear(hidden_size, hidden_size)
        self.linear3 = nn.Linear(hidden_size, output_size)
        self.linear4 = nn.Linear(hidden_size, output_size)
        
        self.dropout = nn.Dropout(dropout)
        self.gate_activation = nn.Sigmoid()
        self.activation = nn.ELU()
        
        if input_size != output_size:
            self.skip_layer = nn.Linear(input_size, output_size)
        else:
            self.skip_layer = None
    
    def forward(self, x):
        hidden = self.activation(self.linear1(x))
        hidden = self.dropout(hidden)
        hidden = self.linear2(hidden)
        
        gate = self.gate_activation(self.linear4(hidden))
        output = self.linear3(hidden)
        output = gate * output
        
        if self.skip_layer is not None:
            output = output + self.skip_layer(x)
        else:
            output = output + x
            
        return output

class InterpretableMultiHeadAttention(nn.Module):
    """Interpretable Multi-Head Attention for TFT"""
    
    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % num_heads == 0
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        self.w_q = nn.Linear(d_model, d_model, bias=False)
        self.w_k = nn.Linear(d_model, d_model, bias=False)
        self.w_v = nn.Linear(d_model, d_model, bias=False)
        self.w_o = nn.Linear(d_model, d_model)
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, query, key, value, mask=None):
        batch_size = query.size(0)
        
        Q = self.w_q(query).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        K = self.w_k(key).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        V = self.w_v(value).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        
        attention_weights = torch.matmul(Q, K.transpose(-2, -1)) / np.sqrt(self.d_k)
        
        if mask is not None:
            attention_weights = attention_weights.masked_fill(mask == 0, -1e9)
        
        attention_weights = F.softmax(attention_weights, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        context = torch.matmul(attention_weights, V)
        context = context.transpose(1, 2).contiguous().view(
            batch_size, -1, self.d_model
        )
        
        output = self.w_o(context)
        
        return output, attention_weights

class TemporalFusionTransformer(nn.Module):
    """Temporal Fusion Transformer for financial time series prediction"""
    
    def __init__(self, config: TFTConfig):
        super().__init__()
        self.config = config
        
        self.static_vsn = VariableSelectionNetwork(
            config.static_features, config.hidden_size, config.dropout
        )
        self.temporal_vsn = VariableSelectionNetwork(
            config.time_varying_features, config.hidden_size, config.dropout
        )
        
        self.static_context_grn = GatedResidualNetwork(
            config.static_features, config.hidden_size, config.hidden_size, config.dropout
        )
        
        self.encoder = nn.LSTM(
            config.hidden_size, config.hidden_size, 
            batch_first=True, dropout=config.dropout
        )
        self.decoder = nn.LSTM(
            config.hidden_size, config.hidden_size,
            batch_first=True, dropout=config.dropout
        )
        
        self.attention = InterpretableMultiHeadAttention(
            config.hidden_size, config.num_heads, config.dropout
        )
        
        self.output_grn = GatedResidualNetwork(
            config.hidden_size, config.hidden_size, 1, config.dropout
        )
        
        self.quantile_heads = nn.ModuleList([
            nn.Linear(config.hidden_size, 1) for _ in range(3)  # 10%, 50%, 90%
        ])
        
    def forward(self, static_features, temporal_features, future_features=None):
        batch_size, seq_len, _ = temporal_features.shape
        
        static_selected, static_weights = self.static_vsn(static_features)
        static_context = self.static_context_grn(static_selected.squeeze(-2))
        
        temporal_selected, temporal_weights = self.temporal_vsn(
            temporal_features.view(batch_size * seq_len, -1)
        )
        temporal_selected = temporal_selected.view(batch_size, seq_len, -1)
        
        encoder_output, (hidden, cell) = self.encoder(temporal_selected)
        
        if future_features is not None:
            decoder_input = future_features
        else:
            decoder_input = encoder_output[:, -1:, :].repeat(1, self.config.prediction_length, 1)
        
        decoder_output, _ = self.decoder(decoder_input, (hidden, cell))
        
        attended_output, attention_weights = self.attention(
            decoder_output, encoder_output, encoder_output
        )
        
        output = self.output_grn(attended_output)
        
        quantile_outputs = []
        for head in self.quantile_heads:
            quantile_outputs.append(head(attended_output))
        
        return {
            'predictions': output,
            'quantiles': torch.cat(quantile_outputs, dim=-1),
            'attention_weights': attention_weights,
            'static_weights': static_weights,
            'temporal_weights': temporal_weights
        }

class QuantileLoss(nn.Module):
    """Quantile loss for TFT training"""
    
    def __init__(self, quantiles: List[float] = [0.1, 0.5, 0.9]):
        super().__init__()
        self.quantiles = quantiles
    
    def forward(self, predictions, targets):
        losses = []
        for i, q in enumerate(self.quantiles):
            error = targets - predictions[..., i:i+1]
            loss = torch.max(q * error, (q - 1) * error)
            losses.append(loss.mean())
        return sum(losses) / len(losses)

class FinancialTimeSeriesDataset(Dataset):
    """Dataset for financial time series data"""
    
    def __init__(self, data: pd.DataFrame, config: TFTConfig, 
                 target_column: str = 'returns'):
        self.data = data
        self.config = config
        self.target_column = target_column
        
        self.static_features = self._prepare_static_features()
        self.temporal_features = self._prepare_temporal_features()
        self.targets = self._prepare_targets()
        
    def _prepare_static_features(self) -> torch.Tensor:
        """Prepare static features (market regime, sector, etc.)"""
        static_data = np.random.randn(len(self.data), self.config.static_features)
        return torch.FloatTensor(static_data)
    
    def _prepare_temporal_features(self) -> torch.Tensor:
        """Prepare temporal features"""
        feature_cols = [col for col in self.data.columns if col != self.target_column]
        temporal_data = self.data[feature_cols].values
        
        if temporal_data.shape[1] < self.config.time_varying_features:
            padding = np.zeros((temporal_data.shape[0], 
                              self.config.time_varying_features - temporal_data.shape[1]))
            temporal_data = np.concatenate([temporal_data, padding], axis=1)
        else:
            temporal_data = temporal_data[:, :self.config.time_varying_features]
        
        return torch.FloatTensor(temporal_data)
    
    def _prepare_targets(self) -> torch.Tensor:
        """Prepare target values"""
        targets = self.data[self.target_column].values
        return torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.data) - self.config.context_length - self.config.prediction_length + 1
    
    def __getitem__(self, idx):
        context_start = idx
        context_end = idx + self.config.context_length
        pred_end = context_end + self.config.prediction_length
        
        static_feat = self.static_features[context_start]
        temporal_feat = self.temporal_features[context_start:context_end]
        target = self.targets[context_end:pred_end]
        
        return static_feat, temporal_feat, target

class TFTPredictor:
    """Temporal Fusion Transformer predictor for financial markets"""
    
    def __init__(self, config: TFTConfig = None):
        self.config = config or TFTConfig()
        self.model = TemporalFusionTransformer(self.config)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        self.scaler = StandardScaler() if StandardScaler else None
        self.is_trained = False
        
        logger.info(f"Initialized TFT with config: {asdict(self.config)}")
    
    def prepare_market_data(self, market_data: Dict[str, Any]) -> torch.Tensor:
        """Prepare market data for TFT prediction"""
        features = []
        
        if 'price_data' in market_data:
            price_data = market_data['price_data']
            features.extend([
                price_data.get('returns', 0),
                price_data.get('volatility', 0),
                price_data.get('volume_normalized', 0),
                price_data.get('high_low_ratio', 1),
                price_data.get('close_open_ratio', 1)
            ])
        
        if 'technical_indicators' in market_data:
            tech = market_data['technical_indicators']
            features.extend([
                tech.get('rsi', 50) / 100,  # Normalize
                tech.get('macd_normalized', 0),
                tech.get('bollinger_position', 0.5),
                tech.get('momentum', 0),
                tech.get('trend_strength', 0)
            ])
        
        if 'market_conditions' in market_data:
            conditions = market_data['market_conditions']
            features.extend([
                conditions.get('vix_normalized', 0.5),
                conditions.get('sector_momentum', 0),
                conditions.get('market_regime', 0),
                conditions.get('correlation_spy', 0),
                conditions.get('beta_adjusted', 1)
            ])
        
        if 'sentiment' in market_data:
            sentiment = market_data['sentiment']
            features.extend([
                sentiment.get('news_sentiment', 0),
                sentiment.get('social_sentiment', 0),
                sentiment.get('options_sentiment', 0),
                sentiment.get('analyst_sentiment', 0),
                sentiment.get('earnings_sentiment', 0)
            ])
        
        while len(features) < self.config.time_varying_features:
            features.append(0.0)
        
        return torch.FloatTensor(features[:self.config.time_varying_features])
    
    def predict(self, market_data: Dict[str, Any], 
                prediction_horizon: int = 10) -> Dict[str, Any]:
        """Make predictions using TFT"""
        
        if not self.is_trained:
            logger.warning("Model not trained, using mock predictions")
            return self._generate_mock_predictions(prediction_horizon)
        
        self.model.eval()
        with torch.no_grad():
            temporal_features = self.prepare_market_data(market_data)
            static_features = torch.randn(self.config.static_features)  # Mock static features
            
            temporal_features = temporal_features.unsqueeze(0).unsqueeze(0)
            static_features = static_features.unsqueeze(0)
            
            temporal_features = temporal_features.repeat(1, self.config.context_length, 1)
            
            output = self.model(static_features, temporal_features)
            
            predictions = output['predictions'].squeeze().cpu().numpy()
            quantiles = output['quantiles'].squeeze().cpu().numpy()
            
            return {
                'predictions': predictions.tolist(),
                'quantile_10': quantiles[:, 0].tolist(),
                'quantile_50': quantiles[:, 1].tolist(),
                'quantile_90': quantiles[:, 2].tolist(),
                'confidence_intervals': {
                    'lower': quantiles[:, 0].tolist(),
                    'upper': quantiles[:, 2].tolist()
                },
                'prediction_horizon': prediction_horizon,
                'model_confidence': 0.85,
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_mock_predictions(self, horizon: int) -> Dict[str, Any]:
        """Generate mock predictions for testing"""
        base_return = np.random.normal(0.001, 0.02)
        predictions = []
        quantile_10 = []
        quantile_50 = []
        quantile_90 = []
        
        for i in range(horizon):
            trend = base_return * (1 + i * 0.1)
            noise = np.random.normal(0, 0.01)
            pred = trend + noise
            
            predictions.append(pred)
            quantile_10.append(pred - 0.02)
            quantile_50.append(pred)
            quantile_90.append(pred + 0.02)
        
        return {
            'predictions': predictions,
            'quantile_10': quantile_10,
            'quantile_50': quantile_50,
            'quantile_90': quantile_90,
            'confidence_intervals': {
                'lower': quantile_10,
                'upper': quantile_90
            },
            'prediction_horizon': horizon,
            'model_confidence': 0.75,
            'timestamp': datetime.now().isoformat(),
            'note': 'Mock predictions - model not trained'
        }
    
    def train(self, train_data: pd.DataFrame, val_data: pd.DataFrame,
              epochs: int = 100, batch_size: int = 32, learning_rate: float = 0.001):
        """Train the TFT model"""
        
        train_dataset = FinancialTimeSeriesDataset(train_data, self.config)
        val_dataset = FinancialTimeSeriesDataset(val_data, self.config)
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = QuantileLoss()
        
        best_val_loss = float('inf')
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0
            for batch_idx, (static_feat, temporal_feat, targets) in enumerate(train_loader):
                static_feat = static_feat.to(self.device)
                temporal_feat = temporal_feat.to(self.device)
                targets = targets.to(self.device)
                
                optimizer.zero_grad()
                output = self.model(static_feat, temporal_feat)
                loss = criterion(output['quantiles'], targets.unsqueeze(-1))
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for static_feat, temporal_feat, targets in val_loader:
                    static_feat = static_feat.to(self.device)
                    temporal_feat = temporal_feat.to(self.device)
                    targets = targets.to(self.device)
                    
                    output = self.model(static_feat, temporal_feat)
                    loss = criterion(output['quantiles'], targets.unsqueeze(-1))
                    val_loss += loss.item()
            
            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(val_loader)
            
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                self.save_model("best_tft_model.pth")
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
        
        self.is_trained = True
        logger.info("TFT training completed")
    
    def save_model(self, path: str):
        """Save the trained model"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': asdict(self.config),
            'scaler': self.scaler
        }, path)
        logger.info(f"TFT model saved to {path}")
    
    def load_model(self, path: str):
        """Load a trained model"""
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.config = TFTConfig(**checkpoint['config'])
            self.model = TemporalFusionTransformer(self.config).to(self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.scaler = checkpoint.get('scaler', self.scaler)
            self.is_trained = True
            logger.info(f"TFT model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load TFT model: {e}")

async def main():
    """Example usage of TFT predictor"""
    
    config = TFTConfig(
        prediction_length=5,
        context_length=20,
        hidden_size=64
    )
    predictor = TFTPredictor(config)
    
    market_data = {
        'price_data': {
            'returns': 0.01,
            'volatility': 0.25,
            'volume_normalized': 0.8
        },
        'technical_indicators': {
            'rsi': 65,
            'macd_normalized': 0.2,
            'momentum': 0.05
        },
        'market_conditions': {
            'vix_normalized': 0.6,
            'sector_momentum': 0.02,
            'market_regime': 1
        },
        'sentiment': {
            'news_sentiment': 0.1,
            'social_sentiment': -0.05
        }
    }
    
    result = predictor.predict(market_data)
    print("TFT Prediction Results:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())

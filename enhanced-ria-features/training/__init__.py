"""
Custom Stock Data Training Module
Real-time learning system for user-provided stock data
"""

from .custom_stock_data_trainer import CustomStockDataTrainer, train_on_apple_stock, train_on_multiple_stocks

__all__ = [
    'CustomStockDataTrainer',
    'train_on_apple_stock', 
    'train_on_multiple_stocks'
]

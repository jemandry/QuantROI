#!/usr/bin/env python3
"""
Sample Stock Data Generator for QuantROI Training
Creates realistic sample data for testing the learning system
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import random

def generate_sample_stock_data(
    symbol: str = "AAPL",
    days: int = 30,
    start_price: float = 150.0,
    volatility: float = 0.02,
    trend: float = 0.001
) -> pd.DataFrame:
    """
    Generate realistic sample stock data for training
    
    Args:
        symbol: Stock symbol
        days: Number of days of data
        start_price: Starting price
        volatility: Daily volatility (standard deviation)
        trend: Daily trend (drift)
    
    Returns:
        DataFrame with OHLCV data
    """
    
    timestamps = []
    current_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        market_open = current_date.replace(hour=9, minute=30, second=0, microsecond=0)
        
        for minute in range(390):  # 390 minutes in trading day
            timestamps.append(market_open + timedelta(minutes=minute))
        
        current_date += timedelta(days=1)
    
    n_points = len(timestamps)
    dt = 1/390  # 1 minute as fraction of trading day
    
    returns = np.random.normal(trend * dt, volatility * np.sqrt(dt), n_points)
    
    for i in range(1, len(returns)):
        if abs(returns[i-1]) > 2 * volatility:
            returns[i] *= 0.5
        
        if abs(returns[i-1]) > volatility:
            returns[i] *= 1.5
    
    log_prices = np.cumsum(returns)
    prices = start_price * np.exp(log_prices)
    
    data = []
    for i in range(0, len(prices), 5):  # 5-minute bars
        if i + 4 < len(prices):
            price_slice = prices[i:i+5]
            
            open_price = price_slice[0]
            high_price = np.max(price_slice)
            low_price = np.min(price_slice)
            close_price = price_slice[-1]
            
            price_change = abs(close_price - open_price) / open_price
            base_volume = random.randint(50000, 200000)
            volume = int(base_volume * (1 + price_change * 10))
            
            data.append({
                'timestamp': timestamps[i].isoformat(),
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
    
    return pd.DataFrame(data)

def generate_sample_with_news_events(
    symbol: str = "AAPL",
    days: int = 30,
    start_price: float = 150.0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate sample stock data with corresponding news events
    
    Returns:
        Tuple of (price_data, news_data)
    """
    
    price_data = generate_sample_stock_data(symbol, days, start_price)
    
    news_events = []
    news_templates = [
        "{symbol} reports strong quarterly earnings",
        "{symbol} announces new product launch",
        "{symbol} CEO speaks at major conference",
        "{symbol} receives analyst upgrade",
        "{symbol} faces regulatory scrutiny",
        "{symbol} announces partnership deal",
        "{symbol} reports supply chain issues",
        "{symbol} beats revenue expectations"
    ]
    
    for day in range(days):
        num_events = random.randint(1, 3)
        
        for _ in range(num_events):
            event_time = datetime.now() - timedelta(days=days-day) + timedelta(
                hours=random.randint(6, 20),
                minutes=random.randint(0, 59)
            )
            
            headline = random.choice(news_templates).format(symbol=symbol)
            
            sentiment = random.uniform(-1, 1)
            
            news_events.append({
                'timestamp': event_time.isoformat(),
                'symbol': symbol,
                'headline': headline,
                'sentiment': round(sentiment, 2),
                'source': random.choice(['Reuters', 'Bloomberg', 'CNBC', 'WSJ'])
            })
    
    news_data = pd.DataFrame(news_events)
    return price_data, news_data

def save_sample_data(symbol: str = "AAPL", output_dir: str = "./sample_data"):
    """Save sample data files for training"""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    price_data, news_data = generate_sample_with_news_events(symbol)
    
    price_file = f"{output_dir}/{symbol}_price_data.csv"
    news_file = f"{output_dir}/{symbol}_news_data.csv"
    
    price_data.to_csv(price_file, index=False)
    news_data.to_csv(news_file, index=False)
    
    price_json = f"{output_dir}/{symbol}_price_data.json"
    news_json = f"{output_dir}/{symbol}_news_data.json"
    
    price_data.to_json(price_json, orient='records', date_format='iso')
    news_data.to_json(news_json, orient='records', date_format='iso')
    
    print(f"Sample data saved:")
    print(f"  Price data: {price_file} ({len(price_data)} records)")
    print(f"  News data: {news_file} ({len(news_data)} records)")
    print(f"  JSON versions also saved")
    
    return price_file, news_file

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate sample stock data for QuantROI training')
    parser.add_argument('--symbol', default='AAPL', help='Stock symbol')
    parser.add_argument('--days', type=int, default=30, help='Number of days of data')
    parser.add_argument('--start-price', type=float, default=150.0, help='Starting price')
    parser.add_argument('--output-dir', default='./sample_data', help='Output directory')
    
    args = parser.parse_args()
    
    print(f"Generating sample data for {args.symbol}...")
    price_file, news_file = save_sample_data(
        symbol=args.symbol,
        output_dir=args.output_dir
    )
    
    print(f"\nTo train QuantROI with this data, run:")
    print(f"python custom_stock_data_trainer.py --symbol {args.symbol} --data-file {price_file}")

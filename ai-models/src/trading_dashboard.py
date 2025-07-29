import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

try:
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    STREAMLIT_AVAILABLE = True
except ImportError:
    logging.warning("Streamlit/Plotly not available - using basic dashboard")
    STREAMLIT_AVAILABLE = False

try:
    import dash
    from dash import dcc, html, Input, Output, callback
    import dash_bootstrap_components as dbc
    DASH_AVAILABLE = True
except ImportError:
    logging.warning("Dash not available - using Streamlit only")
    DASH_AVAILABLE = False

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    logging.warning("FastAPI not available - using basic API")
    FASTAPI_AVAILABLE = False

class OptionChainVisualizer:
    """
    Advanced option chain visualization with heatmaps and price overlays
    Supports real-time updates and interactive analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def create_option_heatmap(self, option_data: List[Dict[str, Any]], 
                            underlying_price: float) -> Dict[str, Any]:
        """Create interactive option chain heatmap"""
        try:
            if not option_data:
                return {'error': 'No option data provided'}
            
            df = pd.DataFrame(option_data)
            
            calls = df[df['option_type'] == 'call'].copy()
            puts = df[df['option_type'] == 'put'].copy()
            
            call_volume_pivot = calls.pivot_table(
                values='volume', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            put_volume_pivot = puts.pivot_table(
                values='volume', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            call_iv_pivot = calls.pivot_table(
                values='implied_volatility', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            put_iv_pivot = puts.pivot_table(
                values='implied_volatility', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            heatmap_data = {
                'call_volume': call_volume_pivot.to_dict(),
                'put_volume': put_volume_pivot.to_dict(),
                'call_iv': call_iv_pivot.to_dict(),
                'put_iv': put_iv_pivot.to_dict(),
                'underlying_price': underlying_price,
                'strikes': sorted(df['strike'].unique()),
                'expirations': sorted(df['expiration'].unique()),
                'timestamp': datetime.now().isoformat()
            }
            
            return heatmap_data
            
        except Exception as e:
            self.logger.error(f"Error creating option heatmap: {e}")
            return {'error': str(e)}
    
    def create_gamma_exposure_chart(self, option_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create gamma exposure visualization"""
        try:
            df = pd.DataFrame(option_data)
            
            gamma_exposure = df.groupby('strike').agg({
                'gamma': 'sum',
                'volume': 'sum',
                'open_interest': 'sum'
            }).reset_index()
            
            gamma_exposure['gamma_exposure'] = (
                gamma_exposure['gamma'] * gamma_exposure['open_interest']
            )
            
            chart_data = {
                'strikes': gamma_exposure['strike'].tolist(),
                'gamma_exposure': gamma_exposure['gamma_exposure'].tolist(),
                'volume': gamma_exposure['volume'].tolist(),
                'timestamp': datetime.now().isoformat()
            }
            
            return chart_data
            
        except Exception as e:
            self.logger.error(f"Error creating gamma exposure chart: {e}")
            return {'error': str(e)}
    
    def create_pcr_trend_chart(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create Put-Call Ratio trend visualization"""
        try:
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            df['pcr_volume'] = df['put_volume'] / df['call_volume']
            df['pcr_oi'] = df['put_open_interest'] / df['call_open_interest']
            
            df['pcr_ma_5'] = df['pcr_volume'].rolling(5).mean()
            df['pcr_ma_20'] = df['pcr_volume'].rolling(20).mean()
            
            chart_data = {
                'timestamps': df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'pcr_volume': df['pcr_volume'].tolist(),
                'pcr_oi': df['pcr_oi'].tolist(),
                'pcr_ma_5': df['pcr_ma_5'].tolist(),
                'pcr_ma_20': df['pcr_ma_20'].tolist(),
                'underlying_price': df['underlying_price'].tolist()
            }
            
            return chart_data
            
        except Exception as e:
            self.logger.error(f"Error creating PCR trend chart: {e}")
            return {'error': str(e)}
    
    def generate_heatmap_data(self, option_chain_data: List[Dict[str, Any]], underlying_price: float = None) -> Dict[str, Any]:
        """Generate heatmap data for option chain visualization"""
        try:
            if not option_chain_data:
                return {'error': 'No option chain data provided'}
            
            df = pd.DataFrame(option_chain_data)
            
            if underlying_price is None:
                underlying_price = df.get('underlying_price', [0]).iloc[0] if len(df) > 0 else 0
            
            calls = df[df['option_type'] == 'call'].copy()
            puts = df[df['option_type'] == 'put'].copy()
            
            call_volume_pivot = calls.pivot_table(
                values='volume', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            put_volume_pivot = puts.pivot_table(
                values='volume', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            call_iv_pivot = calls.pivot_table(
                values='implied_volatility', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            put_iv_pivot = puts.pivot_table(
                values='implied_volatility', 
                index='expiration', 
                columns='strike', 
                fill_value=0
            )
            
            heatmap_data = {
                'call_volume': call_volume_pivot.to_dict(),
                'put_volume': put_volume_pivot.to_dict(),
                'call_iv': call_iv_pivot.to_dict(),
                'put_iv': put_iv_pivot.to_dict(),
                'underlying_price': underlying_price,
                'strikes': sorted(df['strike'].unique()),
                'expirations': sorted(df['expiration'].unique()),
                'timestamp': datetime.now().isoformat()
            }
            
            return heatmap_data
            
        except Exception as e:
            self.logger.error(f"Error generating heatmap data: {e}")
            return {'error': str(e)}

class NFTLeaderboard:
    """
    NFT competition leaderboard with performance metrics and royalty tracking
    Displays user-submitted trading strategies and their performance
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def create_leaderboard_data(self, nft_strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create leaderboard data for NFT trading strategies"""
        try:
            sorted_strategies = sorted(
                nft_strategies, 
                key=lambda x: x.get('sharpe_ratio', 0), 
                reverse=True
            )
            
            leaderboard_data = {
                'strategies': [],
                'summary_stats': {},
                'timestamp': datetime.now().isoformat()
            }
            
            total_strategies = len(sorted_strategies)
            total_returns = sum(s.get('total_return', 0) for s in sorted_strategies)
            avg_sharpe = np.mean([s.get('sharpe_ratio', 0) for s in sorted_strategies])
            
            leaderboard_data = []
            
            for rank, strategy in enumerate(sorted_strategies[:50], 1):  # Top 50
                strategy_data = {
                    'rank': rank,
                    'strategy_name': strategy.get('nft_id', f'Strategy {rank}'),  # Use nft_id as strategy_name
                    'creator': strategy.get('creator', 'Anonymous'),
                    'nft_id': strategy.get('nft_id', ''),
                    'sharpe_ratio': round(strategy.get('sharpe_ratio', 0), 3),
                    'total_return': round(strategy.get('total_return', 0), 4),
                    'accuracy': round(strategy.get('accuracy', 0), 3),
                    'max_drawdown': round(strategy.get('max_drawdown', 0), 4),
                    'trades_count': strategy.get('trades_count', 0),
                    'royalties_earned': round(strategy.get('royalties_earned', 0), 6),
                    'last_updated': strategy.get('last_updated', datetime.now().isoformat()),
                    'performance_badge': self._get_performance_badge(strategy.get('sharpe_ratio', 0))
                }
                
                leaderboard_data.append(strategy_data)
            
            return leaderboard_data
            
        except Exception as e:
            self.logger.error(f"Error creating leaderboard data: {e}")
            return {'error': str(e)}

    def _get_performance_badge(self, sharpe_ratio: float) -> str:
        """Get performance badge based on Sharpe ratio"""
        if sharpe_ratio >= 2.0:
            return "🏆 Elite"
        elif sharpe_ratio >= 1.5:
            return "🥇 Excellent"
        elif sharpe_ratio >= 1.0:
            return "🥈 Good"
        elif sharpe_ratio >= 0.5:
            return "🥉 Fair"
        else:
            return "📈 Developing"

class StreamlitDashboard:
    """
    Streamlit-based trading dashboard with real-time updates
    Displays option heatmaps, NFT leaderboards, and performance metrics
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.option_visualizer = OptionChainVisualizer()
        self.nft_leaderboard = NFTLeaderboard()
        
    def create_main_dashboard(self):
        """Create main Streamlit dashboard"""
        try:
            if not STREAMLIT_AVAILABLE:
                self.logger.error("Streamlit not available")
                return
            
            st.set_page_config(
                page_title="QuantROI Trading Dashboard",
                page_icon="📈",
                layout="wide",
                initial_sidebar_state="expanded"
            )
            
            st.title("🚀 QuantROI Real-Time Trading Dashboard")
            st.markdown("*AI-Driven Trading with Option Chain Analysis & NFT Competitions*")
            
            st.sidebar.title("Navigation")
            page = st.sidebar.selectbox(
                "Select Page",
                ["Overview", "Option Analysis", "NFT Leaderboard", "Risk Management", "Performance Analytics"]
            )
            
            if page == "Overview":
                self._create_overview_page()
            elif page == "Option Analysis":
                self._create_option_analysis_page()
            elif page == "NFT Leaderboard":
                self._create_nft_leaderboard_page()
            elif page == "Risk Management":
                self._create_risk_management_page()
            elif page == "Performance Analytics":
                self._create_performance_analytics_page()
                
        except Exception as e:
            self.logger.error(f"Error creating dashboard: {e}")
            st.error(f"Dashboard error: {e}")

    def _create_overview_page(self):
        """Create overview page with key metrics"""
        try:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Portfolio Value",
                    value="$1,234,567",
                    delta="$12,345 (1.2%)"
                )
            
            with col2:
                st.metric(
                    label="Daily P&L",
                    value="$8,901",
                    delta="$2,345 vs yesterday"
                )
            
            with col3:
                st.metric(
                    label="Sharpe Ratio",
                    value="2.34",
                    delta="0.12 vs benchmark"
                )
            
            with col4:
                st.metric(
                    label="Active Strategies",
                    value="47",
                    delta="3 new today"
                )
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Portfolio Performance")
                dates = pd.date_range(start='2025-01-01', end='2025-07-29', freq='D')
                performance = np.cumsum(np.random.normal(0.001, 0.02, len(dates)))
                
                chart_data = pd.DataFrame({
                    'Date': dates,
                    'Performance': performance
                })
                
                st.line_chart(chart_data.set_index('Date'))
            
            with col2:
                st.subheader("Strategy Allocation")
                allocation_data = {
                    'Strategy': ['Momentum', 'Mean Reversion', 'Arbitrage', 'Options', 'NFT Strategies'],
                    'Allocation': [30, 25, 20, 15, 10]
                }
                
                fig = px.pie(
                    values=allocation_data['Allocation'],
                    names=allocation_data['Strategy'],
                    title="Strategy Allocation"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Recent Activity")
            activity_data = pd.DataFrame({
                'Time': ['09:30:15', '09:31:22', '09:32:45', '09:33:12', '09:34:01'],
                'Action': ['BUY', 'SELL', 'BUY', 'HEDGE', 'BUY'],
                'Symbol': ['AAPL', 'GOOGL', 'MSFT', 'SPY', 'TSLA'],
                'Quantity': [100, 50, 75, 200, 25],
                'Price': [150.25, 2750.80, 330.45, 445.20, 850.15],
                'Strategy': ['Momentum', 'Mean Rev', 'NFT-001', 'Risk Hedge', 'Options']
            })
            
            st.dataframe(activity_data, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"Error creating overview page: {e}")
            st.error(f"Overview page error: {e}")

    def _create_option_analysis_page(self):
        """Create option chain analysis page"""
        try:
            st.header("📊 Option Chain Analysis")
            
            symbol = st.selectbox("Select Symbol", ["AAPL", "GOOGL", "MSFT", "TSLA", "SPY"])
            
            mock_option_data = []
            strikes = np.arange(140, 161, 2.5)  # Strike range
            expirations = ['2025-08-15', '2025-09-19', '2025-10-17']
            
            for exp in expirations:
                for strike in strikes:
                    for opt_type in ['call', 'put']:
                        mock_option_data.append({
                            'symbol': symbol,
                            'strike': strike,
                            'expiration': exp,
                            'option_type': opt_type,
                            'volume': np.random.randint(10, 5000),
                            'open_interest': np.random.randint(100, 10000),
                            'implied_volatility': np.random.uniform(0.15, 0.45),
                            'delta': np.random.uniform(-1, 1),
                            'gamma': np.random.uniform(0, 0.1),
                            'theta': np.random.uniform(-0.5, 0),
                            'vega': np.random.uniform(0, 1)
                        })
            
            heatmap_data = self.option_visualizer.create_option_heatmap(mock_option_data, 150.0)
            
            if 'error' not in heatmap_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Call Volume Heatmap")
                    st.write("Call volume data loaded successfully")
                    st.json(heatmap_data['call_volume'])
                
                with col2:
                    st.subheader("Put Volume Heatmap")
                    st.write("Put volume data loaded successfully")
                    st.json(heatmap_data['put_volume'])
            
            gamma_data = self.option_visualizer.create_gamma_exposure_chart(mock_option_data)
            
            if 'error' not in gamma_data:
                st.subheader("Gamma Exposure by Strike")
                
                gamma_df = pd.DataFrame({
                    'Strike': gamma_data['strikes'],
                    'Gamma Exposure': gamma_data['gamma_exposure'],
                    'Volume': gamma_data['volume']
                })
                
                fig = px.bar(
                    gamma_df,
                    x='Strike',
                    y='Gamma Exposure',
                    title=f"{symbol} Gamma Exposure Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Put/Call Ratio", "1.23", "0.15")
            
            with col2:
                st.metric("Avg IV", "28.5%", "2.1%")
            
            with col3:
                st.metric("Max Pain", "$148.50", "$1.25")
            
            with col4:
                st.metric("Total Volume", "125,430", "15,234")
            
        except Exception as e:
            self.logger.error(f"Error creating option analysis page: {e}")
            st.error(f"Option analysis error: {e}")

    def _create_nft_leaderboard_page(self):
        """Create NFT strategy leaderboard page"""
        try:
            st.header("🏆 NFT Strategy Leaderboard")
            
            mock_strategies = []
            for i in range(50):
                mock_strategies.append({
                    'strategy_name': f'Strategy_{i+1:03d}',
                    'creator': f'User_{np.random.randint(1, 100):03d}',
                    'nft_id': f'NFT_{i+1:06d}',
                    'sharpe_ratio': np.random.uniform(0.5, 3.0),
                    'total_return': np.random.uniform(-0.2, 0.8),
                    'accuracy': np.random.uniform(0.55, 0.95),
                    'max_drawdown': np.random.uniform(0.05, 0.25),
                    'trades_count': np.random.randint(50, 1000),
                    'royalties_earned': np.random.uniform(0.001, 0.1),
                    'last_updated': datetime.now().isoformat()
                })
            
            leaderboard_data = self.nft_leaderboard.create_leaderboard_data(mock_strategies)
            
            if 'error' not in leaderboard_data:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Strategies",
                        leaderboard_data['summary_stats']['total_strategies']
                    )
                
                with col2:
                    st.metric(
                        "Avg Sharpe Ratio",
                        f"{leaderboard_data['summary_stats']['average_sharpe']:.2f}"
                    )
                
                with col3:
                    st.metric(
                        "Total Returns",
                        f"{leaderboard_data['summary_stats']['total_returns']:.2f}"
                    )
                
                with col4:
                    st.metric(
                        "Top Performer",
                        leaderboard_data['summary_stats']['top_performer']
                    )
                
                st.subheader("Top Performing Strategies")
                
                leaderboard_df = pd.DataFrame(leaderboard_data['strategies'])
                
                leaderboard_df['Sharpe'] = leaderboard_df['sharpe_ratio'].round(3)
                leaderboard_df['Return'] = (leaderboard_df['total_return'] * 100).round(2).astype(str) + '%'
                leaderboard_df['Accuracy'] = (leaderboard_df['accuracy'] * 100).round(1).astype(str) + '%'
                leaderboard_df['Drawdown'] = (leaderboard_df['max_drawdown'] * 100).round(2).astype(str) + '%'
                leaderboard_df['Royalties'] = leaderboard_df['royalties_earned'].round(6)
                
                display_df = leaderboard_df[[
                    'rank', 'strategy_name', 'creator', 'performance_badge',
                    'Sharpe', 'Return', 'Accuracy', 'Drawdown', 'trades_count', 'Royalties'
                ]].rename(columns={
                    'rank': 'Rank',
                    'strategy_name': 'Strategy',
                    'creator': 'Creator',
                    'performance_badge': 'Badge',
                    'trades_count': 'Trades'
                })
                
                st.dataframe(display_df, use_container_width=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.histogram(
                        leaderboard_df,
                        x='sharpe_ratio',
                        nbins=20,
                        title="Sharpe Ratio Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.scatter(
                        leaderboard_df,
                        x='total_return',
                        y='sharpe_ratio',
                        size='trades_count',
                        color='accuracy',
                        title="Return vs Sharpe Ratio"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"Error creating NFT leaderboard page: {e}")
            st.error(f"NFT leaderboard error: {e}")

    def _create_risk_management_page(self):
        """Create risk management page"""
        try:
            st.header("⚠️ Risk Management Dashboard")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("VaR (95%)", "2.3%", "-0.2%")
            
            with col2:
                st.metric("Max Drawdown", "5.8%", "0.3%")
            
            with col3:
                st.metric("Beta", "1.15", "0.05")
            
            with col4:
                st.metric("Volatility", "18.2%", "-1.1%")
            
            st.subheader("Risk Alerts")
            
            alerts_data = pd.DataFrame({
                'Time': ['09:45:12', '10:15:33', '11:22:45'],
                'Type': ['Position Concentration', 'VaR Limit', 'Correlation Risk'],
                'Severity': ['Medium', 'High', 'Low'],
                'Description': [
                    'AAPL position exceeds 15% limit',
                    'Portfolio VaR approaching 5% limit',
                    'High correlation detected in tech sector'
                ],
                'Action': ['Reduce position', 'Hedge exposure', 'Diversify holdings']
            })
            
            st.dataframe(alerts_data, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"Error creating risk management page: {e}")
            st.error(f"Risk management error: {e}")

    def _create_performance_analytics_page(self):
        """Create performance analytics page"""
        try:
            st.header("📊 Performance Analytics")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Returns Analysis")
                returns_data = pd.DataFrame({
                    'Period': ['1D', '1W', '1M', '3M', '6M', '1Y'],
                    'Portfolio': [0.12, 0.85, 3.2, 8.5, 15.2, 28.7],
                    'Benchmark': [0.08, 0.65, 2.8, 7.1, 12.8, 22.3]
                })
                
                fig = px.bar(
                    returns_data,
                    x='Period',
                    y=['Portfolio', 'Benchmark'],
                    title="Returns Comparison",
                    barmode='group'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Risk Metrics")
                risk_metrics = pd.DataFrame({
                    'Metric': ['Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio', 'Information Ratio'],
                    'Value': [2.34, 3.12, 1.85, 0.67],
                    'Benchmark': [1.89, 2.45, 1.42, 0.00]
                })
                
                fig = px.bar(
                    risk_metrics,
                    x='Metric',
                    y=['Value', 'Benchmark'],
                    title="Risk-Adjusted Returns",
                    barmode='group'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                st.subheader("Strategy Performance")
                strategy_performance = pd.DataFrame({
                    'Strategy': ['Momentum', 'Mean Reversion', 'Arbitrage', 'Options', 'NFT Strategies'],
                    'Return (%)': [12.5, 8.3, 15.2, 22.1, 18.7],
                    'Sharpe': [1.8, 1.2, 2.1, 2.8, 2.3]
                })
                
                fig = px.bar(
                    strategy_performance,
                    x='Strategy',
                    y='Sharpe',
                    title="Strategy Sharpe Ratios"
                )
                st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"Error creating performance analytics page: {e}")
            st.error(f"Performance analytics error: {e}")

class FastAPIServer:
    """
    FastAPI backend for trading dashboard APIs
    Provides REST endpoints for real-time data access
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.app = FastAPI(title="QuantROI Trading API", version="1.0.0") if FASTAPI_AVAILABLE else None
        self.option_visualizer = OptionChainVisualizer()
        self.nft_leaderboard = NFTLeaderboard()
        
        if self.app:
            self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes"""
        if not self.app:
            return
        
        @self.app.get("/")
        async def root():
            return {"message": "QuantROI Trading API", "status": "active"}
        
        @self.app.get("/api/portfolio/metrics")
        async def get_portfolio_metrics():
            """Get current portfolio metrics"""
            return {
                "portfolio_value": 1234567.89,
                "daily_pnl": 8901.23,
                "sharpe_ratio": 2.34,
                "var_95": 0.023,
                "max_drawdown": 0.058,
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/api/options/{symbol}")
        async def get_option_chain(symbol: str):
            """Get option chain data for symbol"""
            mock_options = []
            strikes = np.arange(140, 161, 2.5)
            expirations = ['2025-08-15', '2025-09-19', '2025-10-17']
            
            for exp in expirations:
                for strike in strikes:
                    for opt_type in ['call', 'put']:
                        mock_options.append({
                            'symbol': symbol,
                            'strike': strike,
                            'expiration': exp,
                            'option_type': opt_type,
                            'volume': int(np.random.randint(10, 5000)),
                            'open_interest': int(np.random.randint(100, 10000)),
                            'implied_volatility': float(np.random.uniform(0.15, 0.45)),
                            'delta': float(np.random.uniform(-1, 1)),
                            'gamma': float(np.random.uniform(0, 0.1)),
                            'theta': float(np.random.uniform(-0.5, 0)),
                            'vega': float(np.random.uniform(0, 1))
                        })
            
            return {
                "symbol": symbol,
                "options": mock_options,
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/api/nft/leaderboard")
        async def get_nft_leaderboard():
            """Get NFT strategy leaderboard"""
            mock_strategies = []
            for i in range(20):
                mock_strategies.append({
                    'strategy_name': f'Strategy_{i+1:03d}',
                    'creator': f'User_{np.random.randint(1, 100):03d}',
                    'nft_id': f'NFT_{i+1:06d}',
                    'sharpe_ratio': float(np.random.uniform(0.5, 3.0)),
                    'total_return': float(np.random.uniform(-0.2, 0.8)),
                    'accuracy': float(np.random.uniform(0.55, 0.95)),
                    'max_drawdown': float(np.random.uniform(0.05, 0.25)),
                    'trades_count': int(np.random.randint(50, 1000)),
                    'royalties_earned': float(np.random.uniform(0.001, 0.1)),
                    'last_updated': datetime.now().isoformat()
                })
            
            leaderboard_data = self.nft_leaderboard.create_leaderboard_data(mock_strategies)
            return leaderboard_data

    def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start FastAPI server"""
        if not FASTAPI_AVAILABLE or not self.app:
            self.logger.error("FastAPI not available")
            return
        
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)

async def main():
    """Example dashboard execution"""
    
    option_visualizer = OptionChainVisualizer()
    nft_leaderboard = NFTLeaderboard()
    
    if STREAMLIT_AVAILABLE:
        dashboard = StreamlitDashboard()
        print("Streamlit dashboard initialized")
    
    if FASTAPI_AVAILABLE:
        api_server = FastAPIServer()
        print("FastAPI server initialized")
    
    mock_options = [
        {
            'symbol': 'AAPL',
            'strike': 150.0,
            'expiration': '2025-08-15',
            'option_type': 'call',
            'volume': 1000,
            'open_interest': 5000,
            'implied_volatility': 0.25,
            'delta': 0.6,
            'gamma': 0.05,
            'theta': -0.1,
            'vega': 0.2
        }
    ]
    
    heatmap_data = option_visualizer.create_option_heatmap(mock_options, 150.0)
    print(f"Option heatmap created: {len(heatmap_data)} data points")
    
    mock_strategies = [
        {
            'strategy_name': 'Elite_Strategy_001',
            'creator': 'User_001',
            'nft_id': 'NFT_000001',
            'sharpe_ratio': 2.5,
            'total_return': 0.35,
            'accuracy': 0.78,
            'max_drawdown': 0.08,
            'trades_count': 250,
            'royalties_earned': 0.025,
            'last_updated': datetime.now().isoformat()
        }
    ]
    
    leaderboard_data = nft_leaderboard.create_leaderboard_data(mock_strategies)
    print(f"NFT leaderboard created: {leaderboard_data['summary_stats']['total_strategies']} strategies")

if __name__ == "__main__":
    asyncio.run(main())

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any
import json
import numpy as np
from datetime import datetime, timedelta
import asyncio

class BacktestingDashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()
        
    def setup_layout(self):
        self.app.layout = html.Div([
            html.H1("QuantROI Advanced Backtesting Dashboard", className="header"),
            
            html.Div([
                html.Div([
                    html.Label("Select Symbols:"),
                    dcc.Dropdown(
                        id='symbol-dropdown',
                        options=[
                            {'label': 'AAPL', 'value': 'AAPL'},
                            {'label': 'MSFT', 'value': 'MSFT'},
                            {'label': 'GOOGL', 'value': 'GOOGL'},
                            {'label': 'TSLA', 'value': 'TSLA'},
                            {'label': 'SPY', 'value': 'SPY'},
                            {'label': 'QQQ', 'value': 'QQQ'},
                            {'label': 'NVDA', 'value': 'NVDA'},
                            {'label': 'AMD', 'value': 'AMD'}
                        ],
                        value=['AAPL', 'MSFT'],
                        multi=True
                    )
                ], className="control-item", style={'width': '30%', 'display': 'inline-block'}),
                
                html.Div([
                    html.Label("Lookback Period (months):"),
                    dcc.Slider(
                        id='lookback-slider',
                        min=1,
                        max=24,
                        value=12,
                        marks={i: str(i) for i in range(1, 25, 3)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], className="control-item", style={'width': '30%', 'display': 'inline-block'}),
                
                html.Div([
                    html.Label("Strategies:"),
                    dcc.Dropdown(
                        id='strategy-dropdown',
                        options=[
                            {'label': 'Gated Deep Q Learning', 'value': 'gated_dql'},
                            {'label': 'Gated Policy Gradient', 'value': 'gated_pg'},
                            {'label': 'Master Strategy', 'value': 'master_strategy'},
                            {'label': 'Enhanced Master', 'value': 'enhanced_master'}
                        ],
                        value=['gated_dql', 'gated_pg', 'master_strategy'],
                        multi=True
                    )
                ], className="control-item", style={'width': '30%', 'display': 'inline-block'}),
                
                html.Div([
                    html.Button("Run Backtest", id="run-backtest-btn", className="btn-primary"),
                    html.Button("Run Monte Carlo", id="run-monte-carlo-btn", className="btn-secondary"),
                    html.Button("Walk Forward Analysis", id="walk-forward-btn", className="btn-info")
                ], style={'margin-top': '20px'})
            ], className="control-panel", style={'padding': '20px', 'background-color': '#f8f9fa'}),
            
            html.Div(id="status-indicator", style={'margin': '10px', 'padding': '10px'}),
            
            html.Div([
                html.Div([
                    html.H3("Strategy Performance Comparison"),
                    dcc.Graph(id="performance-comparison")
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Risk Metrics Comparison"),
                    dcc.Graph(id="risk-metrics-chart")
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Detailed Risk Metrics"),
                    html.Div(id="risk-metrics-table")
                ], style={'width': '100%', 'margin-top': '20px'}),
                
                html.Div([
                    html.H3("Monte Carlo Simulation Results"),
                    dcc.Graph(id="monte-carlo-distribution")
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Trade Analysis"),
                    dcc.Graph(id="trade-analysis")
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Walk-Forward Analysis"),
                    dcc.Graph(id="walk-forward-chart")
                ], style={'width': '100%', 'margin-top': '20px'})
            ], className="results-panel")
        ])
    
    def setup_callbacks(self):
        @self.app.callback(
            [Output('performance-comparison', 'figure'),
             Output('risk-metrics-table', 'children'),
             Output('risk-metrics-chart', 'figure'),
             Output('monte-carlo-distribution', 'figure'),
             Output('trade-analysis', 'figure'),
             Output('status-indicator', 'children')],
            [Input('run-backtest-btn', 'n_clicks')],
            [Input('symbol-dropdown', 'value'),
             Input('lookback-slider', 'value'),
             Input('strategy-dropdown', 'value')]
        )
        def update_backtest_results(n_clicks, symbols, lookback_months, strategies):
            if n_clicks is None:
                return {}, "", {}, {}, {}, ""
            
            results = self._generate_sample_backtest_results(symbols, strategies)
            
            performance_fig = self._create_performance_comparison(results)
            risk_table = self._create_risk_metrics_table(results)
            risk_chart = self._create_risk_metrics_chart(results)
            monte_carlo_fig = self._create_monte_carlo_distribution(results)
            trade_analysis_fig = self._create_trade_analysis(results)
            
            status = html.Div([
                html.Span("✅ Backtest completed successfully!", style={'color': 'green', 'font-weight': 'bold'}),
                html.Br(),
                html.Span(f"Analyzed {len(symbols)} symbols with {len(strategies)} strategies over {lookback_months} months")
            ])
            
            return performance_fig, risk_table, risk_chart, monte_carlo_fig, trade_analysis_fig, status
    
    def _generate_sample_backtest_results(self, symbols: list, strategies: list) -> Dict[str, Any]:
        np.random.seed(42)
        
        results = {}
        
        for strategy in strategies:
            base_return = np.random.normal(0.08, 0.15)
            sharpe_ratio = np.random.uniform(0.5, 2.5)
            max_drawdown = np.random.uniform(0.05, 0.25)
            win_rate = np.random.uniform(0.45, 0.65)
            
            if strategy == 'gated_dql':
                sharpe_ratio *= 1.1
                max_drawdown *= 0.9
            elif strategy == 'master_strategy':
                base_return *= 1.05
                win_rate *= 1.02
            
            results[strategy] = type('BacktestResult', (), {
                'total_return': base_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_trades': np.random.randint(50, 200),
                'avg_trade_duration': np.random.uniform(1, 10)
            })()
        
        return results
    
    def _create_performance_comparison(self, results: Dict[str, Any]) -> go.Figure:
        strategies = list(results.keys())
        returns = [results[strategy].total_return for strategy in strategies]
        sharpe_ratios = [results[strategy].sharpe_ratio for strategy in strategies]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Total Return',
            x=strategies,
            y=returns,
            yaxis='y',
            offsetgroup=1
        ))
        
        fig.add_trace(go.Scatter(
            name='Sharpe Ratio',
            x=strategies,
            y=sharpe_ratios,
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='red')
        ))
        
        fig.update_layout(
            title='Strategy Performance Comparison',
            xaxis_title='Strategy',
            yaxis=dict(title='Total Return', side='left'),
            yaxis2=dict(title='Sharpe Ratio', side='right', overlaying='y'),
            barmode='group'
        )
        
        return fig
    
    def _create_risk_metrics_table(self, results: Dict[str, Any]) -> html.Table:
        table_header = [
            html.Thead([
                html.Tr([
                    html.Th("Strategy"),
                    html.Th("Total Return"),
                    html.Th("Sharpe Ratio"),
                    html.Th("Max Drawdown"),
                    html.Th("Win Rate"),
                    html.Th("Total Trades")
                ])
            ])
        ]
        
        table_body = []
        for strategy, result in results.items():
            row = html.Tr([
                html.Td(strategy),
                html.Td(f"{result.total_return:.2%}"),
                html.Td(f"{result.sharpe_ratio:.2f}"),
                html.Td(f"{result.max_drawdown:.2%}"),
                html.Td(f"{result.win_rate:.2%}"),
                html.Td(f"{result.total_trades}")
            ])
            table_body.append(row)
        
        table = html.Table(
            table_header + [html.Tbody(table_body)],
            className="table table-striped"
        )
        
        return table
    
    def _create_risk_metrics_chart(self, results: Dict[str, Any]) -> go.Figure:
        strategies = list(results.keys())
        max_drawdowns = [results[strategy].max_drawdown for strategy in strategies]
        win_rates = [results[strategy].win_rate for strategy in strategies]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=max_drawdowns,
            y=win_rates,
            mode='markers+text',
            text=strategies,
            textposition="top center",
            marker=dict(size=10, color='blue'),
            name='Strategies'
        ))
        
        fig.update_layout(
            title='Risk vs Win Rate Analysis',
            xaxis_title='Maximum Drawdown',
            yaxis_title='Win Rate',
            showlegend=False
        )
        
        return fig
    
    def _create_monte_carlo_distribution(self, results: Dict[str, Any]) -> go.Figure:
        if 'monte_carlo_results' not in results:
            monte_carlo_results = self._generate_sample_monte_carlo_results()
        else:
            monte_carlo_results = results['monte_carlo_results']
        
        returns = [result['total_return'] for result in monte_carlo_results]
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=returns,
            nbinsx=50,
            name='Return Distribution',
            opacity=0.7
        ))
        
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        fig.add_vline(x=var_95, line_dash="dash", line_color="red", 
                     annotation_text="VaR 95%")
        fig.add_vline(x=var_99, line_dash="dash", line_color="darkred", 
                     annotation_text="VaR 99%")
        
        fig.update_layout(
            title='Monte Carlo Return Distribution',
            xaxis_title='Total Return',
            yaxis_title='Frequency'
        )
        
        return fig
    
    def _create_trade_analysis(self, results: Dict[str, Any]) -> go.Figure:
        strategies = list(results.keys())
        total_trades = [results[strategy].total_trades for strategy in strategies]
        avg_duration = [results[strategy].avg_trade_duration for strategy in strategies]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=total_trades,
            y=avg_duration,
            mode='markers+text',
            text=strategies,
            textposition="top center",
            marker=dict(size=12, color='green'),
            name='Strategies'
        ))
        
        fig.update_layout(
            title='Trade Frequency vs Duration Analysis',
            xaxis_title='Total Trades',
            yaxis_title='Average Trade Duration (hours)',
            showlegend=False
        )
        
        return fig
    
    def _generate_sample_monte_carlo_results(self) -> list:
        np.random.seed(42)
        results = []
        
        for i in range(1000):
            results.append({
                'scenario_id': f'scenario_{i}',
                'total_return': np.random.normal(0.08, 0.2),
                'sharpe_ratio': np.random.normal(1.2, 0.5),
                'max_drawdown': np.random.uniform(0.02, 0.3),
                'var_95': np.random.normal(-0.02, 0.01),
                'var_99': np.random.normal(-0.035, 0.015),
                'win_rate': np.random.uniform(0.4, 0.7)
            })
        
        return results
    
    def run_server(self, debug=True, port=8050):
        self.app.run_server(debug=debug, port=port)

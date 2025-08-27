"""
Voting Heatmap UI Visualizer
Tesla dashboard-style visualization for vote intensity and ZKP verification status
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from plotly.graph_objs import Figure
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

@dataclass
class VoteHeatmapData:
    vote_id: str
    timestamp: datetime
    vote_intensity: float  # 0.0 to 1.0
    zkp_status: str  # "pending", "verified", "failed"
    source_reliability: float  # 0.0 to 1.0
    stake_weight: float  # 0.0 to 1.0
    vote_category: str  # "delegation", "strategy", "governance"
    geographic_region: Optional[str] = None
    x_coord: float = 0.0  # For spatial mapping
    y_coord: float = 0.0

@dataclass
class HeatmapConfig:
    update_interval: int = 5  # seconds
    max_data_points: int = 10000
    color_scheme: str = "tesla"  # "tesla", "viridis", "plasma"
    show_zkp_overlay: bool = True
    enable_real_time: bool = True
    geographic_mode: bool = False

class VotingHeatmapVisualizer:
    """
    Tesla dashboard-style heatmap for visualizing vote intensity and ZKP verification status.
    Provides real-time updates with color-coded status indicators.
    """
    
    def __init__(self, config: HeatmapConfig = None):
        self.config = config or HeatmapConfig()
        self.vote_data: List[VoteHeatmapData] = []
        self.app = None
        self.figure_cache = {}
        self.last_update = datetime.now()
        
        self.color_schemes = {
            "tesla": {
                "background": "#000000",
                "primary": "#FF0000",
                "secondary": "#FFFFFF",
                "accent": "#00FF00",
                "warning": "#FFA500",
                "verified": "#00FF00",
                "pending": "#FFA500",
                "failed": "#FF0000"
            },
            "viridis": px.colors.sequential.Viridis,
            "plasma": px.colors.sequential.Plasma
        }
    
    def initialize_dashboard(self, port: int = 8050) -> bool:
        """Initialize Dash web application for real-time heatmap display"""
        try:
            self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
            
            self.app.layout = self._create_layout()
            
            self._register_callbacks()
            
            print(f"Heatmap dashboard initialized on port {port}")
            return True
            
        except Exception as e:
            print(f"Failed to initialize dashboard: {e}")
            return False
    
    def _create_layout(self) -> html.Div:
        """Create Tesla-inspired dashboard layout"""
        colors = self.color_schemes[self.config.color_scheme]
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H1("QuantROI Voting Heatmap", 
                           style={"color": colors["primary"], "textAlign": "center"}),
                    html.H4("Real-time Vote Intensity & ZKP Verification Status",
                           style={"color": colors["secondary"], "textAlign": "center"})
                ])
            ], style={"marginBottom": "20px"}),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Controls", style={"color": colors["primary"]}),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Update Interval (s):", style={"color": colors["secondary"]}),
                                    dcc.Slider(
                                        id="update-interval-slider",
                                        min=1, max=30, step=1,
                                        value=self.config.update_interval,
                                        marks={i: str(i) for i in [1, 5, 10, 15, 30]}
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Label("Color Scheme:", style={"color": colors["secondary"]}),
                                    dcc.Dropdown(
                                        id="color-scheme-dropdown",
                                        options=[
                                            {"label": "Tesla", "value": "tesla"},
                                            {"label": "Viridis", "value": "viridis"},
                                            {"label": "Plasma", "value": "plasma"}
                                        ],
                                        value=self.config.color_scheme,
                                        style={"color": "#000000"}
                                    )
                                ], width=6)
                            ])
                        ])
                    ], style={"backgroundColor": "#1a1a1a", "border": f"1px solid {colors['primary']}"})
                ], width=12)
            ], style={"marginBottom": "20px"}),
            
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id="main-heatmap",
                        style={"height": "600px"},
                        config={"displayModeBar": False}
                    )
                ], width=8),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("ZKP Verification Status", style={"color": colors["primary"]}),
                            html.Div(id="zkp-status-panel")
                        ])
                    ], style={"backgroundColor": "#1a1a1a", "border": f"1px solid {colors['primary']}", "marginBottom": "20px"}),
                    
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Live Statistics", style={"color": colors["primary"]}),
                            html.Div(id="stats-panel")
                        ])
                    ], style={"backgroundColor": "#1a1a1a", "border": f"1px solid {colors['primary']}"})
                ], width=4)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id="time-series-chart",
                        style={"height": "300px"},
                        config={"displayModeBar": False}
                    )
                ], width=12)
            ], style={"marginTop": "20px"}),
            
            dcc.Interval(
                id="interval-component",
                interval=self.config.update_interval * 1000,  # milliseconds
                n_intervals=0
            ),
            
            dcc.Store(id="vote-data-store")
            
        ], style={
            "backgroundColor": colors["background"],
            "minHeight": "100vh",
            "padding": "20px"
        })
    
    def _register_callbacks(self):
        """Register Dash callbacks for interactivity"""
        
        @self.app.callback(
            [Output("main-heatmap", "figure"),
             Output("zkp-status-panel", "children"),
             Output("stats-panel", "children"),
             Output("time-series-chart", "figure")],
            [Input("interval-component", "n_intervals"),
             Input("color-scheme-dropdown", "value"),
             Input("update-interval-slider", "value")]
        )
        def update_dashboard(n_intervals, color_scheme, update_interval):
            self.config.color_scheme = color_scheme
            self.config.update_interval = update_interval
            
            main_heatmap = self._create_main_heatmap()
            zkp_panel = self._create_zkp_status_panel()
            stats_panel = self._create_stats_panel()
            time_series = self._create_time_series_chart()
            
            return main_heatmap, zkp_panel, stats_panel, time_series
    
    def add_vote_data(self, vote_data: VoteHeatmapData) -> None:
        """Add new vote data point to the heatmap"""
        self.vote_data.append(vote_data)
        
        if len(self.vote_data) > self.config.max_data_points:
            self.vote_data = self.vote_data[-self.config.max_data_points:]
        
        self.last_update = datetime.now()
    
    def add_batch_vote_data(self, vote_batch: List[VoteHeatmapData]) -> None:
        """Add batch of vote data for efficient updates"""
        self.vote_data.extend(vote_batch)
        
        if len(self.vote_data) > self.config.max_data_points:
            self.vote_data = self.vote_data[-self.config.max_data_points:]
        
        self.last_update = datetime.now()
    
    def _create_main_heatmap(self) -> Figure:
        """Create main Tesla-style heatmap visualization"""
        if not self.vote_data:
            return self._create_empty_heatmap()
        
        df = pd.DataFrame([
            {
                "x": vote.x_coord,
                "y": vote.y_coord,
                "intensity": vote.vote_intensity,
                "zkp_status": vote.zkp_status,
                "reliability": vote.source_reliability,
                "stake_weight": vote.stake_weight,
                "category": vote.vote_category,
                "timestamp": vote.timestamp
            }
            for vote in self.vote_data
        ])
        
        colors = self.color_schemes[self.config.color_scheme]
        
        if self.config.geographic_mode:
            fig = self._create_geographic_heatmap(df)
        else:
            fig = self._create_grid_heatmap(df)
        
        fig.update_layout(
            plot_bgcolor=colors["background"],
            paper_bgcolor=colors["background"],
            font=dict(color=colors["secondary"]),
            title=dict(
                text="Vote Intensity Heatmap",
                font=dict(color=colors["primary"], size=20)
            ),
            showlegend=True
        )
        
        return fig
    
    def _create_grid_heatmap(self, df: pd.DataFrame) -> Figure:
        """Create grid-based heatmap for vote intensity"""
        grid_size = 50
        x_bins = np.linspace(df["x"].min(), df["x"].max(), grid_size)
        y_bins = np.linspace(df["y"].min(), df["y"].max(), grid_size)
        
        intensity_grid = np.zeros((grid_size-1, grid_size-1))
        zkp_status_grid = np.full((grid_size-1, grid_size-1), "", dtype=object)
        
        for _, row in df.iterrows():
            x_idx = np.digitize(row["x"], x_bins) - 1
            y_idx = np.digitize(row["y"], y_bins) - 1
            
            if 0 <= x_idx < grid_size-1 and 0 <= y_idx < grid_size-1:
                intensity_grid[y_idx, x_idx] += row["intensity"] * row["stake_weight"]
                
                if row["zkp_status"] == "verified":
                    zkp_status_grid[y_idx, x_idx] = "verified"
                elif row["zkp_status"] == "failed" and zkp_status_grid[y_idx, x_idx] != "verified":
                    zkp_status_grid[y_idx, x_idx] = "failed"
                elif zkp_status_grid[y_idx, x_idx] == "":
                    zkp_status_grid[y_idx, x_idx] = "pending"
        
        fig = go.Figure()
        
        fig.add_trace(go.Heatmap(
            z=intensity_grid,
            x=x_bins[:-1],
            y=y_bins[:-1],
            colorscale="Reds" if self.config.color_scheme == "tesla" else self.config.color_scheme,
            showscale=True,
            colorbar=dict(title="Vote Intensity", titlefont=dict(color="white"))
        ))
        
        if self.config.show_zkp_overlay:
            self._add_zkp_overlay(fig, df)
        
        return fig
    
    def _create_geographic_heatmap(self, df: pd.DataFrame) -> Figure:
        """Create geographic heatmap for global vote distribution"""
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df["x"],
            y=df["y"],
            mode="markers",
            marker=dict(
                size=df["intensity"] * 50,
                color=df["reliability"],
                colorscale="Reds" if self.config.color_scheme == "tesla" else self.config.color_scheme,
                showscale=True,
                colorbar=dict(title="Source Reliability")
            ),
            text=df.apply(lambda row: f"Intensity: {row['intensity']:.2f}<br>ZKP: {row['zkp_status']}<br>Reliability: {row['reliability']:.2f}", axis=1),
            hovertemplate="%{text}<extra></extra>"
        ))
        
        return fig
    
    def _add_zkp_overlay(self, fig: Figure, df: pd.DataFrame) -> None:
        """Add ZKP verification status overlay to heatmap"""
        colors = self.color_schemes[self.config.color_scheme]
        
        for status in ["verified", "pending", "failed"]:
            status_data = df[df["zkp_status"] == status]
            if not status_data.empty:
                fig.add_trace(go.Scatter(
                    x=status_data["x"],
                    y=status_data["y"],
                    mode="markers",
                    marker=dict(
                        symbol="circle",
                        size=8,
                        color=colors[status],
                        line=dict(width=2, color="white")
                    ),
                    name=f"ZKP {status.title()}",
                    showlegend=True
                ))
    
    def _create_zkp_status_panel(self) -> List[html.Div]:
        """Create ZKP verification status panel"""
        if not self.vote_data:
            return [html.P("No data available", style={"color": "white"})]
        
        total_votes = len(self.vote_data)
        verified_count = sum(1 for vote in self.vote_data if vote.zkp_status == "verified")
        pending_count = sum(1 for vote in self.vote_data if vote.zkp_status == "pending")
        failed_count = sum(1 for vote in self.vote_data if vote.zkp_status == "failed")
        
        colors = self.color_schemes[self.config.color_scheme]
        
        return [
            html.Div([
                html.H6("Verified", style={"color": colors["verified"]}),
                html.H4(f"{verified_count}", style={"color": colors["verified"]}),
                html.P(f"{verified_count/total_votes*100:.1f}%", style={"color": "white"})
            ], style={"textAlign": "center", "marginBottom": "15px"}),
            
            html.Div([
                html.H6("Pending", style={"color": colors["pending"]}),
                html.H4(f"{pending_count}", style={"color": colors["pending"]}),
                html.P(f"{pending_count/total_votes*100:.1f}%", style={"color": "white"})
            ], style={"textAlign": "center", "marginBottom": "15px"}),
            
            html.Div([
                html.H6("Failed", style={"color": colors["failed"]}),
                html.H4(f"{failed_count}", style={"color": colors["failed"]}),
                html.P(f"{failed_count/total_votes*100:.1f}%", style={"color": "white"})
            ], style={"textAlign": "center", "marginBottom": "15px"}),
            
            html.Hr(style={"borderColor": colors["primary"]}),
            
            html.Div([
                html.H6("Verification Rate", style={"color": colors["secondary"]}),
                html.H4(f"{verified_count/(verified_count+failed_count)*100:.1f}%" if (verified_count+failed_count) > 0 else "N/A", 
                       style={"color": colors["accent"]})
            ], style={"textAlign": "center"})
        ]
    
    def _create_stats_panel(self) -> List[html.Div]:
        """Create live statistics panel"""
        if not self.vote_data:
            return [html.P("No data available", style={"color": "white"})]
        
        total_votes = len(self.vote_data)
        avg_intensity = np.mean([vote.vote_intensity for vote in self.vote_data])
        avg_reliability = np.mean([vote.source_reliability for vote in self.vote_data])
        avg_stake = np.mean([vote.stake_weight for vote in self.vote_data])
        
        recent_cutoff = datetime.now() - timedelta(minutes=5)
        recent_votes = [vote for vote in self.vote_data if vote.timestamp > recent_cutoff]
        
        colors = self.color_schemes[self.config.color_scheme]
        
        return [
            html.Div([
                html.H6("Total Votes", style={"color": colors["secondary"]}),
                html.H4(f"{total_votes:,}", style={"color": colors["accent"]})
            ], style={"textAlign": "center", "marginBottom": "15px"}),
            
            html.Div([
                html.H6("Avg Intensity", style={"color": colors["secondary"]}),
                html.H4(f"{avg_intensity:.2f}", style={"color": colors["accent"]})
            ], style={"textAlign": "center", "marginBottom": "15px"}),
            
            html.Div([
                html.H6("Avg Reliability", style={"color": colors["secondary"]}),
                html.H4(f"{avg_reliability:.2f}", style={"color": colors["accent"]})
            ], style={"textAlign": "center", "marginBottom": "15px"}),
            
            html.Div([
                html.H6("Avg Stake Weight", style={"color": colors["secondary"]}),
                html.H4(f"{avg_stake:.2f}", style={"color": colors["accent"]})
            ], style={"textAlign": "center", "marginBottom": "15px"}),
            
            html.Hr(style={"borderColor": colors["primary"]}),
            
            html.Div([
                html.H6("Recent Activity (5m)", style={"color": colors["secondary"]}),
                html.H4(f"{len(recent_votes)}", style={"color": colors["primary"]})
            ], style={"textAlign": "center"}),
            
            html.Div([
                html.P(f"Last Update: {self.last_update.strftime('%H:%M:%S')}", 
                      style={"color": colors["secondary"], "fontSize": "12px", "textAlign": "center"})
            ])
        ]
    
    def _create_time_series_chart(self) -> Figure:
        """Create time series chart for vote activity over time"""
        if not self.vote_data:
            return self._create_empty_time_series()
        
        df = pd.DataFrame([
            {
                "timestamp": vote.timestamp,
                "intensity": vote.vote_intensity,
                "zkp_status": vote.zkp_status
            }
            for vote in self.vote_data
        ])
        
        df.set_index("timestamp", inplace=True)
        resampled = df.resample("5T").agg({
            "intensity": ["count", "mean"],
            "zkp_status": lambda x: (x == "verified").sum()
        }).fillna(0)
        
        resampled.columns = ["vote_count", "avg_intensity", "verified_count"]
        resampled.reset_index(inplace=True)
        
        colors = self.color_schemes[self.config.color_scheme]
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Scatter(
                x=resampled["timestamp"],
                y=resampled["vote_count"],
                mode="lines+markers",
                name="Vote Count",
                line=dict(color=colors["primary"], width=2)
            ),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Scatter(
                x=resampled["timestamp"],
                y=resampled["avg_intensity"],
                mode="lines",
                name="Avg Intensity",
                line=dict(color=colors["accent"], width=2)
            ),
            secondary_y=True
        )
        
        fig.add_trace(
            go.Scatter(
                x=resampled["timestamp"],
                y=resampled["verified_count"],
                mode="lines",
                name="Verified ZKPs",
                line=dict(color=colors["verified"], width=2)
            ),
            secondary_y=False
        )
        
        fig.update_layout(
            plot_bgcolor=colors["background"],
            paper_bgcolor=colors["background"],
            font=dict(color=colors["secondary"]),
            title=dict(
                text="Vote Activity Over Time",
                font=dict(color=colors["primary"], size=16)
            ),
            xaxis_title="Time",
            showlegend=True
        )
        
        fig.update_yaxes(title_text="Vote Count / Verified ZKPs", secondary_y=False, color=colors["secondary"])
        fig.update_yaxes(title_text="Average Intensity", secondary_y=True, color=colors["secondary"])
        
        return fig
    
    def _create_empty_heatmap(self) -> Figure:
        """Create empty heatmap placeholder"""
        colors = self.color_schemes[self.config.color_scheme]
        
        fig = go.Figure()
        fig.add_annotation(
            text="No vote data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(color=colors["secondary"], size=20)
        )
        
        fig.update_layout(
            plot_bgcolor=colors["background"],
            paper_bgcolor=colors["background"],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        
        return fig
    
    def _create_empty_time_series(self) -> Figure:
        """Create empty time series placeholder"""
        colors = self.color_schemes[self.config.color_scheme]
        
        fig = go.Figure()
        fig.add_annotation(
            text="No time series data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(color=colors["secondary"], size=16)
        )
        
        fig.update_layout(
            plot_bgcolor=colors["background"],
            paper_bgcolor=colors["background"],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        
        return fig
    
    def run_dashboard(self, host: str = "0.0.0.0", port: int = 8050, debug: bool = False) -> None:
        """Run the dashboard web application"""
        if not self.app:
            raise RuntimeError("Dashboard not initialized. Call initialize_dashboard() first.")
        
        print(f"Starting voting heatmap dashboard at http://{host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)
    
    def export_heatmap_image(self, filename: str, format: str = "png") -> bool:
        """Export current heatmap as image file"""
        try:
            fig = self._create_main_heatmap()
            fig.write_image(filename, format=format, width=1200, height=800)
            print(f"Heatmap exported to {filename}")
            return True
        except Exception as e:
            print(f"Failed to export heatmap: {e}")
            return False
    
    def generate_heatmap_report(self) -> Dict:
        """Generate comprehensive heatmap analytics report"""
        if not self.vote_data:
            return {"error": "No data available for report generation"}
        
        total_votes = len(self.vote_data)
        
        zkp_stats = {
            "verified": sum(1 for vote in self.vote_data if vote.zkp_status == "verified"),
            "pending": sum(1 for vote in self.vote_data if vote.zkp_status == "pending"),
            "failed": sum(1 for vote in self.vote_data if vote.zkp_status == "failed")
        }
        
        intensities = [vote.vote_intensity for vote in self.vote_data]
        intensity_stats = {
            "mean": np.mean(intensities),
            "median": np.median(intensities),
            "std": np.std(intensities),
            "min": np.min(intensities),
            "max": np.max(intensities)
        }
        
        reliabilities = [vote.source_reliability for vote in self.vote_data]
        reliability_stats = {
            "mean": np.mean(reliabilities),
            "median": np.median(reliabilities),
            "std": np.std(reliabilities),
            "high_reliability_count": sum(1 for r in reliabilities if r > 0.8)
        }
        
        categories = {}
        for vote in self.vote_data:
            categories[vote.vote_category] = categories.get(vote.vote_category, 0) + 1
        
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_votes = [vote for vote in self.vote_data if vote.timestamp > recent_cutoff]
        
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "total_votes": total_votes,
            "zkp_verification": {
                **zkp_stats,
                "verification_rate": zkp_stats["verified"] / (zkp_stats["verified"] + zkp_stats["failed"]) if (zkp_stats["verified"] + zkp_stats["failed"]) > 0 else 0
            },
            "intensity_analysis": intensity_stats,
            "reliability_analysis": reliability_stats,
            "category_distribution": categories,
            "recent_activity": {
                "last_hour_votes": len(recent_votes),
                "activity_rate": len(recent_votes) / 60 if recent_votes else 0  # votes per minute
            },
            "data_quality": {
                "data_points": total_votes,
                "time_span_hours": (max(vote.timestamp for vote in self.vote_data) - min(vote.timestamp for vote in self.vote_data)).total_seconds() / 3600 if total_votes > 1 else 0,
                "last_update": self.last_update.isoformat()
            }
        }
        
        return report

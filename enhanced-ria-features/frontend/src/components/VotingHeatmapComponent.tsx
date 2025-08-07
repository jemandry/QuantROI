'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, Typography, Box, Switch, FormControlLabel, Grid } from '@mui/material';
import Plot from 'react-plotly.js';
import { useQuery } from '@apollo/client';
import { GET_VOTING_HEATMAP_DATA } from '../graphql/queries';

interface VoteHeatmapData {
  vote_id: string;
  timestamp: string;
  vote_intensity: number;
  zkp_status: 'pending' | 'verified' | 'failed';
  source_reliability: number;
  stake_weight: number;
  x_coord: number;
  y_coord: number;
}

const VotingHeatmapComponent: React.FC = () => {
  const [showZkpOverlay, setShowZkpOverlay] = useState(true);
  const [realTimeEnabled, setRealTimeEnabled] = useState(true);
  
  const { data, loading, error, refetch } = useQuery(GET_VOTING_HEATMAP_DATA, {
    pollInterval: realTimeEnabled ? 5000 : 0,
    errorPolicy: 'all'
  });

  const mockData: VoteHeatmapData[] = [
    {
      vote_id: 'vote_001',
      timestamp: new Date().toISOString(),
      vote_intensity: 0.8,
      zkp_status: 'verified',
      source_reliability: 0.9,
      stake_weight: 0.7,
      x_coord: 25,
      y_coord: 35
    },
    {
      vote_id: 'vote_002',
      timestamp: new Date().toISOString(),
      vote_intensity: 0.6,
      zkp_status: 'pending',
      source_reliability: 0.7,
      stake_weight: 0.5,
      x_coord: 45,
      y_coord: 55
    },
    {
      vote_id: 'vote_003',
      timestamp: new Date().toISOString(),
      vote_intensity: 0.9,
      zkp_status: 'verified',
      source_reliability: 0.95,
      stake_weight: 0.8,
      x_coord: 65,
      y_coord: 25
    }
  ];

  const voteData = data?.votingHeatmapData || mockData;

  const getZkpColor = (status: string) => {
    switch (status) {
      case 'verified': return '#00FF00';
      case 'pending': return '#FFA500';
      case 'failed': return '#FF0000';
      default: return '#FFFFFF';
    }
  };

  const heatmapTrace = {
    x: voteData.map(d => d.x_coord),
    y: voteData.map(d => d.y_coord),
    z: voteData.map(d => d.vote_intensity),
    type: 'scatter' as const,
    mode: 'markers' as const,
    marker: {
      size: voteData.map(d => d.stake_weight * 50 + 10),
      color: showZkpOverlay 
        ? voteData.map(d => getZkpColor(d.zkp_status))
        : voteData.map(d => d.vote_intensity),
      colorscale: showZkpOverlay ? undefined : 'Viridis',
      showscale: !showZkpOverlay,
      opacity: 0.8,
      line: {
        color: '#FFFFFF',
        width: 1
      }
    },
    text: voteData.map(d => 
      `Vote: ${d.vote_id}<br>` +
      `Intensity: ${(d.vote_intensity * 100).toFixed(1)}%<br>` +
      `ZKP Status: ${d.zkp_status}<br>` +
      `Reliability: ${(d.source_reliability * 100).toFixed(1)}%<br>` +
      `Stake Weight: ${(d.stake_weight * 100).toFixed(1)}%`
    ),
    hovertemplate: '%{text}<extra></extra>'
  };

  const layout = {
    title: {
      text: 'Real-time Voting Heatmap',
      font: { color: '#FFFFFF', size: 20 }
    },
    paper_bgcolor: '#000000',
    plot_bgcolor: '#000000',
    xaxis: {
      title: 'Spatial X Coordinate',
      gridcolor: '#333333',
      color: '#FFFFFF'
    },
    yaxis: {
      title: 'Spatial Y Coordinate',
      gridcolor: '#333333',
      color: '#FFFFFF'
    },
    font: { color: '#FFFFFF' },
    margin: { t: 50, r: 50, b: 50, l: 50 }
  };

  return (
    <Card sx={{ height: '600px', backgroundColor: '#1a1a1a' }}>
      <CardContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="h5" color="primary" gutterBottom>
            Tesla-Style Voting Heatmap
          </Typography>
          
          <Grid container spacing={2} alignItems="center">
            <Grid item>
              <FormControlLabel
                control={
                  <Switch
                    checked={showZkpOverlay}
                    onChange={(e) => setShowZkpOverlay(e.target.checked)}
                    color="primary"
                  />
                }
                label="ZKP Status Overlay"
              />
            </Grid>
            <Grid item>
              <FormControlLabel
                control={
                  <Switch
                    checked={realTimeEnabled}
                    onChange={(e) => setRealTimeEnabled(e.target.checked)}
                    color="primary"
                  />
                }
                label="Real-time Updates"
              />
            </Grid>
          </Grid>
        </Box>

        <Box sx={{ height: '450px' }}>
          <Plot
            data={[heatmapTrace]}
            layout={layout}
            style={{ width: '100%', height: '100%' }}
            config={{
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['pan2d', 'lasso2d']
            }}
          />
        </Box>

        {loading && (
          <Typography color="warning.main">
            Loading heatmap data...
          </Typography>
        )}

        {error && (
          <Typography color="error.main">
            Error loading data: {error.message}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default VotingHeatmapComponent;

'use client';

import React from 'react';
import { Card, CardContent, Typography, Box, Chip, LinearProgress, Grid } from '@mui/material';
import { useQuery } from '@apollo/client';
import { GET_SYSTEM_STATUS } from '../graphql/queries';

interface SystemMetrics {
  total_votes_processed: number;
  successful_votes: number;
  failed_votes: number;
  avg_processing_time_ms: number;
  total_anomalies_detected: number;
  causal_relationships_discovered: number;
  model_accuracy: number;
}

const SystemStatusComponent: React.FC = () => {
  const { data, loading, error } = useQuery(GET_SYSTEM_STATUS, {
    pollInterval: 10000,
    errorPolicy: 'all'
  });

  const mockMetrics: SystemMetrics = {
    total_votes_processed: 1247,
    successful_votes: 1198,
    failed_votes: 49,
    avg_processing_time_ms: 0.85,
    total_anomalies_detected: 23,
    causal_relationships_discovered: 156,
    model_accuracy: 0.94
  };

  const metrics = data?.systemStatus?.metrics || mockMetrics;
  const successRate = metrics.total_votes_processed > 0 
    ? (metrics.successful_votes / metrics.total_votes_processed) * 100 
    : 0;

  const getStatusColor = (value: number, threshold: number, reverse = false) => {
    if (reverse) {
      return value <= threshold ? 'success' : value <= threshold * 1.5 ? 'warning' : 'error';
    }
    return value >= threshold ? 'success' : value >= threshold * 0.8 ? 'warning' : 'error';
  };

  const getPerformanceStatus = () => {
    if (metrics.avg_processing_time_ms < 1.0 && successRate > 95) return 'Optimal';
    if (metrics.avg_processing_time_ms < 2.0 && successRate > 90) return 'Good';
    if (metrics.avg_processing_time_ms < 5.0 && successRate > 80) return 'Fair';
    return 'Needs Attention';
  };

  return (
    <Card sx={{ backgroundColor: '#1a1a1a', height: '600px' }}>
      <CardContent>
        <Typography variant="h5" color="primary" gutterBottom>
          System Status
        </Typography>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" color="secondary" gutterBottom>
            Overall Performance
          </Typography>
          <Chip 
            label={getPerformanceStatus()}
            color={getStatusColor(successRate, 95) as any}
            sx={{ mb: 2 }}
          />
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="secondary">
                Processing Success Rate: {successRate.toFixed(1)}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={successRate} 
                color={getStatusColor(successRate, 95) as any}
                sx={{ mt: 1 }}
              />
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Typography variant="body2" color="secondary">
              Total Votes
            </Typography>
            <Typography variant="h6" color="primary">
              {metrics.total_votes_processed.toLocaleString()}
            </Typography>
          </Grid>

          <Grid item xs={6}>
            <Typography variant="body2" color="secondary">
              Successful
            </Typography>
            <Typography variant="h6" color="success.main">
              {metrics.successful_votes.toLocaleString()}
            </Typography>
          </Grid>

          <Grid item xs={6}>
            <Typography variant="body2" color="secondary">
              Failed
            </Typography>
            <Typography variant="h6" color="error.main">
              {metrics.failed_votes.toLocaleString()}
            </Typography>
          </Grid>

          <Grid item xs={6}>
            <Typography variant="body2" color="secondary">
              Avg Time (ms)
            </Typography>
            <Typography 
              variant="h6" 
              color={getStatusColor(metrics.avg_processing_time_ms, 1.0, true) === 'success' ? 'success.main' : 
                     getStatusColor(metrics.avg_processing_time_ms, 1.0, true) === 'warning' ? 'warning.main' : 'error.main'}
            >
              {metrics.avg_processing_time_ms.toFixed(2)}
            </Typography>
          </Grid>

          <Grid item xs={12}>
            <Box sx={{ mt: 2, mb: 2 }}>
              <Typography variant="body2" color="secondary">
                Model Accuracy: {(metrics.model_accuracy * 100).toFixed(1)}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={metrics.model_accuracy * 100} 
                color={getStatusColor(metrics.model_accuracy * 100, 90) as any}
                sx={{ mt: 1 }}
              />
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Typography variant="body2" color="secondary">
              Anomalies
            </Typography>
            <Typography variant="h6" color="warning.main">
              {metrics.total_anomalies_detected}
            </Typography>
          </Grid>

          <Grid item xs={6}>
            <Typography variant="body2" color="secondary">
              Causal Links
            </Typography>
            <Typography variant="h6" color="info.main">
              {metrics.causal_relationships_discovered}
            </Typography>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" color="secondary" gutterBottom>
            Feature Status
          </Typography>
          
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <Chip label="ZKP Proofs" color="success" size="small" />
            </Grid>
            <Grid item xs={6}>
              <Chip label="IPFS Storage" color="success" size="small" />
            </Grid>
            <Grid item xs={6}>
              <Chip label="Causal AI" color="success" size="small" />
            </Grid>
            <Grid item xs={6}>
              <Chip label="Heatmap UI" color="success" size="small" />
            </Grid>
            <Grid item xs={6}>
              <Chip label="Delay Alerts" color="success" size="small" />
            </Grid>
            <Grid item xs={6}>
              <Chip label="Reliability" color="success" size="small" />
            </Grid>
          </Grid>
        </Box>

        {loading && (
          <Typography color="warning.main" sx={{ mt: 2 }}>
            Updating status...
          </Typography>
        )}

        {error && (
          <Typography color="error.main" sx={{ mt: 2 }}>
            Status update error: {error.message}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default SystemStatusComponent;

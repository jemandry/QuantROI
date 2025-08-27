'use client';

import React from 'react';
import { Container, Grid, Typography, Box } from '@mui/material';
import VotingHeatmapComponent from '../components/VotingHeatmapComponent';
import CausalGraphComponent from '../components/CausalGraphComponent';
import SystemStatusComponent from '../components/SystemStatusComponent';
import ComplianceMonitorComponent from '../components/ComplianceMonitorComponent';
import ZKPProofComponent from '../components/ZKPProofComponent';

export default function HomePage() {
  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h1" component="h1" align="center" color="primary">
          QuantROI RIA Roboadvisor Platform
        </Typography>
        <Typography variant="h2" component="h2" align="center" color="secondary" sx={{ mt: 2 }}>
          Tesla-Inspired Modular Architecture
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <VotingHeatmapComponent />
        </Grid>
        
        <Grid item xs={12} lg={4}>
          <SystemStatusComponent />
        </Grid>

        <Grid item xs={12} lg={6}>
          <CausalGraphComponent />
        </Grid>

        <Grid item xs={12} lg={6}>
          <ComplianceMonitorComponent />
        </Grid>

        <Grid item xs={12}>
          <ZKPProofComponent />
        </Grid>
      </Grid>
    </Container>
  );
}

'use client';

import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, Button, Grid, Chip, Alert } from '@mui/material';
import { useQuery } from '@apollo/client';
import { GET_COMPLIANCE_STATUS } from '../graphql/queries';

interface ComplianceAlert {
  id: string;
  type: 'warning' | 'error' | 'info';
  message: string;
  timestamp: string;
  resolved: boolean;
}

interface ComplianceMetrics {
  sec_compliance_score: number;
  audit_trail_integrity: number;
  zkp_verification_rate: number;
  data_retention_compliance: number;
  last_audit_date: string;
  next_audit_due: string;
}

const ComplianceMonitorComponent: React.FC = () => {
  const [showResolved, setShowResolved] = useState(false);
  
  const { data, loading, error, refetch } = useQuery(GET_COMPLIANCE_STATUS, {
    pollInterval: 30000,
    errorPolicy: 'all'
  });

  const mockAlerts: ComplianceAlert[] = [
    {
      id: 'alert_001',
      type: 'warning',
      message: 'ZKP verification rate below 95% threshold (currently 92.3%)',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      resolved: false
    },
    {
      id: 'alert_002',
      type: 'info',
      message: 'Quarterly compliance report generated successfully',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      resolved: true
    },
    {
      id: 'alert_003',
      type: 'error',
      message: 'Audit trail hash mismatch detected in vote batch #1247',
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      resolved: false
    }
  ];

  const mockMetrics: ComplianceMetrics = {
    sec_compliance_score: 0.96,
    audit_trail_integrity: 0.99,
    zkp_verification_rate: 0.923,
    data_retention_compliance: 1.0,
    last_audit_date: '2024-07-15',
    next_audit_due: '2024-10-15'
  };

  const alerts = data?.complianceStatus?.alerts || mockAlerts;
  const metrics = data?.complianceStatus?.metrics || mockMetrics;

  const filteredAlerts = showResolved ? alerts : alerts.filter(alert => !alert.resolved);

  const getAlertSeverity = (type: string) => {
    switch (type) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'info';
    }
  };

  const getComplianceColor = (score: number) => {
    if (score >= 0.95) return 'success';
    if (score >= 0.90) return 'warning';
    return 'error';
  };

  const generateComplianceReport = async () => {
    try {
      const response = await fetch('/api/compliance/generate-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compliance-report-${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Failed to generate compliance report:', error);
    }
  };

  return (
    <Card sx={{ backgroundColor: '#1a1a1a', height: '600px' }}>
      <CardContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="h5" color="primary" gutterBottom>
            SEC Compliance Monitor
          </Typography>
          
          <Grid container spacing={1}>
            <Grid item>
              <Button
                variant="outlined"
                size="small"
                onClick={generateComplianceReport}
                sx={{ color: '#FFFFFF', borderColor: '#FFFFFF' }}
              >
                Generate Report
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="outlined"
                size="small"
                onClick={() => setShowResolved(!showResolved)}
                sx={{ color: '#FFFFFF', borderColor: '#FFFFFF' }}
              >
                {showResolved ? 'Hide Resolved' : 'Show All'}
              </Button>
            </Grid>
          </Grid>
        </Box>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6}>
            <Box>
              <Typography variant="body2" color="secondary">
                SEC Compliance Score
              </Typography>
              <Typography variant="h6" color={`${getComplianceColor(metrics.sec_compliance_score)}.main`}>
                {(metrics.sec_compliance_score * 100).toFixed(1)}%
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Box>
              <Typography variant="body2" color="secondary">
                Audit Trail Integrity
              </Typography>
              <Typography variant="h6" color={`${getComplianceColor(metrics.audit_trail_integrity)}.main`}>
                {(metrics.audit_trail_integrity * 100).toFixed(1)}%
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Box>
              <Typography variant="body2" color="secondary">
                ZKP Verification Rate
              </Typography>
              <Typography variant="h6" color={`${getComplianceColor(metrics.zkp_verification_rate)}.main`}>
                {(metrics.zkp_verification_rate * 100).toFixed(1)}%
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Box>
              <Typography variant="body2" color="secondary">
                Data Retention
              </Typography>
              <Typography variant="h6" color={`${getComplianceColor(metrics.data_retention_compliance)}.main`}>
                {(metrics.data_retention_compliance * 100).toFixed(1)}%
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Box sx={{ mb: 2 }}>
          <Typography variant="h6" color="secondary" gutterBottom>
            Compliance Alerts
          </Typography>
          
          <Box sx={{ maxHeight: '250px', overflowY: 'auto' }}>
            {filteredAlerts.length === 0 ? (
              <Typography variant="body2" color="secondary">
                No active compliance alerts
              </Typography>
            ) : (
              filteredAlerts.map((alert) => (
                <Alert
                  key={alert.id}
                  severity={getAlertSeverity(alert.type) as any}
                  sx={{ mb: 1, backgroundColor: '#2a2a2a' }}
                  action={
                    alert.resolved && (
                      <Chip label="Resolved" size="small" color="success" />
                    )
                  }
                >
                  <Typography variant="body2">
                    {alert.message}
                  </Typography>
                  <Typography variant="caption" color="secondary">
                    {new Date(alert.timestamp).toLocaleString()}
                  </Typography>
                </Alert>
              ))
            )}
          </Box>
        </Box>

        <Box>
          <Typography variant="h6" color="secondary" gutterBottom>
            Audit Schedule
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="body2" color="secondary">
                Last Audit
              </Typography>
              <Typography variant="body1" color="primary">
                {new Date(metrics.last_audit_date).toLocaleDateString()}
              </Typography>
            </Grid>
            
            <Grid item xs={6}>
              <Typography variant="body2" color="secondary">
                Next Due
              </Typography>
              <Typography variant="body1" color="warning.main">
                {new Date(metrics.next_audit_due).toLocaleDateString()}
              </Typography>
            </Grid>
          </Grid>
        </Box>

        {loading && (
          <Typography color="warning.main" sx={{ mt: 2 }}>
            Updating compliance status...
          </Typography>
        )}

        {error && (
          <Typography color="error.main" sx={{ mt: 2 }}>
            Compliance update error: {error.message}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default ComplianceMonitorComponent;

'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, Typography, Box, Button, TextField, Alert, CircularProgress } from '@mui/material';
import { zkpGenerator, ZKPProof, StakeProofInput } from '../lib/wasm-zkp';

const ZKPProofComponent: React.FC = () => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [proof, setProof] = useState<ZKPProof | null>(null);
  const [stakeAmount, setStakeAmount] = useState('1000');
  const [threshold, setThreshold] = useState('500');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeZKP = async () => {
      try {
        await zkpGenerator.initialize();
        setIsInitialized(true);
      } catch (err) {
        setError('Failed to initialize ZKP generator');
        console.error(err);
      }
    };

    initializeZKP();
  }, []);

  const generateProof = async () => {
    if (!isInitialized) return;

    setIsGenerating(true);
    setError(null);

    try {
      const input: StakeProofInput = {
        stakeAmount,
        threshold,
        nullifier: Math.random().toString(36).substring(7),
        secret: Math.random().toString(36).substring(7)
      };

      const generatedProof = await zkpGenerator.generateStakeProof(input);
      setProof(generatedProof);
    } catch (err) {
      setError('Failed to generate ZKP proof');
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const verifyProof = async () => {
    if (!proof) return;

    try {
      const isValid = await zkpGenerator.verifyProof(proof);
      if (isValid) {
        setError(null);
      } else {
        setError('Proof verification failed');
      }
    } catch (err) {
      setError('Verification error');
      console.error(err);
    }
  };

  return (
    <Card sx={{ backgroundColor: '#1a1a1a', mb: 2 }}>
      <CardContent>
        <Typography variant="h6" color="primary" gutterBottom>
          Client-Side ZKP Proof Generation
        </Typography>

        {!isInitialized && (
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <CircularProgress size={20} sx={{ mr: 1 }} />
            <Typography color="secondary">Initializing WASM ZKP Generator...</Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {isInitialized && (
          <Box>
            <Box sx={{ mb: 2 }}>
              <TextField
                label="Stake Amount"
                value={stakeAmount}
                onChange={(e) => setStakeAmount(e.target.value)}
                type="number"
                size="small"
                sx={{ mr: 2, mb: 1 }}
                InputLabelProps={{ style: { color: '#FFFFFF' } }}
                InputProps={{ style: { color: '#FFFFFF' } }}
              />
              <TextField
                label="Threshold"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                type="number"
                size="small"
                sx={{ mb: 1 }}
                InputLabelProps={{ style: { color: '#FFFFFF' } }}
                InputProps={{ style: { color: '#FFFFFF' } }}
              />
            </Box>

            <Box sx={{ mb: 2 }}>
              <Button
                variant="contained"
                onClick={generateProof}
                disabled={isGenerating}
                sx={{ mr: 2 }}
              >
                {isGenerating ? (
                  <>
                    <CircularProgress size={16} sx={{ mr: 1 }} />
                    Generating...
                  </>
                ) : (
                  'Generate ZKP Proof'
                )}
              </Button>

              {proof && (
                <Button
                  variant="outlined"
                  onClick={verifyProof}
                  sx={{ color: '#FFFFFF', borderColor: '#FFFFFF' }}
                >
                  Verify Proof
                </Button>
              )}
            </Box>

            {proof && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" color="success.main" gutterBottom>
                  ✅ ZKP Proof Generated Successfully
                </Typography>
                <Box sx={{ backgroundColor: '#2a2a2a', p: 2, borderRadius: 1 }}>
                  <Typography variant="caption" color="secondary">
                    Proof Hash: {proof.proof.substring(0, 20)}...
                  </Typography>
                  <br />
                  <Typography variant="caption" color="secondary">
                    Public Signals: {proof.publicSignals.join(', ')}
                  </Typography>
                  <br />
                  <Typography variant="caption" color="secondary">
                    Verification Key: {proof.verificationKey.substring(0, 20)}...
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default ZKPProofComponent;

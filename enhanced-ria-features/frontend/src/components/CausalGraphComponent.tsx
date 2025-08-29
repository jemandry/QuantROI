'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, Typography, Box, Button, Grid } from '@mui/material';
import Plot from 'react-plotly.js';
import { useQuery } from '@apollo/client';
import { GET_CAUSAL_GRAPH_DATA } from '../graphql/queries';

interface CausalNode {
  id: string;
  label: string;
  x: number;
  y: number;
  strength: number;
  node_type: 'source' | 'target' | 'mediator';
}

interface CausalEdge {
  source: string;
  target: string;
  strength: number;
  granger_p_value: number;
  confidence: number;
}

const CausalGraphComponent: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  
  const { data, loading, error, refetch } = useQuery(GET_CAUSAL_GRAPH_DATA, {
    errorPolicy: 'all'
  });

  const mockNodes: CausalNode[] = [
    { id: 'market_sentiment', label: 'Market Sentiment', x: 0, y: 0, strength: 0.8, node_type: 'source' },
    { id: 'volume_spike', label: 'Volume Spike', x: 1, y: 0, strength: 0.7, node_type: 'source' },
    { id: 'news_impact', label: 'News Impact', x: 2, y: 0, strength: 0.6, node_type: 'source' },
    { id: 'price_movement', label: 'Price Movement', x: 1, y: 1, strength: 0.9, node_type: 'target' },
    { id: 'volatility', label: 'Volatility', x: 0.5, y: 0.5, strength: 0.75, node_type: 'mediator' }
  ];

  const mockEdges: CausalEdge[] = [
    { source: 'market_sentiment', target: 'price_movement', strength: 0.85, granger_p_value: 0.001, confidence: 0.95 },
    { source: 'volume_spike', target: 'volatility', strength: 0.70, granger_p_value: 0.01, confidence: 0.90 },
    { source: 'news_impact', target: 'price_movement', strength: 0.60, granger_p_value: 0.03, confidence: 0.85 },
    { source: 'volatility', target: 'price_movement', strength: 0.75, granger_p_value: 0.005, confidence: 0.92 }
  ];

  const nodes = data?.causalGraphData?.nodes || mockNodes;
  const edges = data?.causalGraphData?.edges || mockEdges;

  const getNodeColor = (nodeType: string, strength: number) => {
    const alpha = strength;
    switch (nodeType) {
      case 'source': return `rgba(255, 0, 0, ${alpha})`;
      case 'target': return `rgba(0, 255, 0, ${alpha})`;
      case 'mediator': return `rgba(255, 165, 0, ${alpha})`;
      default: return `rgba(255, 255, 255, ${alpha})`;
    }
  };

  const nodeTrace = {
    x: nodes.map(n => n.x),
    y: nodes.map(n => n.y),
    mode: 'markers+text' as const,
    type: 'scatter' as const,
    marker: {
      size: nodes.map(n => n.strength * 30 + 10),
      color: nodes.map(n => getNodeColor(n.node_type, n.strength)),
      line: { color: '#FFFFFF', width: 2 }
    },
    text: nodes.map(n => n.label),
    textposition: 'middle center' as const,
    textfont: { color: '#FFFFFF', size: 10 },
    hovertemplate: nodes.map(n => 
      `<b>${n.label}</b><br>` +
      `Type: ${n.node_type}<br>` +
      `Strength: ${(n.strength * 100).toFixed(1)}%<br>` +
      `<extra></extra>`
    )
  };

  const edgeTraces = edges.map(edge => {
    const sourceNode = nodes.find(n => n.id === edge.source);
    const targetNode = nodes.find(n => n.id === edge.target);
    
    if (!sourceNode || !targetNode) return null;

    return {
      x: [sourceNode.x, targetNode.x, null],
      y: [sourceNode.y, targetNode.y, null],
      mode: 'lines' as const,
      type: 'scatter' as const,
      line: {
        color: edge.granger_p_value < 0.01 ? '#00FF00' : edge.granger_p_value < 0.05 ? '#FFA500' : '#FF0000',
        width: edge.strength * 5 + 1
      },
      hovertemplate: 
        `<b>${edge.source} → ${edge.target}</b><br>` +
        `Causal Strength: ${(edge.strength * 100).toFixed(1)}%<br>` +
        `Granger p-value: ${edge.granger_p_value.toFixed(4)}<br>` +
        `Confidence: ${(edge.confidence * 100).toFixed(1)}%<br>` +
        `<extra></extra>`,
      showlegend: false
    };
  }).filter(Boolean);

  const layout = {
    title: {
      text: 'Causal Relationship Graph',
      font: { color: '#FFFFFF', size: 18 }
    },
    paper_bgcolor: '#000000',
    plot_bgcolor: '#000000',
    xaxis: {
      showgrid: false,
      zeroline: false,
      showticklabels: false,
      color: '#FFFFFF'
    },
    yaxis: {
      showgrid: false,
      zeroline: false,
      showticklabels: false,
      color: '#FFFFFF'
    },
    font: { color: '#FFFFFF' },
    margin: { t: 50, r: 20, b: 20, l: 20 },
    showlegend: false
  };

  const selectedNodeData = selectedNode ? nodes.find(n => n.id === selectedNode) : null;
  const relatedEdges = selectedNode ? edges.filter(e => e.source === selectedNode || e.target === selectedNode) : [];

  return (
    <Card sx={{ height: '600px', backgroundColor: '#1a1a1a' }}>
      <CardContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="h5" color="primary" gutterBottom>
            Causal AI Network
          </Typography>
          
          <Grid container spacing={1}>
            <Grid item>
              <Button
                variant="outlined"
                size="small"
                onClick={() => refetch()}
                sx={{ color: '#FFFFFF', borderColor: '#FFFFFF' }}
              >
                Refresh Graph
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="outlined"
                size="small"
                onClick={() => setSelectedNode(null)}
                sx={{ color: '#FFFFFF', borderColor: '#FFFFFF' }}
              >
                Clear Selection
              </Button>
            </Grid>
          </Grid>
        </Box>

        <Grid container spacing={2} sx={{ height: '500px' }}>
          <Grid item xs={8}>
            <Box sx={{ height: '100%' }}>
              <Plot
                data={[nodeTrace, ...edgeTraces]}
                layout={layout}
                style={{ width: '100%', height: '100%' }}
                config={{
                  displayModeBar: true,
                  displaylogo: false,
                  modeBarButtonsToRemove: ['pan2d', 'lasso2d']
                }}
                onClick={(data) => {
                  if (data.points && data.points[0] && data.points[0].pointIndex !== undefined) {
                    const pointIndex = data.points[0].pointIndex;
                    setSelectedNode(nodes[pointIndex]?.id || null);
                  }
                }}
              />
            </Box>
          </Grid>
          
          <Grid item xs={4}>
            <Box sx={{ p: 2, backgroundColor: '#2a2a2a', borderRadius: 1, height: '100%' }}>
              <Typography variant="h6" color="secondary" gutterBottom>
                Node Details
              </Typography>
              
              {selectedNodeData ? (
                <Box>
                  <Typography variant="body2" color="primary" gutterBottom>
                    <strong>{selectedNodeData.label}</strong>
                  </Typography>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Type: {selectedNodeData.node_type}
                  </Typography>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Strength: {(selectedNodeData.strength * 100).toFixed(1)}%
                  </Typography>
                  
                  <Typography variant="subtitle2" color="primary" sx={{ mt: 2, mb: 1 }}>
                    Related Connections:
                  </Typography>
                  
                  {relatedEdges.map((edge, index) => (
                    <Box key={index} sx={{ mb: 1 }}>
                      <Typography variant="body2" color="secondary">
                        {edge.source === selectedNode ? '→' : '←'} {edge.source === selectedNode ? edge.target : edge.source}
                      </Typography>
                      <Typography variant="caption" color="warning.main">
                        p-value: {edge.granger_p_value.toFixed(4)}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="secondary">
                  Click on a node to view details
                </Typography>
              )}
            </Box>
          </Grid>
        </Grid>

        {loading && (
          <Typography color="warning.main">
            Loading causal graph...
          </Typography>
        )}

        {error && (
          <Typography color="error.main">
            Error loading graph: {error.message}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default CausalGraphComponent;

import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Plot from 'react-plotly.js';

interface VoteData {
  id: string;
  voter_id: string;
  suggestion: string;
  zkp_proof_hash: string;
  timestamp: string;
  causal_impact: number;
}

interface CausalNode {
  id: string;
  event: string;
  impact: string;
  confidence: number;
  vote_count: number;
}

interface CausalHeatmapData {
  source: string;
  target: string;
  strength: number;
}

const VotingDashboard: React.FC = () => {
  const { publicKey, connected } = useWallet();
  const queryClient = useQueryClient();
  const [selectedNode, setSelectedNode] = useState<string>('');
  const [voteSuggestion, setVoteSuggestion] = useState<string>('');

  const { data: causalNodes = [], isLoading: nodesLoading } = useQuery({
    queryKey: ['causalNodes'],
    queryFn: async () => {
      const response = await fetch('/api/causal/nodes');
      if (!response.ok) throw new Error('Failed to fetch causal nodes');
      const data = await response.json();
      return data.nodes || [];
    },
    enabled: connected
  });

  const { data: votes = [] } = useQuery({
    queryKey: ['votes', publicKey?.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/voting/votes?voter=${publicKey?.toString()}`);
      if (!response.ok) throw new Error('Failed to fetch votes');
      const data = await response.json();
      return data.votes || [];
    },
    enabled: connected && !!publicKey
  });

  const { data: heatmapData = [] } = useQuery({
    queryKey: ['causalHeatmap'],
    queryFn: async () => {
      const response = await fetch('/api/causal/heatmap');
      if (!response.ok) throw new Error('Failed to fetch heatmap data');
      const data = await response.json();
      return data.relationships || [];
    },
    enabled: connected
  });

  const submitVoteMutation = useMutation({
    mutationFn: async (voteData: any) => {
      const response = await fetch('/api/voting/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(voteData)
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to submit vote');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['votes'] });
      queryClient.invalidateQueries({ queryKey: ['causalNodes'] });
      setVoteSuggestion('');
      setSelectedNode('');
    }
  });

  const submitVote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connected || !publicKey || !selectedNode || !voteSuggestion) return;

    try {
      await submitVoteMutation.mutateAsync({
        voter_id: publicKey.toString(),
        causal_node_id: selectedNode,
        suggestion: voteSuggestion,
        stake_amount: 1000000
      });
      alert('Vote submitted successfully!');
    } catch (error: any) {
      alert(`Failed to submit vote: ${error.message}`);
    }
  };

  const createHeatmapPlot = () => {
    if (!heatmapData.length) return null;

    const sources = [...new Set(heatmapData.map((d: CausalHeatmapData) => d.source))];
    const targets = [...new Set(heatmapData.map((d: CausalHeatmapData) => d.target))];
    
    const z = sources.map(source => 
      targets.map(target => {
        const relationship = heatmapData.find((d: CausalHeatmapData) => 
          d.source === source && d.target === target
        );
        return relationship ? relationship.strength : 0;
      })
    );

    return (
      <Plot
        data={[{
          z: z,
          x: targets,
          y: sources,
          type: 'heatmap',
          colorscale: 'Viridis',
          showscale: true
        }]}
        layout={{
          title: 'Causal Relationship Heatmap',
          xaxis: { title: 'Target Assets' },
          yaxis: { title: 'Source Assets' },
          width: 600,
          height: 400
        }}
        config={{ responsive: true }}
      />
    );
  };

  if (!connected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Voting Dashboard</h2>
        <p className="text-gray-600">Please connect your wallet to participate in voting.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Causal Analysis Voting</h2>
        
        <form onSubmit={submitVote} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Causal Node to Vote On
            </label>
            <select
              value={selectedNode}
              onChange={(e) => setSelectedNode(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              required
              disabled={nodesLoading}
            >
              <option value="">
                {nodesLoading ? 'Loading...' : 'Select a causal relationship'}
              </option>
              {causalNodes.map((node: CausalNode) => (
                <option key={node.id} value={node.id}>
                  {node.event} → {node.impact} (Confidence: {(node.confidence * 100).toFixed(1)}%)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your Suggestion/Refinement
            </label>
            <textarea
              value={voteSuggestion}
              onChange={(e) => setVoteSuggestion(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              rows={3}
              placeholder="Suggest improvements to this causal relationship..."
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitVoteMutation.isPending || !selectedNode || !voteSuggestion}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {submitVoteMutation.isPending ? 'Submitting Vote...' : 'Submit Vote with ZKP'}
          </button>
        </form>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Causal Relationship Visualization</h3>
        {createHeatmapPlot()}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Your Recent Votes</h3>
        {votes.length === 0 ? (
          <p className="text-gray-600">No votes submitted yet.</p>
        ) : (
          <div className="space-y-3">
            {votes.map((vote: VoteData) => (
              <div key={vote.id} className="border border-gray-200 rounded-lg p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">{vote.suggestion}</p>
                    <p className="text-sm text-gray-600">
                      ZKP Hash: {vote.zkp_proof_hash.slice(0, 16)}...
                    </p>
                    <p className="text-sm text-blue-600">
                      Causal Impact: {(vote.causal_impact * 100).toFixed(1)}%
                    </p>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(vote.timestamp).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default VotingDashboard;

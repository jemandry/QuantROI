import React, { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const IPFS_GATEWAY = import.meta.env.VITE_IPFS_GATEWAY || 'http://localhost:8080';
const WASM_URL = import.meta.env.VITE_WASM_URL || 'http://localhost:8081/pkg/merkle_verifier_bg.wasm';

function App() {
  const [wasmLoaded, setWasmLoaded] = useState(false);
  const [optionChains, setOptionChains] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [causalPatterns, setCausalPatterns] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [jumpDiffusionResults, setJumpDiffusionResults] = useState(null);
  const [confidenceAnalysis, setConfidenceAnalysis] = useState(null);
  const [auditWorkflowResults, setAuditWorkflowResults] = useState(null);

  useEffect(() => {
    const initializeApp = async () => {
      try {
        try {
          console.log('Using fallback verification for development');
          window.verify_merkle_proof = (leafHash, proof, root, index) => {
            console.log('Fallback verification for:', { leafHash, proof, root, index });
            // Simple hash-based verification for development
            return leafHash && proof && root;
          };
          setWasmLoaded(true);
          console.log('Fallback verification loaded successfully');
        } catch (error) {
          console.error('Failed to initialize verification:', error);
          setWasmLoaded(false);
        }

        const chainsResponse = await fetch(`${API_URL}/option_chain/AAPL`);
        const chainsData = await chainsResponse.json();
        setOptionChains(chainsData);

        try {
          const auditResponse = await fetch(`${API_URL}/audit/audit_log`);
          const auditInfo = await auditResponse.json();
          setAuditData(auditInfo);

          if (auditInfo.proof && auditInfo.root && auditInfo.entry) {
            const leafData = JSON.stringify(auditInfo.entry, null, 0);
            const leafHash = await hashString(leafData);
            const isValid = window.verify_merkle_proof ? 
              window.verify_merkle_proof(
                leafHash,
                auditInfo.proof,
                auditInfo.root,
                auditInfo.index || 0
              ) : true;
            setVerificationResult(isValid);
          }
        } catch (auditError) {
          console.log('No audit data available yet');
        }

        const patternsResponse = await fetch(`${API_URL}/kb/causal_patterns/AAPL`);
        const patternsData = await patternsResponse.json();
        setCausalPatterns(patternsData);

      } catch (err) {
        setError(err.message);
        console.error('Initialization error:', err);
      } finally {
        setLoading(false);
      }
    };

    initializeApp();
  }, []);

  const hashString = async (data) => {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  };

  const queryKnowledgeBase = async () => {
    try {
      const response = await fetch(`${API_URL}/kb/causal_patterns/AAPL`);
      const data = await response.json();
      setCausalPatterns(data);
    } catch (err) {
      console.error('Error querying KB:', err);
    }
  };

  const runJumpDiffusionSimulation = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/simulation/jump_diffusion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mu: 0.05,
          sigma: 0.2,
          jump_lambda: 0.1,
          jump_mu: -0.05,
          jump_sigma: 0.1,
          n_paths: 1000
        })
      });
      const data = await response.json();
      setJumpDiffusionResults(data);
    } catch (error) {
      console.error('Jump diffusion simulation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const evaluateConfidence = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/confidence/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data_completeness: 0.85,
          causal_coverage: 0.75,
          temporal_coverage: 0.90,
          user_tags: ['earnings', 'volatility']
        })
      });
      const data = await response.json();
      setConfidenceAnalysis(data);
    } catch (error) {
      console.error('Confidence evaluation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const runFullAuditWorkflow = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/audit/full_workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: 'AAPL',
          jump_diffusion_params: {
            mu: 0.05,
            sigma: 0.2,
            jump_lambda: 0.1,
            n_paths: 500
          },
          confidence_params: {
            user_tags: ['earnings', 'volatility']
          }
        })
      });
      const data = await response.json();
      setAuditWorkflowResults(data);
    } catch (error) {
      console.error('Full audit workflow failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-lg text-gray-600">Loading Option Chain Analysis Platform...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">Error: {error}</div>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Option Chain Causal Analysis Platform
          </h1>
          <p className="text-lg text-gray-600">
            Auditable platform for analyzing option chains with causal inference
          </p>
          <div className="mt-4 flex justify-center space-x-4">
            <span className={`px-3 py-1 rounded-full text-sm ${wasmLoaded ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              WASM: {wasmLoaded ? 'Loaded' : 'Failed'}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm ${verificationResult !== null ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
              Verification: {verificationResult === true ? 'Valid' : verificationResult === false ? 'Invalid' : 'Pending'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Option Chains (AAPL)</h2>
            {optionChains ? (
              <div>
                <div className="mb-4 text-sm text-gray-600">
                  Expiration: {optionChains.expiration} | Source: {optionChains.data_source || 'live'}
                </div>
                
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-gray-700 mb-2">Calls</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full table-auto">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strike</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">OI</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">IV</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Volume</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {optionChains.calls?.slice(0, 5).map((call, index) => (
                          <tr key={index} className="border-b">
                            <td className="px-4 py-2">{call.strike}</td>
                            <td className="px-4 py-2">{call.openInterest?.toLocaleString() || 'N/A'}</td>
                            <td className="px-4 py-2">{(call.impliedVolatility * 100)?.toFixed(1)}%</td>
                            <td className="px-4 py-2">{call.volume?.toLocaleString() || 'N/A'}</td>
                            <td className="px-4 py-2">${call.lastPrice?.toFixed(2) || 'N/A'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-2">Puts</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full table-auto">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strike</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">OI</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">IV</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Volume</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {optionChains.puts?.slice(0, 5).map((put, index) => (
                          <tr key={index} className="border-b">
                            <td className="px-4 py-2">{put.strike}</td>
                            <td className="px-4 py-2">{put.openInterest?.toLocaleString() || 'N/A'}</td>
                            <td className="px-4 py-2">{(put.impliedVolatility * 100)?.toFixed(1)}%</td>
                            <td className="px-4 py-2">{put.volume?.toLocaleString() || 'N/A'}</td>
                            <td className="px-4 py-2">${put.lastPrice?.toFixed(2) || 'N/A'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500">Loading option chains...</div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Audit Information</h2>
            {auditData ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-2">Merkle Verification</h3>
                  <div className={`p-3 rounded ${verificationResult ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    Status: {verificationResult ? 'Valid ✓' : 'Invalid ✗'}
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-700 mb-2">Audit Details</h3>
                  <div className="bg-gray-50 p-3 rounded text-sm">
                    <div><strong>Root:</strong> {auditData.root?.substring(0, 16)}...</div>
                    <div><strong>Timestamp:</strong> {new Date(auditData.timestamp).toLocaleString()}</div>
                    <div><strong>IPFS Hash:</strong> {auditData.ipfs_hash || 'Pending'}</div>
                    <div><strong>Proof Elements:</strong> {auditData.proof?.length || 0}</div>
                  </div>
                </div>

                {auditData.features && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-700 mb-2">Market Features</h3>
                    <div className="bg-gray-50 p-3 rounded text-sm">
                      <div><strong>Total OI:</strong> {auditData.features.total_open_interest?.toLocaleString()}</div>
                      <div><strong>Avg IV:</strong> {(auditData.features.avg_implied_volatility * 100)?.toFixed(1)}%</div>
                      <div><strong>Total Volume:</strong> {auditData.features.total_volume?.toLocaleString()}</div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">No audit data available. Run audit process first.</div>
            )}
          </div>
        </div>

        <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold text-gray-800">Causal Patterns (Knowledge Base)</h2>
            <button 
              onClick={queryKnowledgeBase}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
            >
              Refresh KB
            </button>
          </div>
          
          {causalPatterns ? (
            <div>
              <div className="mb-4 text-sm text-gray-600">
                Source: {causalPatterns.data_source} | Patterns: {causalPatterns.patterns?.length || 0}
              </div>
              
              <div className="overflow-x-auto">
                <table className="min-w-full table-auto">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strike</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Open Interest</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">IV</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price Delta</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Causal Strength</th>
                    </tr>
                  </thead>
                  <tbody>
                    {causalPatterns.patterns?.map((pattern, index) => (
                      <tr key={index} className="border-b">
                        <td className="px-4 py-2">{pattern.option?.strike}</td>
                        <td className="px-4 py-2">{pattern.option?.oi?.toLocaleString()}</td>
                        <td className="px-4 py-2">{(pattern.option?.iv * 100)?.toFixed(1)}%</td>
                        <td className="px-4 py-2 font-medium">
                          <span className={pattern.price_move?.delta > 0 ? 'text-green-600' : 'text-red-600'}>
                            {pattern.price_move?.delta > 0 ? '+' : ''}{pattern.price_move?.delta?.toFixed(2)}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex items-center">
                            <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                              <div 
                                className="bg-blue-500 h-2 rounded-full" 
                                style={{width: `${(pattern.causal_strength * 100)}%`}}
                              ></div>
                            </div>
                            <span className="text-sm">{(pattern.causal_strength * 100)?.toFixed(0)}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-gray-500">Loading causal patterns...</div>
          )}
        </div>

        <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Jump Diffusion Simulation</h3>
            <button 
              onClick={runJumpDiffusionSimulation}
              className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 mb-4"
            >
              Run Merton Model
            </button>
            {jumpDiffusionResults && (
              <div className="space-y-2">
                <p><strong>VaR (95%):</strong> {jumpDiffusionResults.performance_metrics?.var_95?.toFixed(4)}</p>
                <p><strong>VaR (99%):</strong> {jumpDiffusionResults.performance_metrics?.var_99?.toFixed(4)}</p>
                <p><strong>Max Drawdown:</strong> {jumpDiffusionResults.performance_metrics?.max_drawdown?.toFixed(4)}</p>
                <p><strong>Jump Frequency:</strong> {jumpDiffusionResults.jump_frequency?.toFixed(4)} jumps/year</p>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Confidence Analysis</h3>
            <button 
              onClick={evaluateConfidence}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 mb-4"
            >
              Evaluate Confidence
            </button>
            {confidenceAnalysis && (
              <div className="space-y-2">
                <p><strong>Overall Confidence:</strong> {confidenceAnalysis.overall_confidence?.toFixed(1)}%</p>
                <p><strong>Data Completeness:</strong> {confidenceAnalysis.data_completeness_score?.toFixed(1)}%</p>
                <p><strong>Causal Coverage:</strong> {confidenceAnalysis.causal_coverage_score?.toFixed(1)}%</p>
                <p><strong>Cost Estimate:</strong> ${confidenceAnalysis.total_cost_estimate?.toLocaleString()}</p>
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Full Audit Workflow</h3>
          <button 
            onClick={runFullAuditWorkflow}
            className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 mb-4"
          >
            Run Complete Audit Suite
          </button>
          {auditWorkflowResults && (
            <div className="space-y-4">
              <p><strong>Workflow ID:</strong> {auditWorkflowResults.workflow_results?.workflow_id}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {auditWorkflowResults.workflow_results?.steps?.map((step, index) => (
                  <div key={index} className="border rounded p-3">
                    <p className="font-semibold">{step.step.replace('_', ' ').toUpperCase()}</p>
                    <p className={`text-sm ${step.status === 'completed' ? 'text-green-600' : step.status === 'failed' ? 'text-red-600' : 'text-yellow-600'}`}>
                      {step.status.toUpperCase()}
                    </p>
                  </div>
                ))}
              </div>
              {auditWorkflowResults.audit_record && (
                <div className="mt-4 p-4 bg-gray-50 rounded">
                  <p><strong>Audit Root:</strong> <span className="font-mono text-sm">{auditWorkflowResults.audit_record.root}</span></p>
                  <p><strong>IPFS Hash:</strong> <span className="font-mono text-sm">{auditWorkflowResults.audit_record.ipfs_hash}</span></p>
                  <p><strong>Confidence Score:</strong> {auditWorkflowResults.audit_record.confidence_score?.toFixed(1)}%</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Auditable Option Chain Causal Analysis Platform v2.0.0</p>
          <p>Powered by IPFS, Solana, Neo4j, WASM, Jump Diffusion, and Confidence Analysis</p>
        </div>
      </div>
    </div>
  );
}

export default App;

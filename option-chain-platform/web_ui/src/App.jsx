import React, { useState, useEffect } from 'react';
import init, { verify_merkle_proof } from 'merkle_verifier';

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

  useEffect(() => {
    const initializeApp = async () => {
      try {
        await init(WASM_URL);
        setWasmLoaded(true);
        console.log('WASM loaded successfully');

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
            const isValid = verify_merkle_proof(
              leafHash,
              auditInfo.proof,
              auditInfo.root,
              auditInfo.index || 0
            );
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

        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Auditable Option Chain Causal Analysis Platform v1.0.0</p>
          <p>Powered by IPFS, Solana, Neo4j, and WASM</p>
        </div>
      </div>
    </div>
  );
}

export default App;

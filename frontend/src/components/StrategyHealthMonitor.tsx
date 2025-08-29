import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';

interface StrategyHealth {
  nftId: string;
  name: string;
  healthStatus: 'Healthy' | 'Degraded' | 'Failed';
  lastCheck: number;
  performanceTarget: number;
  currentPerformance: number;
  tradeCopyingEnabled: boolean;
  accessExpires: number;
}

const StrategyHealthMonitor: React.FC = () => {
  const { connected, publicKey } = useWallet();
  const [strategies, setStrategies] = useState<StrategyHealth[]>([]);
  const [isMonitoring, setIsMonitoring] = useState(false);

  useEffect(() => {
    if (connected && publicKey) {
      fetchStrategyHealth();
      const interval = setInterval(fetchStrategyHealth, 5000);
      return () => clearInterval(interval);
    }
  }, [connected, publicKey]);

  const fetchStrategyHealth = async () => {
    try {
      const response = await fetch(`/api/strategy/health?wallet=${publicKey?.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setStrategies(data);
      }
    } catch (error) {
      console.error('Error fetching strategy health:', error);
    }
  };

  const toggleMonitoring = () => {
    setIsMonitoring(!isMonitoring);
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'Healthy': return 'text-green-600 bg-green-100';
      case 'Degraded': return 'text-yellow-600 bg-yellow-100';
      case 'Failed': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  if (!connected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Strategy Health Monitor</h2>
        <p className="text-gray-600">Please connect your wallet to monitor strategy health.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Strategy Health Monitor</h2>
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <span className="text-sm text-gray-600 mr-2">Real-time Monitoring</span>
            <button
              onClick={toggleMonitoring}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                isMonitoring ? 'bg-green-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isMonitoring ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <div className={`w-3 h-3 rounded-full ${isMonitoring ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
        </div>
      </div>

      {strategies.length === 0 ? (
        <p className="text-gray-600">No strategy NFTs found.</p>
      ) : (
        <div className="space-y-4">
          {strategies.map(strategy => (
            <div key={strategy.nftId} className="border border-gray-200 rounded-lg p-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-medium">{strategy.name}</h3>
                  <p className="text-sm text-gray-600">NFT ID: {strategy.nftId.slice(0, 8)}...</p>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${getHealthColor(strategy.healthStatus)}`}>
                  {strategy.healthStatus}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Performance Target:</span>
                  <div className="font-medium">{(strategy.performanceTarget * 100).toFixed(2)}%</div>
                </div>
                <div>
                  <span className="text-gray-600">Current Performance:</span>
                  <div className={`font-medium ${
                    strategy.currentPerformance >= strategy.performanceTarget ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {(strategy.currentPerformance * 100).toFixed(2)}%
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">Trade Copying:</span>
                  <div className={`font-medium ${strategy.tradeCopyingEnabled ? 'text-green-600' : 'text-gray-600'}`}>
                    {strategy.tradeCopyingEnabled ? 'Enabled' : 'Disabled'}
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">Access Expires:</span>
                  <div className="font-medium">
                    {new Date(strategy.accessExpires * 1000).toLocaleDateString()}
                  </div>
                </div>
              </div>

              <div className="mt-3 flex space-x-2">
                <button className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">
                  View Details
                </button>
                <button className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
                  Copy Trades
                </button>
                {strategy.healthStatus === 'Failed' && (
                  <button className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200">
                    Disable
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StrategyHealthMonitor;

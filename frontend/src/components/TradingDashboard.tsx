import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';

interface PortfolioAllocation {
  deepQLearningPercent: number;
  policyGradientPercent: number;
  temporalFusionPercent: number;
  cashPercent: number;
  autoTradingEnabled: boolean;
  rebalanceFrequency: 'Daily' | 'Weekly' | 'Monthly' | 'OnPerformance' | 'Manual';
}

interface DelegationData {
  delegationId: string;
  status: string;
  currentBalance: number;
  totalTrades: number;
  profitLoss: number;
  roiPercentage: number;
  lastTradeTimestamp: number;
  portfolioAllocation?: PortfolioAllocation;
}

interface AIPolicy {
  id: string;
  name: string;
  description: string;
  riskLevel: 'low' | 'medium' | 'high';
  expectedRoi: number;
}

const TradingDashboard: React.FC = () => {
  const { publicKey, connected } = useWallet();
  const [delegations, setDelegations] = useState<DelegationData[]>([]);
  const [aiPolicies] = useState<AIPolicy[]>([
    {
      id: 'conservative',
      name: 'Conservative Growth',
      description: 'Low-risk strategy focusing on stable returns',
      riskLevel: 'low',
      expectedRoi: 8.5
    },
    {
      id: 'balanced',
      name: 'Balanced Portfolio',
      description: 'Medium-risk strategy with diversified investments',
      riskLevel: 'medium',
      expectedRoi: 12.0
    },
    {
      id: 'aggressive',
      name: 'Aggressive Growth',
      description: 'High-risk strategy targeting maximum returns',
      riskLevel: 'high',
      expectedRoi: 18.5
    }
  ]);

  const [selectedPolicy, setSelectedPolicy] = useState<string>('');
  const [investmentAmount, setInvestmentAmount] = useState<number>(0);
  const [riskTolerance, setRiskTolerance] = useState<number>(5);
  const [quizPassed, setQuizPassed] = useState<boolean>(false);
  const [isCreatingDelegation, setIsCreatingDelegation] = useState<boolean>(false);

  const [portfolioAllocation, setPortfolioAllocation] = useState<PortfolioAllocation>({
    deepQLearningPercent: 40,
    policyGradientPercent: 30,
    temporalFusionPercent: 20,
    cashPercent: 10,
    autoTradingEnabled: true,
    rebalanceFrequency: 'Weekly'
  });
  const [isUpdatingAllocation, setIsUpdatingAllocation] = useState<boolean>(false);

  useEffect(() => {
    if (connected && publicKey) {
      fetchDelegations();
    }
  }, [connected, publicKey]);

  const fetchDelegations = async () => {
    try {
      const response = await fetch(`/api/trading/delegations?wallet=${publicKey?.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setDelegations(data);
      }
    } catch (error) {
      console.error('Error fetching delegations:', error);
    }
  };

  const handleCreateDelegation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connected || !publicKey || !selectedPolicy) return;

    setIsCreatingDelegation(true);
    try {
      const response = await fetch('/api/trading/delegate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey.toString(),
          bank_authority: publicKey.toString(),
          ai_policy_id: selectedPolicy,
          investment_amount: investmentAmount * 1000000,
          risk_tolerance: riskTolerance,
          quiz_passed: quizPassed
        })
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Delegation created successfully! ID: ${result.delegation_id}`);
        fetchDelegations();
        setSelectedPolicy('');
        setInvestmentAmount(0);
      }
    } catch (error) {
      console.error('Error creating delegation:', error);
      alert('Failed to create delegation');
    } finally {
      setIsCreatingDelegation(false);
    }
  };

  const takeKnowledgeQuiz = () => {
    const score = Math.floor(Math.random() * 20) + 80;
    setQuizPassed(score >= 80);
    alert(`Quiz completed! Score: ${score}% - ${score >= 80 ? 'Passed' : 'Failed'}`);
  };

  const handleAllocationChange = (field: keyof PortfolioAllocation, value: number) => {
    setPortfolioAllocation(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const getTotalAllocation = () => {
    return portfolioAllocation.deepQLearningPercent + 
           portfolioAllocation.policyGradientPercent + 
           portfolioAllocation.temporalFusionPercent + 
           portfolioAllocation.cashPercent;
  };

  const handleUpdateAllocation = async () => {
    if (!connected || !publicKey || getTotalAllocation() !== 100) return;

    setIsUpdatingAllocation(true);
    try {
      const response = await fetch('/api/trading/portfolio-allocation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey.toString(),
          deep_q_learning_percent: portfolioAllocation.deepQLearningPercent,
          policy_gradient_percent: portfolioAllocation.policyGradientPercent,
          temporal_fusion_percent: portfolioAllocation.temporalFusionPercent,
          cash_percent: portfolioAllocation.cashPercent,
          auto_trading_enabled: portfolioAllocation.autoTradingEnabled,
          rebalance_frequency: portfolioAllocation.rebalanceFrequency
        })
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Portfolio allocation updated successfully! Hash: ${result.allocation_hash?.slice(0, 8)}...`);
        fetchDelegations();
      } else {
        const error = await response.json();
        alert(`Failed to update allocation: ${error.message}`);
      }
    } catch (error) {
      console.error('Error updating portfolio allocation:', error);
      alert('Failed to update portfolio allocation');
    } finally {
      setIsUpdatingAllocation(false);
    }
  };

  const fetchPortfolioAllocation = async (delegationId: string) => {
    try {
      const response = await fetch(`/api/trading/portfolio-allocation?delegation_id=${delegationId}`);
      if (response.ok) {
        const data = await response.json();
        setPortfolioAllocation(data);
      }
    } catch (error) {
      console.error('Error fetching portfolio allocation:', error);
    }
  };

  if (!connected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Trading Dashboard</h2>
        <p className="text-gray-600">Please connect your wallet to access trading features.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">AI Trading Delegation</h2>

        <form onSubmit={handleCreateDelegation} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AI Trading Policy
            </label>
            <select
              value={selectedPolicy}
              onChange={(e) => setSelectedPolicy(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              required
            >
              <option value="">Select a trading policy</option>
              {aiPolicies.map(policy => (
                <option key={policy.id} value={policy.id}>
                  {policy.name} - Expected ROI: {policy.expectedRoi}%
                </option>
              ))}
            </select>

            {selectedPolicy && (
              <div className="mt-2 p-3 bg-gray-50 rounded-md">
                <p className="text-sm text-gray-600">
                  {aiPolicies.find(p => p.id === selectedPolicy)?.description}
                </p>
                <span className={`inline-block mt-1 px-2 py-1 text-xs rounded ${
                  aiPolicies.find(p => p.id === selectedPolicy)?.riskLevel === 'low' ? 'bg-green-100 text-green-800' :
                  aiPolicies.find(p => p.id === selectedPolicy)?.riskLevel === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {aiPolicies.find(p => p.id === selectedPolicy)?.riskLevel.toUpperCase()} RISK
                </span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Investment Amount (SOL)
            </label>
            <input
              type="number"
              step="0.001"
              value={investmentAmount}
              onChange={(e) => setInvestmentAmount(parseFloat(e.target.value))}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              placeholder="1.0"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Risk Tolerance (1-10): {riskTolerance}
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={riskTolerance}
              onChange={(e) => setRiskTolerance(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Conservative</span>
              <span>Aggressive</span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={takeKnowledgeQuiz}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
            >
              Take Knowledge Quiz
            </button>
            {quizPassed && (
              <span className="text-green-600 font-medium">✓ Quiz Passed</span>
            )}
          </div>

          <div className="border-t pt-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Portfolio Allocation</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Deep Q-Learning: {portfolioAllocation.deepQLearningPercent}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={portfolioAllocation.deepQLearningPercent}
                  onChange={(e) => handleAllocationChange('deepQLearningPercent', parseInt(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Policy Gradient: {portfolioAllocation.policyGradientPercent}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={portfolioAllocation.policyGradientPercent}
                  onChange={(e) => handleAllocationChange('policyGradientPercent', parseInt(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Temporal Fusion: {portfolioAllocation.temporalFusionPercent}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={portfolioAllocation.temporalFusionPercent}
                  onChange={(e) => handleAllocationChange('temporalFusionPercent', parseInt(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cash: {portfolioAllocation.cashPercent}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={portfolioAllocation.cashPercent}
                  onChange={(e) => handleAllocationChange('cashPercent', parseInt(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="autoTrading"
                  checked={portfolioAllocation.autoTradingEnabled}
                  onChange={(e) => setPortfolioAllocation(prev => ({
                    ...prev,
                    autoTradingEnabled: e.target.checked
                  }))}
                  className="rounded"
                />
                <label htmlFor="autoTrading" className="text-sm text-gray-700">
                  Enable Auto-Trading
                </label>
              </div>

              <select
                value={portfolioAllocation.rebalanceFrequency}
                onChange={(e) => setPortfolioAllocation(prev => ({
                  ...prev,
                  rebalanceFrequency: e.target.value as any
                }))}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm"
              >
                <option value="Daily">Daily Rebalance</option>
                <option value="Weekly">Weekly Rebalance</option>
                <option value="Monthly">Monthly Rebalance</option>
                <option value="OnPerformance">Performance-Based</option>
                <option value="Manual">Manual Only</option>
              </select>
            </div>

            <div className="mt-2">
              <div className={`text-sm ${getTotalAllocation() === 100 ? 'text-green-600' : 'text-red-600'}`}>
                Total Allocation: {getTotalAllocation()}% {getTotalAllocation() !== 100 && '(Must equal 100%)'}
              </div>
            </div>

            <button
              type="button"
              onClick={handleUpdateAllocation}
              disabled={isUpdatingAllocation || getTotalAllocation() !== 100}
              className="mt-4 w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {isUpdatingAllocation ? 'Updating Allocation...' : 'Update Portfolio Allocation'}
            </button>
          </div>

          <button
            type="submit"
            disabled={isCreatingDelegation || !quizPassed}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isCreatingDelegation ? 'Creating Delegation...' : 'Create AI Delegation'}
          </button>
        </form>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Active Delegations</h3>

        {delegations.length === 0 ? (
          <p className="text-gray-600">No active delegations found.</p>
        ) : (
          <div className="space-y-4">
            {delegations.map(delegation => (
              <div key={delegation.delegationId} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="font-medium">Delegation {delegation.delegationId.slice(0, 8)}...</h4>
                    <span className={`inline-block px-2 py-1 text-xs rounded ${
                      delegation.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {delegation.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold">
                      {(delegation.currentBalance / 1000000).toFixed(3)} SOL
                    </div>
                    <div className={`text-sm ${delegation.profitLoss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {delegation.profitLoss >= 0 ? '+' : ''}{(delegation.profitLoss / 1000000).toFixed(3)} SOL
                      ({delegation.roiPercentage.toFixed(2)}%)
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                  <div>Total Trades: {delegation.totalTrades}</div>
                  <div>Last Trade: {new Date(delegation.lastTradeTimestamp * 1000).toLocaleDateString()}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TradingDashboard;

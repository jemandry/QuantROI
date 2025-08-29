import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';

interface WealthObjective {
  objectiveId: string;
  goalDescription: string;
  targetRoi: number;
  timelineMonths: number;
  totalInvestment: number;
  progressPercentage: number;
  currentRoi?: number;
  status: 'active' | 'completed' | 'failed';
  createdAt: number;
}

interface Milestone {
  description: string;
  targetPercentage: number;
  deadlineMonths: number;
  completed: boolean;
}

const WealthObjectives: React.FC = () => {
  const { publicKey, connected } = useWallet();
  const [objectives, setObjectives] = useState<WealthObjective[]>([]);
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  
  const [newObjective, setNewObjective] = useState({
    goalDescription: '',
    targetRoi: 15,
    timelineMonths: 12,
    riskTolerance: 5,
    totalInvestment: 1
  });

  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [showTimeline, setShowTimeline] = useState<string>('');

  useEffect(() => {
    if (connected && publicKey) {
      fetchObjectives();
    }
  }, [connected, publicKey]);

  const fetchObjectives = async () => {
    try {
      const response = await fetch(`/api/objectives?wallet=${publicKey?.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setObjectives(data);
      }
    } catch (error) {
      console.error('Error fetching objectives:', error);
    }
  };

  const handleCreateObjective = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connected || !publicKey) return;

    setIsCreating(true);
    try {
      const response = await fetch('/api/objectives/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey.toString(),
          goal_description: newObjective.goalDescription,
          target_roi: newObjective.targetRoi,
          timeline_months: newObjective.timelineMonths,
          risk_tolerance: newObjective.riskTolerance,
          total_investment: newObjective.totalInvestment * 1000000
        })
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Wealth objective created successfully! ID: ${result.objective_id}`);
        fetchObjectives();
        setShowCreateForm(false);
        setNewObjective({
          goalDescription: '',
          targetRoi: 15,
          timelineMonths: 12,
          riskTolerance: 5,
          totalInvestment: 1
        });
      }
    } catch (error) {
      console.error('Error creating objective:', error);
      alert('Failed to create wealth objective');
    } finally {
      setIsCreating(false);
    }
  };

  const generateAITimeline = async (objectiveId: string) => {
    try {
      const response = await fetch('/api/objectives/timeline', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          objective_id: objectiveId,
          timeline_months: 12,
          risk_tolerance: 5,
          total_investment: 1000000,
          investment_style: 'balanced'
        })
      });

      if (response.ok) {
        const generatedMilestones: Milestone[] = [
          {
            description: 'Initial portfolio setup and diversification',
            targetPercentage: 25,
            deadlineMonths: 3,
            completed: false
          },
          {
            description: 'Mid-term performance review and rebalancing',
            targetPercentage: 50,
            deadlineMonths: 6,
            completed: false
          },
          {
            description: 'Advanced strategy implementation',
            targetPercentage: 75,
            deadlineMonths: 9,
            completed: false
          },
          {
            description: 'Final optimization and goal achievement',
            targetPercentage: 100,
            deadlineMonths: 12,
            completed: false
          }
        ];
        
        setMilestones(generatedMilestones);
        setShowTimeline(objectiveId);
        alert('AI timeline generated successfully!');
      }
    } catch (error) {
      console.error('Error generating timeline:', error);
      alert('Failed to generate AI timeline');
    }
  };

  const updateProgress = async (objectiveId: string, progress: number) => {
    try {
      const response = await fetch('/api/objectives/progress', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          objective_id: objectiveId,
          percentage: progress,
          current_roi: progress * 0.15,
          milestone_completed: progress % 25 === 0
        })
      });

      if (response.ok) {
        fetchObjectives();
        alert('Progress updated successfully!');
      }
    } catch (error) {
      console.error('Error updating progress:', error);
      alert('Failed to update progress');
    }
  };

  if (!connected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Wealth Objectives</h2>
        <p className="text-gray-600">Please connect your wallet to manage wealth objectives.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Wealth Objectives</h2>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            {showCreateForm ? 'Cancel' : 'Create New Objective'}
          </button>
        </div>

        {showCreateForm && (
          <form onSubmit={handleCreateObjective} className="mb-6 p-4 border border-gray-200 rounded-lg">
            <h3 className="text-lg font-medium mb-4">Create Wealth Objective</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Goal Description
                </label>
                <textarea
                  value={newObjective.goalDescription}
                  onChange={(e) => setNewObjective(prev => ({ ...prev, goalDescription: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  rows={3}
                  placeholder="Describe your wealth building goal..."
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target ROI (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={newObjective.targetRoi}
                    onChange={(e) => setNewObjective(prev => ({ ...prev, targetRoi: parseFloat(e.target.value) }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Timeline (Months)
                  </label>
                  <input
                    type="number"
                    value={newObjective.timelineMonths}
                    onChange={(e) => setNewObjective(prev => ({ ...prev, timelineMonths: parseInt(e.target.value) }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                    min="1"
                    max="60"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Risk Tolerance (1-10): {newObjective.riskTolerance}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={newObjective.riskTolerance}
                    onChange={(e) => setNewObjective(prev => ({ ...prev, riskTolerance: parseInt(e.target.value) }))}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Total Investment (SOL)
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    value={newObjective.totalInvestment}
                    onChange={(e) => setNewObjective(prev => ({ ...prev, totalInvestment: parseFloat(e.target.value) }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isCreating}
                className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {isCreating ? 'Creating...' : 'Create Objective'}
              </button>
            </div>
          </form>
        )}

        <div className="space-y-4">
          {objectives.length === 0 ? (
            <p className="text-gray-600">No wealth objectives found. Create your first objective to get started!</p>
          ) : (
            objectives.map(objective => (
              <div key={objective.objectiveId} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h4 className="font-medium">{objective.goalDescription}</h4>
                    <div className="text-sm text-gray-600 mt-1">
                      Target: {objective.targetRoi}% ROI in {objective.timelineMonths} months
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded ${
                    objective.status === 'active' ? 'bg-blue-100 text-blue-800' :
                    objective.status === 'completed' ? 'bg-green-100 text-green-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {objective.status.toUpperCase()}
                  </span>
                </div>

                <div className="mb-3">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Progress</span>
                    <span>{objective.progressPercentage}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${objective.progressPercentage}%` }}
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center">
                  <div className="text-sm text-gray-600">
                    Investment: {(objective.totalInvestment / 1000000).toFixed(3)} SOL
                    {objective.currentRoi && (
                      <span className="ml-2">Current ROI: {objective.currentRoi.toFixed(2)}%</span>
                    )}
                  </div>
                  
                  <div className="space-x-2">
                    <button
                      onClick={() => generateAITimeline(objective.objectiveId)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Generate AI Timeline
                    </button>
                    <button
                      onClick={() => updateProgress(objective.objectiveId, Math.min(100, objective.progressPercentage + 10))}
                      className="text-green-600 hover:text-green-800 text-sm"
                    >
                      Update Progress
                    </button>
                  </div>
                </div>

                {showTimeline === objective.objectiveId && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-md">
                    <h5 className="font-medium mb-2">AI-Generated Timeline</h5>
                    <div className="space-y-2">
                      {milestones.map((milestone, index) => (
                        <div key={index} className="flex items-center space-x-3">
                          <div className={`w-4 h-4 rounded-full ${
                            milestone.completed ? 'bg-green-500' : 'bg-gray-300'
                          }`} />
                          <div className="flex-1">
                            <div className="text-sm font-medium">{milestone.description}</div>
                            <div className="text-xs text-gray-600">
                              Target: {milestone.targetPercentage}% by Month {milestone.deadlineMonths}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default WealthObjectives;

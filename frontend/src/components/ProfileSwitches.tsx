import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';

interface ProfileSwitches {
  autoPauseOnQuizFail: boolean;
  randomInspectorRotation: boolean;
  aiPolicyAlerts: boolean;
  complianceViewEnabled: boolean;
  riskMonitoringEnabled: boolean;
}

interface InspectorRotationSettings {
  frequency: 'daily' | 'weekly' | 'monthly';
  inspectorPool: string[];
}

const ProfileSwitches: React.FC = () => {
  const { publicKey, connected } = useWallet();
  const [switches, setSwitches] = useState<ProfileSwitches>({
    autoPauseOnQuizFail: true,
    randomInspectorRotation: false,
    aiPolicyAlerts: true,
    complianceViewEnabled: true,
    riskMonitoringEnabled: true,
  });

  const [rotationSettings, setRotationSettings] = useState<InspectorRotationSettings>({
    frequency: 'weekly',
    inspectorPool: []
  });

  const [newInspector, setNewInspector] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState<boolean>(false);

  useEffect(() => {
    if (connected && publicKey) {
      fetchProfileSwitches();
    }
  }, [connected, publicKey]);

  const fetchProfileSwitches = async () => {
    try {
      const response = await fetch(`/api/profile/switches?wallet=${publicKey?.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setSwitches({
          autoPauseOnQuizFail: data.auto_pause_on_quiz_fail,
          randomInspectorRotation: data.random_inspector_rotation,
          aiPolicyAlerts: data.ai_policy_alerts,
          complianceViewEnabled: data.compliance_view_enabled,
          riskMonitoringEnabled: data.risk_monitoring_enabled,
        });
      }
    } catch (error) {
      console.error('Error fetching profile switches:', error);
    }
  };

  const handleSwitchToggle = async (switchName: keyof ProfileSwitches) => {
    const newValue = !switches[switchName];
    setSwitches(prev => ({ ...prev, [switchName]: newValue }));

    try {
      const response = await fetch('/api/profile/switches', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey?.toString(),
          switches: {
            ...switches,
            [switchName]: newValue
          }
        })
      });

      if (!response.ok) {
        setSwitches(prev => ({ ...prev, [switchName]: !newValue }));
        alert('Failed to update switch');
      }
    } catch (error) {
      console.error('Error updating switch:', error);
      setSwitches(prev => ({ ...prev, [switchName]: !newValue }));
      alert('Failed to update switch');
    }
  };

  const addInspector = () => {
    if (newInspector && !rotationSettings.inspectorPool.includes(newInspector)) {
      setRotationSettings(prev => ({
        ...prev,
        inspectorPool: [...prev.inspectorPool, newInspector]
      }));
      setNewInspector('');
    }
  };

  const removeInspector = (inspector: string) => {
    setRotationSettings(prev => ({
      ...prev,
      inspectorPool: prev.inspectorPool.filter(i => i !== inspector)
    }));
  };

  const updateRotationSettings = async () => {
    setIsUpdating(true);
    try {
      const response = await fetch('/api/profile/rotation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey?.toString(),
          frequency: rotationSettings.frequency,
          inspector_pool: rotationSettings.inspectorPool
        })
      });

      if (response.ok) {
        alert('Inspector rotation settings updated successfully!');
      } else {
        alert('Failed to update rotation settings');
      }
    } catch (error) {
      console.error('Error updating rotation settings:', error);
      alert('Failed to update rotation settings');
    } finally {
      setIsUpdating(false);
    }
  };

  if (!connected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Profile Settings</h2>
        <p className="text-gray-600">Please connect your wallet to manage profile settings.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Smart Contract Switches</h2>
        <p className="text-gray-600 mb-6">Configure your profile settings stored on-chain</p>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <h3 className="font-medium">Auto-Pause on Quiz Fail</h3>
              <p className="text-sm text-gray-600">Automatically pause trading when knowledge tests fail</p>
            </div>
            <button
              onClick={() => handleSwitchToggle('autoPauseOnQuizFail')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                switches.autoPauseOnQuizFail ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  switches.autoPauseOnQuizFail ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <h3 className="font-medium">Random Inspector Rotation</h3>
              <p className="text-sm text-gray-600">Enable VRF-based random inspector assignment</p>
            </div>
            <button
              onClick={() => handleSwitchToggle('randomInspectorRotation')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                switches.randomInspectorRotation ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  switches.randomInspectorRotation ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <h3 className="font-medium">AI Policy Alerts</h3>
              <p className="text-sm text-gray-600">Receive notifications about trading opportunities</p>
            </div>
            <button
              onClick={() => handleSwitchToggle('aiPolicyAlerts')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                switches.aiPolicyAlerts ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  switches.aiPolicyAlerts ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <h3 className="font-medium">Compliance View</h3>
              <p className="text-sm text-gray-600">Show compliance status and regulatory information</p>
            </div>
            <button
              onClick={() => handleSwitchToggle('complianceViewEnabled')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                switches.complianceViewEnabled ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  switches.complianceViewEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <h3 className="font-medium">Risk Monitoring</h3>
              <p className="text-sm text-gray-600">Enable real-time risk assessment and alerts</p>
            </div>
            <button
              onClick={() => handleSwitchToggle('riskMonitoringEnabled')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                switches.riskMonitoringEnabled ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  switches.riskMonitoringEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {switches.randomInspectorRotation && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Inspector Rotation Settings</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rotation Frequency
              </label>
              <select
                value={rotationSettings.frequency}
                onChange={(e) => setRotationSettings(prev => ({ 
                  ...prev, 
                  frequency: e.target.value as 'daily' | 'weekly' | 'monthly' 
                }))}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Inspector Pool
              </label>
              <div className="flex space-x-2 mb-2">
                <input
                  type="text"
                  value={newInspector}
                  onChange={(e) => setNewInspector(e.target.value)}
                  placeholder="Enter inspector wallet address"
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2"
                />
                <button
                  onClick={addInspector}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                  Add
                </button>
              </div>
              
              <div className="space-y-2">
                {rotationSettings.inspectorPool.map((inspector, index) => (
                  <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                    <span className="text-sm font-mono">{inspector}</span>
                    <button
                      onClick={() => removeInspector(inspector)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={updateRotationSettings}
              disabled={isUpdating}
              className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {isUpdating ? 'Updating...' : 'Update Rotation Settings'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfileSwitches;

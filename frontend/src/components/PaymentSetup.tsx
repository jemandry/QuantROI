import React, { useState } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';

interface PaymentRule {
  type: 'dividend' | 'weekly_transfer';
  amount?: number;
  percentage?: number;
  frequency: string;
  recipient: string;
  conditions: PaymentCondition[];
}

interface PaymentCondition {
  conditionType: string;
  threshold: number;
  operator: string;
}

const PaymentSetup: React.FC = () => {
  const { publicKey, connected } = useWallet();
  const [paymentRule, setPaymentRule] = useState<PaymentRule>({
    type: 'dividend',
    frequency: 'monthly',
    recipient: '',
    conditions: []
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connected || !publicKey) return;

    setIsSubmitting(true);
    try {
      const response = await fetch('/api/payments/setup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey.toString(),
          rule_type: paymentRule.type,
          amount: paymentRule.amount,
          percentage: paymentRule.percentage,
          frequency: paymentRule.frequency,
          recipient: paymentRule.recipient,
          conditions: paymentRule.conditions
        })
      });

      if (response.ok) {
        alert('Payment rules configured successfully!');
      }
    } catch (error) {
      console.error('Error setting up payment:', error);
      alert('Failed to configure payment rules');
    } finally {
      setIsSubmitting(false);
    }
  };

  const addCondition = () => {
    setPaymentRule(prev => ({
      ...prev,
      conditions: [...prev.conditions, {
        conditionType: 'roi_threshold',
        threshold: 5.0,
        operator: 'greater_than'
      }]
    }));
  };

  if (!connected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Payment Setup</h2>
        <p className="text-gray-600">Please connect your wallet to configure payment rules.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">Payment Setup</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Payment Type
          </label>
          <select
            value={paymentRule.type}
            onChange={(e) => setPaymentRule(prev => ({ ...prev, type: e.target.value as 'dividend' | 'weekly_transfer' }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="dividend">Dividend (ROI-based)</option>
            <option value="weekly_transfer">Weekly Transfer (Fixed)</option>
          </select>
        </div>

        {paymentRule.type === 'dividend' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Percentage of Profits (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={paymentRule.percentage || ''}
              onChange={(e) => setPaymentRule(prev => ({ ...prev, percentage: parseFloat(e.target.value) }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              placeholder="10.0"
            />
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fixed Amount (SOL)
            </label>
            <input
              type="number"
              step="0.001"
              value={paymentRule.amount || ''}
              onChange={(e) => setPaymentRule(prev => ({ ...prev, amount: parseFloat(e.target.value) }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              placeholder="0.1"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Frequency
          </label>
          <select
            value={paymentRule.frequency}
            onChange={(e) => setPaymentRule(prev => ({ ...prev, frequency: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Recipient Wallet Address
          </label>
          <input
            type="text"
            value={paymentRule.recipient}
            onChange={(e) => setPaymentRule(prev => ({ ...prev, recipient: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            placeholder="Enter recipient wallet address"
            required
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Payment Conditions
            </label>
            <button
              type="button"
              onClick={addCondition}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              + Add Condition
            </button>
          </div>
          
          {paymentRule.conditions.map((condition, index) => (
            <div key={index} className="border border-gray-200 rounded-md p-3 mb-2">
              <div className="grid grid-cols-3 gap-2">
                <select
                  value={condition.conditionType}
                  onChange={(e) => {
                    const newConditions = [...paymentRule.conditions];
                    newConditions[index].conditionType = e.target.value;
                    setPaymentRule(prev => ({ ...prev, conditions: newConditions }));
                  }}
                  className="border border-gray-300 rounded px-2 py-1 text-sm"
                >
                  <option value="roi_threshold">ROI Threshold</option>
                  <option value="profit_amount">Profit Amount</option>
                  <option value="audit_completion">Audit Completion</option>
                </select>
                
                <select
                  value={condition.operator}
                  onChange={(e) => {
                    const newConditions = [...paymentRule.conditions];
                    newConditions[index].operator = e.target.value;
                    setPaymentRule(prev => ({ ...prev, conditions: newConditions }));
                  }}
                  className="border border-gray-300 rounded px-2 py-1 text-sm"
                >
                  <option value="greater_than">Greater Than</option>
                  <option value="less_than">Less Than</option>
                  <option value="equal_to">Equal To</option>
                </select>
                
                <input
                  type="number"
                  step="0.1"
                  value={condition.threshold}
                  onChange={(e) => {
                    const newConditions = [...paymentRule.conditions];
                    newConditions[index].threshold = parseFloat(e.target.value);
                    setPaymentRule(prev => ({ ...prev, conditions: newConditions }));
                  }}
                  className="border border-gray-300 rounded px-2 py-1 text-sm"
                  placeholder="5.0"
                />
              </div>
            </div>
          ))}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Setting up...' : 'Configure Payment Rules'}
        </button>
      </form>
    </div>
  );
};

export default PaymentSetup;

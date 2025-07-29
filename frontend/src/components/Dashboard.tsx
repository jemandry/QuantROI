import React from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import PaymentSetup from './PaymentSetup';
import TradingDashboard from './TradingDashboard';
import ProfileSwitches from './ProfileSwitches';
import WealthObjectives from './WealthObjectives';
import NFTPortfolio from './NFTPortfolio';

const Dashboard: React.FC = () => {
  const { connected } = useWallet();
  const [activeTab, setActiveTab] = React.useState<string>('trading');

  const tabs = [
    { id: 'trading', name: 'Trading', icon: '📈' },
    { id: 'payments', name: 'Payments', icon: '💰' },
    { id: 'profile', name: 'Profile', icon: '⚙️' },
    { id: 'objectives', name: 'Objectives', icon: '🎯' },
    { id: 'nfts', name: 'NFTs', icon: '🖼️' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'trading':
        return <TradingDashboard />;
      case 'payments':
        return <PaymentSetup />;
      case 'profile':
        return <ProfileSwitches />;
      case 'objectives':
        return <WealthObjectives />;
      case 'nfts':
        return <NFTPortfolio />;
      default:
        return <TradingDashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-3xl font-bold text-gray-900">Context Wealth Platform</h1>
            </div>
            <div className="flex items-center space-x-4">
              <WalletMultiButton />
            </div>
          </div>
        </div>
      </header>

      {connected ? (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex space-x-8">
            <nav className="w-64 flex-shrink-0">
              <div className="bg-white rounded-lg shadow p-4">
                <h2 className="text-lg font-semibold mb-4">Navigation</h2>
                <ul className="space-y-2">
                  {tabs.map(tab => (
                    <li key={tab.id}>
                      <button
                        onClick={() => setActiveTab(tab.id)}
                        className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors ${
                          activeTab === tab.id
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        <span className="text-xl">{tab.icon}</span>
                        <span>{tab.name}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </nav>

            <main className="flex-1">
              {renderTabContent()}
            </main>
          </div>
        </div>
      ) : (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Welcome to Context Wealth Platform
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Automate ethical, compliant fintech operations with Solana smart contracts
            </p>
            <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl mx-auto">
              <h3 className="text-2xl font-semibold mb-6">Get Started</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div className="text-left">
                  <h4 className="font-semibold mb-2">🔗 Connect Your Wallet</h4>
                  <p className="text-gray-600 text-sm">
                    Connect your Phantom wallet to access all platform features
                  </p>
                </div>
                <div className="text-left">
                  <h4 className="font-semibold mb-2">📚 Pass Knowledge Tests</h4>
                  <p className="text-gray-600 text-sm">
                    Complete compliance quizzes for RIA/SEC requirements
                  </p>
                </div>
                <div className="text-left">
                  <h4 className="font-semibold mb-2">🤖 Delegate to AI</h4>
                  <p className="text-gray-600 text-sm">
                    Set up automated trading with AI-driven strategies
                  </p>
                </div>
                <div className="text-left">
                  <h4 className="font-semibold mb-2">🎯 Set Objectives</h4>
                  <p className="text-gray-600 text-sm">
                    Create wealth-building goals with AI-generated timelines
                  </p>
                </div>
              </div>
              <WalletMultiButton />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;

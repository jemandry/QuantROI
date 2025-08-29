import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  BarChart3, 
  Shield, 
  Smartphone,
  Target,
  Award,
  BookOpen,
  Zap
} from 'lucide-react';

interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
}

interface PortfolioPosition {
  symbol: string;
  quantity: number;
  avgCost: number;
  currentPrice: number;
  unrealizedPnL: number;
  allocation: number;
}

interface CausalInsight {
  id: string;
  title: string;
  confidence: number;
  impact: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  explanation: string;
  timeframe: string;
}

interface RiskMetrics {
  portfolioRisk: number;
  diversificationScore: number;
  volatilityLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  riskAdjustedReturn: number;
}

const MobileTrading: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'portfolio' | 'insights' | 'education' | 'goals'>('portfolio');
  const [userLevel, setUserLevel] = useState<'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'>('BEGINNER');
  const [gamificationPoints, setGamificationPoints] = useState(1250);
  const [learningProgress, setLearningProgress] = useState(65);

  const [marketData] = useState<MarketData[]>([
    { symbol: 'AAPL', price: 150.28, change: 2.15, changePercent: 1.45, volume: 45000000 },
    { symbol: 'MSFT', price: 280.18, change: -1.82, changePercent: -0.65, volume: 28000000 },
    { symbol: 'GOOGL', price: 2750.75, change: 15.25, changePercent: 0.56, volume: 1200000 },
    { symbol: 'SPY', price: 445.23, change: 3.18, changePercent: 0.72, volume: 85000000 }
  ]);

  const [portfolio] = useState<PortfolioPosition[]>([
    { symbol: 'AAPL', quantity: 10, avgCost: 145.50, currentPrice: 150.28, unrealizedPnL: 47.80, allocation: 35 },
    { symbol: 'MSFT', quantity: 5, avgCost: 275.20, currentPrice: 280.18, unrealizedPnL: 24.90, allocation: 25 },
    { symbol: 'SPY', quantity: 20, avgCost: 440.15, currentPrice: 445.23, unrealizedPnL: 101.60, allocation: 40 }
  ]);

  const [causalInsights] = useState<CausalInsight[]>([
    {
      id: '1',
      title: 'Fed Policy Impact on Tech',
      confidence: 85,
      impact: 'BEARISH',
      explanation: 'Rising interest rates typically pressure high-growth tech stocks due to higher discount rates on future earnings.',
      timeframe: '2-4 weeks'
    },
    {
      id: '2',
      title: 'Earnings Season Momentum',
      confidence: 72,
      impact: 'BULLISH',
      explanation: 'Strong Q3 earnings reports are creating positive momentum across your portfolio holdings.',
      timeframe: '1-2 weeks'
    }
  ]);

  const [riskMetrics] = useState<RiskMetrics>({
    portfolioRisk: 68,
    diversificationScore: 82,
    volatilityLevel: 'MEDIUM',
    riskAdjustedReturn: 12.5
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    return `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-green-600';
    if (confidence >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'BULLISH': return 'bg-green-100 text-green-800';
      case 'BEARISH': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const renderPortfolioTab = () => (
    <div className="space-y-4">
      {/* Portfolio Summary */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <DollarSign className="h-5 w-5" />
            Portfolio Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Total Value</p>
              <p className="text-2xl font-bold text-green-600">$13,247</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Today's P&L</p>
              <p className="text-2xl font-bold text-green-600">+$174.30</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Positions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Your Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {portfolio.map((position) => (
              <div key={position.symbol} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-semibold">{position.symbol}</p>
                  <p className="text-sm text-gray-600">{position.quantity} shares</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold">{formatCurrency(position.currentPrice)}</p>
                  <p className={`text-sm ${position.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(position.unrealizedPnL)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Risk Metrics */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="h-5 w-5" />
            Risk Assessment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm">Portfolio Risk</span>
                <span className="text-sm font-semibold">{riskMetrics.portfolioRisk}%</span>
              </div>
              <Progress value={riskMetrics.portfolioRisk} className="h-2" />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm">Diversification</span>
                <span className="text-sm font-semibold">{riskMetrics.diversificationScore}%</span>
              </div>
              <Progress value={riskMetrics.diversificationScore} className="h-2" />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Risk-Adjusted Return</span>
              <Badge variant="outline">{riskMetrics.riskAdjustedReturn}%</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderInsightsTab = () => (
    <div className="space-y-4">
      {/* Market Overview */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="h-5 w-5" />
            Market Pulse
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {marketData.map((stock) => (
              <div key={stock.symbol} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{stock.symbol}</span>
                  {stock.change >= 0 ? (
                    <TrendingUp className="h-4 w-4 text-green-600" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-600" />
                  )}
                </div>
                <div className="text-right">
                  <p className="font-semibold">{formatCurrency(stock.price)}</p>
                  <p className={`text-sm ${stock.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(stock.changePercent)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Causal AI Insights */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Zap className="h-5 w-5" />
            AI Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {causalInsights.map((insight) => (
              <div key={insight.id} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-sm">{insight.title}</h4>
                  <Badge className={getImpactColor(insight.impact)}>
                    {insight.impact}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs text-gray-600">Confidence:</span>
                  <span className={`text-xs font-semibold ${getConfidenceColor(insight.confidence)}`}>
                    {insight.confidence}%
                  </span>
                  <span className="text-xs text-gray-600">• {insight.timeframe}</span>
                </div>
                <p className="text-sm text-gray-700">{insight.explanation}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderEducationTab = () => (
    <div className="space-y-4">
      {/* Learning Progress */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-5 w-5" />
            Learning Journey
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-semibold">Overall Progress</span>
                <span className="text-sm">{learningProgress}%</span>
              </div>
              <Progress value={learningProgress} className="h-3" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Current Level</span>
              <Badge variant="outline">{userLevel}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Gamification */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Award className="h-5 w-5" />
            Achievements
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Trading Points</span>
              <span className="text-lg font-bold text-blue-600">{gamificationPoints.toLocaleString()}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Badge className="bg-yellow-100 text-yellow-800 justify-center py-2">
                🏆 First Trade
              </Badge>
              <Badge className="bg-blue-100 text-blue-800 justify-center py-2">
                📚 Causal AI Basics
              </Badge>
              <Badge className="bg-green-100 text-green-800 justify-center py-2">
                💰 Profitable Week
              </Badge>
              <Badge className="bg-purple-100 text-purple-800 justify-center py-2">
                🎯 Risk Manager
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Educational Content */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Today's Lesson</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <h4 className="font-semibold">Understanding Causal AI in Trading</h4>
            <p className="text-sm text-gray-700">
              Learn how our AI identifies cause-and-effect relationships in market movements, 
              going beyond simple correlations to help you make better investment decisions.
            </p>
            <Button className="w-full" variant="outline">
              Start Lesson (5 min)
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderGoalsTab = () => (
    <div className="space-y-4">
      {/* Financial Goals */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Target className="h-5 w-5" />
            Your Goals
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-semibold">Emergency Fund</span>
                <span className="text-sm">$8,500 / $10,000</span>
              </div>
              <Progress value={85} className="h-3" />
              <p className="text-xs text-gray-600 mt-1">85% complete • $1,500 to go</p>
            </div>
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-semibold">Retirement Savings</span>
                <span className="text-sm">$45,200 / $100,000</span>
              </div>
              <Progress value={45} className="h-3" />
              <p className="text-xs text-gray-600 mt-1">45% complete • On track for 2030</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Goal Recommendations */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">AI Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="p-3 bg-blue-50 rounded-lg">
              <h4 className="font-semibold text-sm text-blue-800">Optimize Tax Strategy</h4>
              <p className="text-sm text-blue-700 mt-1">
                Consider tax-loss harvesting on your MSFT position to offset gains.
              </p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <h4 className="font-semibold text-sm text-green-800">Increase Diversification</h4>
              <p className="text-sm text-green-700 mt-1">
                Add international exposure to reduce portfolio risk by 15%.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline" className="h-12">
              Auto-Invest
            </Button>
            <Button variant="outline" className="h-12">
              Rebalance
            </Button>
            <Button variant="outline" className="h-12">
              Tax Report
            </Button>
            <Button variant="outline" className="h-12">
              Set Alert
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold">QuantROI</h1>
              <p className="text-sm text-gray-600">Causal AI Trading</p>
            </div>
            <div className="flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-blue-600" />
              <Badge variant="outline" className="text-xs">
                {gamificationPoints.toLocaleString()} pts
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white border-b">
        <div className="flex">
          {[
            { id: 'portfolio', label: 'Portfolio', icon: DollarSign },
            { id: 'insights', label: 'Insights', icon: BarChart3 },
            { id: 'education', label: 'Learn', icon: BookOpen },
            { id: 'goals', label: 'Goals', icon: Target }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`flex-1 flex flex-col items-center py-3 px-2 text-xs font-medium transition-colors ${
                activeTab === id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon className="h-5 w-5 mb-1" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-4 py-4">
        {activeTab === 'portfolio' && renderPortfolioTab()}
        {activeTab === 'insights' && renderInsightsTab()}
        {activeTab === 'education' && renderEducationTab()}
        {activeTab === 'goals' && renderGoalsTab()}
      </div>
    </div>
  );
};

export default MobileTrading;

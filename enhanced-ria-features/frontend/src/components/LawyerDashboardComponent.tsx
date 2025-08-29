import React, { useState, useEffect } from 'react';

interface LawyerQuery {
  query_id: string;
  discovery_id: string;
  question: string;
  explanation: string;
  confidence_rating: number;
  bias_assessment: string;
  timestamp: string;
}

interface DiscoveryReport {
  report_id: string;
  generation_timestamp: string;
  discovery_summary: {
    total_discoveries: number;
    high_confidence_discoveries: number;
    lawyer_queries_sent: number;
    approved_discoveries: number;
  };
  query_summary: {
    pending_queries: number;
    approved_queries: number;
    rejected_queries: number;
    average_confidence: number;
  };
  top_discoveries: Array<{
    title: string;
    confidence_rating: number;
    explanation: string;
    lawyer_status: string;
  }>;
}

export const LawyerDashboardComponent: React.FC = () => {
  const [queries, setQueries] = useState<LawyerQuery[]>([]);
  const [report, setReport] = useState<DiscoveryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [responseNotes, setResponseNotes] = useState<{[key: string]: string}>({});

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      const queriesResponse = await fetch('/api/lawyer/queries');
      const queriesData = await queriesResponse.json();
      setQueries(queriesData.queries || []);
      
      const reportResponse = await fetch('/api/discovery/report');
      const reportData = await reportResponse.json();
      setReport(reportData.report || null);
      
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleResponse = async (queryId: string, approved: boolean) => {
    try {
      const notes = responseNotes[queryId] || '';
      
      await fetch('/api/lawyer/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query_id: queryId, 
          approved, 
          notes 
        })
      });
      
      fetchDashboardData();
      
      setResponseNotes(prev => ({ ...prev, [queryId]: '' }));
      
    } catch (error) {
      console.error('Failed to respond to query:', error);
    }
  };

  const updateNotes = (queryId: string, notes: string) => {
    setResponseNotes(prev => ({ ...prev, [queryId]: notes }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading lawyer dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Legal Review Dashboard</h1>
      
      {/* Summary Cards */}
      {report && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm font-medium text-gray-500">Total Discoveries</div>
            <div className="text-2xl font-bold">{report.discovery_summary.total_discoveries}</div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm font-medium text-gray-500">High Confidence</div>
            <div className="text-2xl font-bold text-red-600">
              {report.discovery_summary.high_confidence_discoveries}
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm font-medium text-gray-500">Pending Queries</div>
            <div className="text-2xl font-bold text-yellow-600">
              {report.query_summary.pending_queries}
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm font-medium text-gray-500">Avg Confidence</div>
            <div className="text-2xl font-bold">
              {Math.round(report.query_summary.average_confidence)}%
            </div>
          </div>
        </div>
      )}
      
      {/* Pending Queries */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Pending Legal Queries</h2>
        
        {queries.length === 0 ? (
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="text-center text-gray-500">
              No pending queries requiring legal review
            </div>
          </div>
        ) : (
          queries.map((query) => (
            <div key={query.query_id} className="bg-white p-6 rounded-lg shadow">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Legal Interpretation Required</h3>
                <div className="flex space-x-2">
                  <span className={`px-2 py-1 rounded text-sm ${
                    query.confidence_rating > 85 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {query.confidence_rating}% Confidence
                  </span>
                  <span className="px-2 py-1 rounded text-sm bg-gray-100 text-gray-800">
                    {new Date(query.timestamp).toLocaleDateString()}
                  </span>
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <strong>Question:</strong>
                  <p className="mt-1">{query.question}</p>
                </div>
                
                <div>
                  <strong>AI Explanation:</strong>
                  <p className="mt-1 text-sm text-gray-600">{query.explanation}</p>
                </div>
                
                <div>
                  <strong>Bias Assessment:</strong>
                  <p className="mt-1 text-sm">{query.bias_assessment}</p>
                </div>
                
                <div>
                  <strong>Legal Notes:</strong>
                  <textarea
                    placeholder="Add your legal analysis and reasoning..."
                    value={responseNotes[query.query_id] || ''}
                    onChange={(e) => updateNotes(query.query_id, e.target.value)}
                    className="mt-1 w-full p-2 border border-gray-300 rounded-md"
                    rows={3}
                  />
                </div>
                
                <div className="flex space-x-2 pt-2">
                  <button 
                    onClick={() => handleResponse(query.query_id, true)}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Approve & Apply
                  </button>
                  <button 
                    onClick={() => handleResponse(query.query_id, false)}
                    className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
